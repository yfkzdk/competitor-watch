from app.core.models import Competitor, MonitoringLog
from app.models.competitor import CompetitorCreate, CompetitorUpdate
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from contextlib import contextmanager


class CompetitorService:
    """竞品业务逻辑 — SQLAlchemy ORM 实现"""

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

    def _row_to_dict(self, comp: Competitor) -> Dict:
        return {
            "id": comp.id, "name": comp.name, "url": comp.url,
            "category": comp.category or "未分类", "status": comp.status or "active",
            "priority": comp.priority or "medium", "description": comp.description or "",
            "type": comp.type or "all", "frequency": comp.frequency or "15",
            "market_share": comp.market_share or 0, "price_index": comp.price_index or 90,
            "user_rating": comp.user_rating or 4.0, "growth": comp.growth or 0,
            "feature_count": comp.feature_count or 0,
            "innovation_velocity": comp.innovation_velocity or 0,
            "security_mentions": comp.security_mentions or 0,
            "last_checked": comp.last_checked.isoformat() if comp.last_checked else None,
            "created_at": comp.created_at.isoformat() if comp.created_at else None,
            "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
            "metrics": {
                "feature_count": comp.feature_count or 0,
                "price_index": comp.price_index or 90,
                "innovation_velocity": comp.innovation_velocity or 0,
                "security_mentions": comp.security_mentions or 0,
                "market_share": comp.market_share or 0,
                "user_rating": comp.user_rating or 4.0,
                "growth": comp.growth or 0,
            },
        }

    def get_all_competitors(self) -> List[Dict]:
        with self._session() as db:
            rows = db.query(Competitor).order_by(Competitor.id).all()
            return [self._row_to_dict(c) for c in rows]

    def get_competitor_by_id(self, comp_id: int) -> Optional[Dict]:
        with self._session() as db:
            comp = db.query(Competitor).filter(Competitor.id == comp_id).first()
            if comp is None:
                return None
            return self._row_to_dict(comp)

    def create_competitor(self, data: CompetitorCreate) -> Dict:
        with self._session() as db:
            comp = Competitor(
                name=data.name, url=data.url, status=data.status,
                type=data.type, frequency=data.frequency,
                market_share=data.market_share, price_index=data.price_index,
                user_rating=data.user_rating, growth=data.growth,
                created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
            )
            db.add(comp)
            db.flush()
            db.refresh(comp)
            return self._row_to_dict(comp)

    def update_competitor(self, comp_id: int, data: CompetitorUpdate) -> Optional[Dict]:
        with self._session() as db:
            comp = db.query(Competitor).filter(Competitor.id == comp_id).first()
            if comp is None:
                return None
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(comp, field, value)
            comp.updated_at = datetime.utcnow()
            db.flush()
            db.refresh(comp)
            return self._row_to_dict(comp)

    def get_monitoring_logs(self, comp_id: int, hours: int = 168,
                            event_type: Optional[str] = None) -> List[Dict]:
        with self._session() as db:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            q = db.query(MonitoringLog).filter(
                MonitoringLog.competitor_id == comp_id,
                MonitoringLog.checked_at >= cutoff,
            )
            if event_type:
                q = q.filter(MonitoringLog.monitoring_type == event_type)
            logs = q.order_by(MonitoringLog.checked_at.desc()).all()
            return [
                {
                    "id": log.id, "competitor_id": log.competitor_id,
                    "status": log.status, "response_time": log.response_time,
                    "error_message": log.error_message, "url": log.url,
                    "content_hash": log.content_hash, "content_length": log.content_length,
                    "monitoring_type": log.monitoring_type, "details": log.details,
                    "timestamp": log.checked_at.isoformat() if log.checked_at else None,
                    "event_type": log.monitoring_type,
                }
                for log in logs
            ]

    def trigger_fetch(self, comp_id: int) -> Dict:
        with self._session() as db:
            comp = db.query(Competitor).filter(Competitor.id == comp_id).first()
            if not comp:
                return {"success": False, "error": "竞品不存在"}
            comp.last_checked = datetime.utcnow()

            try:
                from app.services.data_pipeline import data_pipeline
                from app.services.scraper_engine import scraper_engine
                fetch_result = scraper_engine.run(comp_id)
                pipeline_result = data_pipeline.run(comp_id, fetch_result)
                return {
                    "success": True,
                    "data": {
                        "fetched": pipeline_result["fetch_events"],
                        "changes": pipeline_result["changes_detected"],
                        "alerts_triggered": pipeline_result["alerts_triggered"],
                    },
                }
            except Exception as e:
                return {"success": False, "error": str(e), "status": "ERROR"}

    def delete_competitor(self, comp_id: int) -> bool:
        with self._session() as db:
            comp = db.query(Competitor).filter(Competitor.id == comp_id).first()
            if comp is None:
                return False
            db.delete(comp)
            db.flush()
            return True


competitor_service = CompetitorService()
