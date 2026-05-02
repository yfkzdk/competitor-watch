from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.competitor import CompetitorCreate, CompetitorUpdate
from app.models.common import SuccessResponse
from app.services.competitor_service import competitor_service
from app.core.executor import run_sync_function
from app.core.database import SessionLocal
from app.core.models import Competitor, Change, MonitoringSnapshot
from sqlalchemy import func

router = APIRouter()

@router.get("/competitors", response_model=SuccessResponse)
async def get_competitors():
    """获取所有竞品列表"""
    competitors = await run_sync_function(competitor_service.get_all_competitors)
    return SuccessResponse(data=competitors)

@router.get("/v1/competitors", response_model=SuccessResponse)
async def get_competitors_v1():
    """获取所有竞品列表 (v1别名)"""
    return await get_competitors()


def _get_matrix_data():
    """获取竞品对比矩阵数据（含真实异常数和快照数）"""
    db = SessionLocal()
    try:
        comps = db.query(Competitor).order_by(Competitor.id).all()
        result = []
        for c in comps:
            anomaly_count = db.query(func.count(Change.id)).filter(
                Change.competitor_id == c.id,
                Change.severity.in_(['P0', 'P1'])
            ).scalar() or 0
            snapshot_count = db.query(func.count(MonitoringSnapshot.id)).filter(
                MonitoringSnapshot.competitor_id == c.id
            ).scalar() or 0
            result.append({
                "id": c.id, "name": c.name,
                "price_index": c.price_index or 0,
                "market_share": c.market_share or 0,
                "user_rating": c.user_rating or 0,
                "growth": c.growth or 0,
                "metrics": {},
                "anomaly_count": anomaly_count,
                "snapshot_count": snapshot_count,
            })
        return result
    finally:
        db.close()


@router.get("/competitors/matrix")
async def get_competitors_matrix():
    """获取竞品对比矩阵数据"""
    data = await run_sync_function(_get_matrix_data)
    return {"success": True, "data": data}


@router.get("/competitors/posture")
async def get_competitors_posture():
    """竞争态势5维评分卡"""
    from app.services.posture_scorer import compute_posture_scores
    data = await run_sync_function(compute_posture_scores)
    return {"success": True, "data": data}


@router.get("/competitors/{comp_id}", response_model=SuccessResponse)
async def get_competitor(comp_id: int):
    """获取单个竞品详情"""
    competitor = await run_sync_function(
        competitor_service.get_competitor_by_id, comp_id
    )
    if not competitor:
        raise HTTPException(status_code=404, detail="竞品不存在")
    return SuccessResponse(data=competitor)

@router.get("/competitors/{comp_id}/logs", response_model=SuccessResponse)
async def get_competitor_logs(
    comp_id: int,
    hours: int = Query(168, description="查询最近N小时的日志"),
    event_type: Optional[str] = Query(None, description="事件类型过滤")
):
    """获取竞品监控日志"""
    logs = await run_sync_function(
        competitor_service.get_monitoring_logs, comp_id, hours, event_type
    )
    return SuccessResponse(data=logs)

@router.post("/competitors/{comp_id}/fetch", response_model=SuccessResponse)
async def trigger_competitor_fetch(comp_id: int):
    """触发竞品数据采集"""
    result = await run_sync_function(competitor_service.trigger_fetch, comp_id)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "数据采集失败")
        )
    return SuccessResponse(data=result.get("data", {}))

@router.post("/competitors", response_model=SuccessResponse, status_code=201)
async def create_competitor(data: CompetitorCreate):
    """创建新竞品"""
    competitor = await run_sync_function(
        competitor_service.create_competitor, data
    )
    return SuccessResponse(data=competitor)

@router.put("/competitors/{comp_id}", response_model=SuccessResponse)
async def update_competitor(comp_id: int, data: CompetitorUpdate):
    """更新竞品信息"""
    competitor = await run_sync_function(
        competitor_service.update_competitor, comp_id, data
    )
    if not competitor:
        raise HTTPException(status_code=404, detail="竞品不存在")
    return SuccessResponse(data=competitor)

@router.delete("/competitors/{comp_id}", response_model=SuccessResponse)
async def delete_competitor(comp_id: int):
    """删除竞品"""
    success = await run_sync_function(
        competitor_service.delete_competitor, comp_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="竞品不存在")
    return SuccessResponse(data={"deleted": True})