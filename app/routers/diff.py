"""
Diff可视化API路由 - 内容对比+变化时间线
"""
from fastapi import APIRouter, Query
from app.models.common import SuccessResponse
from app.services.diff_service import diff_service
from app.core.database import SessionLocal
from app.core.models import Change, Competitor
from app.core.executor import run_sync_function
from typing import Optional

router = APIRouter()


@router.get("/diff/changes", response_model=SuccessResponse)
async def get_recent_changes(
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
):
    """获取最近的变更列表（跨所有竞品）"""
    db = SessionLocal()
    try:
        rows = db.query(Change, Competitor.name).outerjoin(
            Competitor, Change.competitor_id == Competitor.id
        ).order_by(Change.detected_at.desc()).limit(limit).all()

        data = []
        for change, comp_name in rows:
            data.append({
                "id": change.id,
                "competitor_id": change.competitor_id,
                "competitor_name": comp_name,
                "change_type": change.change_type,
                "field_name": change.field_name,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "severity": change.severity,
                "detected_at": change.detected_at,
                "is_read": change.is_read,
            })
        return SuccessResponse(data=data)
    finally:
        db.close()


@router.get("/diff/compare/{competitor_id}", response_model=SuccessResponse)
async def compare_snapshots(
    competitor_id: int,
    snapshot_type: Optional[str] = Query(None, description="快照类型: price/stock")
):
    """对比最近两次快照差异"""
    result = await run_sync_function(
        diff_service.compare_snapshots, competitor_id, snapshot_type
    )
    return SuccessResponse(data=result)


@router.get("/diff/scrape/{competitor_id}", response_model=SuccessResponse)
async def compare_scrape_results(competitor_id: int):
    """对比最近两次采集结果差异"""
    result = await run_sync_function(
        diff_service.compare_scrape_results, competitor_id
    )
    return SuccessResponse(data=result)


@router.get("/diff/timeline/{competitor_id}", response_model=SuccessResponse)
async def get_change_timeline(
    competitor_id: int,
    days: int = Query(7, ge=1, le=90, description="时间线天数")
):
    """获取变化时间线"""
    result = await run_sync_function(
        diff_service.get_change_timeline, competitor_id, days
    )
    return SuccessResponse(data=result)


@router.get("/diff/history/{competitor_id}", response_model=SuccessResponse)
async def get_scrape_history(
    competitor_id: int,
    limit: int = Query(20, ge=1, le=100, description="历史条数")
):
    """获取采集历史（含变化标记）"""
    result = await run_sync_function(
        diff_service.get_scrape_history, competitor_id, limit
    )
    return SuccessResponse(data=result)
