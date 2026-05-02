"""
监控管理API路由
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.common import SuccessResponse
from app.services.change_detection_service import change_detection_service
from app.services.alert_service import alert_service
from app.services.scheduler_service import scheduler_service
from app.core.executor import run_sync_function
from app.core.database import SessionLocal
from app.core.models import MonitoringSnapshot
from typing import Optional

router = APIRouter()

# ========== 变化检测API ==========

@router.get("/monitoring/snapshots/{competitor_id}", response_model=SuccessResponse)
async def get_snapshots(
    competitor_id: int,
    snapshot_type: Optional[str] = Query(None, description="快照类型: price/sentiment/stock"),
    limit: int = Query(10, description="返回数量")
):
    """获取竞品快照历史"""
    def query_snapshots():
        db = SessionLocal()
        try:
            q = db.query(MonitoringSnapshot).filter(
                MonitoringSnapshot.competitor_id == competitor_id
            )
            if snapshot_type:
                q = q.filter(MonitoringSnapshot.snapshot_type == snapshot_type)
            rows = q.order_by(MonitoringSnapshot.captured_at.desc()).limit(limit).all()
            return [{
                "id": s.id,
                "competitor_id": s.competitor_id,
                "snapshot_type": s.snapshot_type,
                "content": s.content,
                "content_hash": s.content_hash,
                "url": s.url,
                "metadata": s.metadata_,
                "captured_at": s.captured_at,
            } for s in rows]
        finally:
            db.close()

@router.post("/monitoring/snapshots/compare", response_model=SuccessResponse)
async def compare_snapshot(
    competitor_id: int,
    snapshot_type: str,
    data: dict
):
    """对比快照检测变化，变化时自动触发告警"""
    changes = await run_sync_function(
        change_detection_service.compare_snapshots,
        competitor_id, snapshot_type, data
    )

    # 数据闭环：检测到变化时自动触发告警（通过alert_service，支持去重）
    if changes:
        if changes['type'] == 'price_change':
            msg = f"价格从{changes['old_price']}变为{changes['new_price']} ({changes['change_percentage']:.1f}%)"
        elif changes['type'] == 'sentiment_change':
            msg = f"情感分布变化: 正面{changes['old_sentiment']['positive']}→{changes['new_sentiment']['positive']}"
        elif changes['type'] == 'stock_change':
            msg = f"库存状态变化: {'有货' if changes['new_stock'] else '缺货'}"
        else:
            msg = f"检测到{changes['type']}变化"

        try:
            alert_id = await run_sync_function(
                alert_service.trigger_alert,
                competitor_id, changes['type'], changes['severity'], msg, changes
            )
            if alert_id:
                changes['alert_id'] = alert_id
        except Exception as e:
            import logging
            logging.error(f"触发告警失败: {e}")
            changes['alert_error'] = str(e)

    return SuccessResponse(data=changes or {"message": "无变化"})

# ========== 任务调度API ==========

@router.post("/scheduler/jobs", response_model=SuccessResponse)
async def create_monitoring_job(
    competitor_id: int,
    frequency: int = Query(60, description="监控频率（分钟）")
):
    """创建监控任务"""
    job_id = await scheduler_service.add_monitoring_job(competitor_id, frequency)
    return SuccessResponse(data={"job_id": job_id, "frequency": frequency})

@router.delete("/scheduler/jobs/{competitor_id}", response_model=SuccessResponse)
async def delete_monitoring_job(competitor_id: int):
    """删除监控任务"""
    await scheduler_service.remove_monitoring_job(competitor_id)
    return SuccessResponse(data={"deleted": True})

@router.put("/scheduler/jobs/{competitor_id}", response_model=SuccessResponse)
async def update_job_frequency(
    competitor_id: int,
    new_frequency: int = Query(..., description="新频率（分钟）")
):
    """更新任务频率"""
    await scheduler_service.update_job_frequency(competitor_id, new_frequency)
    return SuccessResponse(data={"updated": True, "frequency": new_frequency})

@router.get("/scheduler/jobs", response_model=SuccessResponse)
async def get_all_jobs():
    """获取所有任务"""
    jobs = scheduler_service.get_jobs()
    return SuccessResponse(data=jobs)

@router.get("/scheduler/jobs/{competitor_id}", response_model=SuccessResponse)
async def get_job_status(competitor_id: int):
    """获取任务状态"""
    status = scheduler_service.get_job_status(competitor_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=status)
