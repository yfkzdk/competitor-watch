"""Monitoring service — check scheduling, stats, and log management. SQLAlchemy ORM."""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import contextmanager

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.core.models import MonitoringLog, Competitor


class MonitoringService:
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

    def get_monitoring_stats(self, competitor_id: int = None) -> Dict:
        with self._session() as db:
            q = db.query(
                func.count(MonitoringLog.id).label("total_checks"),
                func.sum(case((MonitoringLog.status == "success", 1), else_=0)).label("success_count"),
                func.sum(case((MonitoringLog.status == "failed", 1), else_=0)).label("fail_count"),
                func.avg(MonitoringLog.response_time).label("avg_response_time"),
                func.max(MonitoringLog.checked_at).label("last_check"),
            )
            if competitor_id:
                q = q.filter(MonitoringLog.competitor_id == competitor_id)

            row = q.first()

        if not row or row.total_checks is None:
            return {"total_checks": 0, "success_rate": 0, "avg_response_time": 0}

        total = row.total_checks or 0
        success = row.success_count or 0
        return {
            "total_checks": total,
            "success_count": success,
            "fail_count": row.fail_count or 0,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
            "avg_response_time": round(row.avg_response_time or 0, 0),
            "last_check": row.last_check,
        }

    def get_recent_logs(self, competitor_id: int = None, limit: int = 20) -> List[Dict]:
        with self._session() as db:
            q = (
                db.query(MonitoringLog, Competitor.name.label("competitor_name"))
                .join(Competitor, MonitoringLog.competitor_id == Competitor.id)
            )
            if competitor_id:
                q = q.filter(MonitoringLog.competitor_id == competitor_id)
            rows = q.order_by(MonitoringLog.checked_at.desc()).limit(limit).all()

            results = []
            for ml, comp_name in rows:
                d = {
                    "id": ml.id,
                    "competitor_id": ml.competitor_id,
                    "status": ml.status,
                    "response_time": ml.response_time,
                    "error_message": ml.error_message,
                    "url": ml.url,
                    "content_hash": ml.content_hash,
                    "content_length": ml.content_length,
                    "monitoring_type": ml.monitoring_type,
                    "details": ml.details,
                    "checked_at": ml.checked_at,
                    "competitor_name": comp_name,
                }
                results.append(d)
            return results

    def get_monitoring_history(self, competitor_id: int, days: int = 7) -> List[Dict]:
        since = datetime.utcnow() - timedelta(days=days)
        with self._session() as db:
            rows = (
                db.query(
                    func.date(MonitoringLog.checked_at).label("date"),
                    func.count(MonitoringLog.id).label("total"),
                    func.sum(case((MonitoringLog.status == "success", 1), else_=0)).label("success"),
                    func.avg(MonitoringLog.response_time).label("avg_time"),
                )
                .filter(
                    MonitoringLog.competitor_id == competitor_id,
                    MonitoringLog.checked_at >= since,
                )
                .group_by(func.date(MonitoringLog.checked_at))
                .order_by(func.date(MonitoringLog.checked_at))
                .all()
            )
            return [
                {"date": str(r.date), "total": r.total, "success": r.success or 0, "avg_time": r.avg_time}
                for r in rows
            ]

    def add_log(self, competitor_id: int, status: str, response_time: int,
                error_message: str = "", url: str = "", monitoring_type: str = "full_scan") -> int:
        with self._session() as db:
            log = MonitoringLog(
                competitor_id=competitor_id,
                status=status,
                response_time=response_time,
                error_message=error_message,
                url=url,
                content_hash="",
                content_length=0,
                monitoring_type=monitoring_type,
                details={},
                checked_at=datetime.utcnow(),
            )
            db.add(log)
            db.flush()
            return log.id


monitoring_service = MonitoringService()
