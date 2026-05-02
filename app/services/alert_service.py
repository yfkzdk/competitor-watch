"""告警服务 — SQLAlchemy ORM 实现"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from app.core.models import AlertRule, AlertHistory, Competitor
from contextlib import contextmanager


class AlertService:
    def __init__(self, db: Session = None):
        self._injected_db = db

    @contextmanager
    def _session(self):
        if self._injected_db:
            yield self._injected_db
        else:
            from app.core.database import SessionLocal
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def create_alert_rule(self, competitor_id: int, rule_type: str,
                         threshold: float, severity: str, channels: List[str]) -> int:
        with self._session() as db:
            rule = AlertRule(
                competitor_id=competitor_id,
                rule_name=f"{rule_type}_rule_{competitor_id}",
                rule_type=rule_type,
                threshold=threshold,
                condition={"severity": severity, "channels": channels},
                is_active=True,
                notification_method=",".join(channels) if channels else "in_app",
                created_at=datetime.utcnow(),
            )
            db.add(rule)
            db.flush()
            db.refresh(rule)
            return rule.id

    def trigger_alert(self, competitor_id: int, alert_type: str,
                     severity: str, message: str, metadata: Dict = None) -> Optional[int]:
        with self._session() as db:
            # Dedup check within the same session
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            dup_count = (
                db.query(func.count(AlertHistory.id))
                .filter(
                    AlertHistory.competitor_id == competitor_id,
                    AlertHistory.triggered_at >= cutoff,
                    AlertHistory.is_read == False,
                )
                .scalar()
            )
            if dup_count > 0:
                return None

            alert = AlertHistory(
                alert_rule_id=0,
                competitor_id=competitor_id,
                message=message,
                severity=severity,
                is_read=False,
                triggered_at=datetime.utcnow(),
            )
            db.add(alert)
            db.flush()
            db.refresh(alert)
            return alert.id

    def get_pending_alerts(self) -> List[Dict]:
        with self._session() as db:
            severity_order = case(
                (AlertHistory.severity == "P0", 1),
                (AlertHistory.severity == "P1", 2),
                (AlertHistory.severity == "P2", 3),
                else_=4,
            )
            rows = (
                db.query(AlertHistory, Competitor.name.label("competitor_name"))
                .outerjoin(Competitor, AlertHistory.competitor_id == Competitor.id)
                .filter(AlertHistory.is_read == False)
                .order_by(severity_order, AlertHistory.triggered_at.asc())
                .all()
            )
            return [
                {
                    "id": ah.id, "alert_rule_id": ah.alert_rule_id,
                    "competitor_id": ah.competitor_id, "message": ah.message,
                    "severity": ah.severity, "is_read": ah.is_read,
                    "triggered_at": ah.triggered_at.isoformat() if ah.triggered_at else None,
                    "status": "pending" if not ah.is_read else "acknowledged",
                    "competitor_name": competitor_name,
                }
                for ah, competitor_name in rows
            ]

    def mark_alert_sent(self, alert_id: int):
        with self._session() as db:
            alert = db.query(AlertHistory).filter(AlertHistory.id == alert_id).first()
            if alert:
                alert.is_read = True
                db.flush()

    def acknowledge_alert(self, alert_id: int):
        with self._session() as db:
            alert = db.query(AlertHistory).filter(AlertHistory.id == alert_id).first()
            if alert:
                alert.is_read = True
                db.flush()

    def get_alerts(self, severity: Optional[str] = None, status: Optional[str] = None,
                   limit: int = 50) -> List[Dict]:
        with self._session() as db:
            q = (
                db.query(AlertHistory, Competitor.name.label("competitor_name"))
                .outerjoin(Competitor, AlertHistory.competitor_id == Competitor.id)
            )
            if severity:
                q = q.filter(AlertHistory.severity == severity)
            if status == "pending":
                q = q.filter(AlertHistory.is_read == False)
            elif status == "read":
                q = q.filter(AlertHistory.is_read == True)
            rows = q.order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
            return [
                {
                    "id": ah.id, "alert_rule_id": ah.alert_rule_id,
                    "competitor_id": ah.competitor_id, "message": ah.message,
                    "severity": ah.severity, "is_read": ah.is_read,
                    "triggered_at": ah.triggered_at.isoformat() if ah.triggered_at else None,
                    "status": "pending" if not ah.is_read else "acknowledged",
                    "competitor_name": competitor_name,
                }
                for ah, competitor_name in rows
            ]

    def get_full_stats(self) -> Dict:
        with self._session() as db:
            total = db.query(func.count(AlertHistory.id)).scalar()
            pending = db.query(func.count(AlertHistory.id)).filter(
                AlertHistory.is_read == False
            ).scalar()
            by_severity = [
                {"severity": s, "cnt": c}
                for s, c in db.query(
                    AlertHistory.severity, func.count(AlertHistory.id)
                ).group_by(AlertHistory.severity).order_by(func.count(AlertHistory.id).desc()).all()
            ]
            by_competitor = [
                {"name": name, "cnt": c}
                for name, c in db.query(
                    Competitor.name, func.count(AlertHistory.id)
                ).outerjoin(Competitor, AlertHistory.competitor_id == Competitor.id)
                .group_by(AlertHistory.competitor_id).order_by(func.count(AlertHistory.id).desc()).all()
            ]
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent = db.query(func.count(AlertHistory.id)).filter(
                AlertHistory.triggered_at >= cutoff
            ).scalar()
            return {
                "total": total or 0,
                "pending": pending or 0,
                "by_severity": by_severity,
                "by_competitor": by_competitor,
                "recent_24h": recent or 0,
            }

    def get_rules(self) -> List[Dict]:
        with self._session() as db:
            rows = (
                db.query(AlertRule, Competitor.name.label("competitor_name"))
                .outerjoin(Competitor, AlertRule.competitor_id == Competitor.id)
                .order_by(AlertRule.id)
                .all()
            )
            return [
                {
                    "id": r.id, "competitor_id": r.competitor_id,
                    "rule_name": r.rule_name, "rule_type": r.rule_type,
                    "condition": r.condition, "threshold": r.threshold,
                    "is_active": r.is_active,
                    "notification_method": r.notification_method,
                    "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "competitor_name": competitor_name,
                }
                for r, competitor_name in rows
            ]

    def create_rule_simple(self, competitor_id: int, rule_name: str,
                          rule_type: str, threshold: float) -> int:
        import json
        with self._session() as db:
            rule = AlertRule(
                competitor_id=competitor_id,
                rule_name=rule_name,
                rule_type=rule_type,
                threshold=threshold,
                condition=json.dumps({"field": rule_type, "op": "gt"}),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(rule)
            db.flush()
            db.refresh(rule)
            return rule.id

    def get_alert_stats(self, hours: int = 24) -> Dict:
        with self._session() as db:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            rows = (
                db.query(
                    AlertHistory.severity,
                    func.count(AlertHistory.id).label("count"),
                )
                .filter(AlertHistory.triggered_at >= cutoff)
                .group_by(AlertHistory.severity)
                .all()
            )
            by_severity = {severity: count for severity, count in rows}
            total = sum(by_severity.values())
            return {"total": total, "by_severity": by_severity, "period_hours": hours}

    def cleanup_old_alerts(self, days: int = 30):
        with self._session() as db:
            cutoff = datetime.utcnow() - timedelta(days=days)
            db.query(AlertHistory).filter(
                AlertHistory.triggered_at < cutoff,
                AlertHistory.is_read == True,
            ).delete()


alert_service = AlertService()
