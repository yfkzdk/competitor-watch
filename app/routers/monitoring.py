from fastapi import APIRouter, Query
from app.models.common import SuccessResponse
from app.core.database import SessionLocal
from app.core.models import Competitor, PriceHistory, UserReview, Change, AlertHistory
from app.core.executor import run_sync_function
from sqlalchemy import func
from typing import Dict

router = APIRouter()

def get_monitoring_stats_sync() -> Dict:
    """获取监控统计（同步函数）"""
    from app.services.monitoring_service import monitoring_service
    return monitoring_service.get_monitoring_stats()

def get_dashboard_stats_sync() -> Dict:
    """获取仪表板统计（同步函数）"""
    db = SessionLocal()
    try:
        competitors_total = db.query(func.count(Competitor.id)).scalar() or 0
        active_count = db.query(func.count(Competitor.id)).filter(
            Competitor.status == 'active'
        ).scalar() or 0
        price_total = db.query(func.count(PriceHistory.id)).scalar() or 0
        review_total = db.query(func.count(UserReview.id)).scalar() or 0
        changes_detected = db.query(func.count(Change.id)).filter(
            Change.is_read == False
        ).scalar() or 0
        alerts_pending = db.query(func.count(AlertHistory.id)).filter(
            AlertHistory.is_read == False
        ).scalar() or 0

        return {
            'competitorsTotal': competitors_total,
            'activeCompetitors': active_count,
            'priceRecords': price_total,
            'reviewRecords': review_total,
            'changesDetected': changes_detected,
            'alertsPending': alerts_pending,
        }
    finally:
        db.close()

@router.get("/monitoring/stats", response_model=SuccessResponse)
async def get_monitoring_stats():
    """获取监控统计"""
    result = await run_sync_function(get_monitoring_stats_sync)
    return SuccessResponse(data=result)

@router.get("/dashboard/stats", response_model=SuccessResponse)
async def get_dashboard_stats():
    """获取仪表板统计"""
    result = await run_sync_function(get_dashboard_stats_sync)
    return SuccessResponse(data=result)

@router.get("/reviews/stats", response_model=SuccessResponse)
async def get_review_stats(
    competitor_id: int = Query(..., description="竞品ID")
):
    """获取评论统计"""
    from app.services.review_service import review_service
    result = await run_sync_function(
        review_service.get_review_stats, competitor_id
    )
    return SuccessResponse(data=result)