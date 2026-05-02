"""
P4/P5 路由: 竞品对比、健康检查、导出、通知配置
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.core.models import Competitor, Change, MonitoringLog
from sqlalchemy import func

router = APIRouter(prefix="/api", tags=["enhanced"])


# ── P4: 竞品多维对比 ──────────────────────────────────────────

@router.get("/comparison")
async def get_comparison_matrix(
    competitor_ids: Optional[str] = Query(None, description="逗号分隔的竞品ID"),
    metrics: Optional[str] = Query(None, description="逗号分隔的指标名"),
):
    """竞品多维对比矩阵"""
    from app.services.comparison_service import comparison_service

    ids = None
    if competitor_ids:
        try:
            ids = [int(x.strip()) for x in competitor_ids.split(",")]
        except ValueError:
            raise HTTPException(400, "competitor_ids 格式错误，需要逗号分隔的数字")

    metric_list = None
    if metrics:
        metric_list = [x.strip() for x in metrics.split(",")]

    return comparison_service.get_comparison_matrix(ids, metric_list)


@router.get("/comparison/radar")
async def get_radar_chart(
    competitor_ids: Optional[str] = Query(None, description="逗号分隔的竞品ID"),
):
    """竞品雷达图数据（归一化 0-100）"""
    from app.services.comparison_service import comparison_service

    ids = None
    if competitor_ids:
        try:
            ids = [int(x.strip()) for x in competitor_ids.split(",")]
        except ValueError:
            raise HTTPException(400, "competitor_ids 格式错误")

    return comparison_service.get_radar_data(ids)


# ── P4: 真实健康检查 ──────────────────────────────────────────

@router.get("/health")
async def health_check():
    """系统健康检查（DB + 调度器 + 最近采集）"""
    checks = {}

    # DB 连通性
    try:
        db = SessionLocal()
        try:
            cnt = db.query(func.count(Competitor.id)).scalar() or 0
            checks["database"] = {"status": "ok", "competitors": cnt}
        finally:
            db.close()
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)[:100]}

    # 调度器状态
    try:
        from app.services.scheduler_service import scheduler_service
        jobs = scheduler_service.get_jobs()
        checks["scheduler"] = {
            "status": "running" if scheduler_service.scheduler.running else "stopped",
            "active_jobs": len(jobs),
        }
    except Exception as e:
        checks["scheduler"] = {"status": "error", "message": str(e)[:100]}

    # 最近采集
    try:
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_cnt = db.query(func.count(MonitoringLog.id)).filter(
                MonitoringLog.checked_at >= cutoff
            ).scalar() or 0
            checks["recent_fetch"] = {"status": "ok", "logs_last_hour": recent_cnt}
        finally:
            db.close()
    except Exception:
        checks["recent_fetch"] = {"status": "unknown"}

    overall = "healthy" if all(c.get("status") in ("ok", "running") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


# ── P5: 导出 ──────────────────────────────────────────────────

@router.get("/export/competitors")
async def export_competitors(
    format: str = Query("json", regex="^(json|csv)$"),
    competitor_ids: Optional[str] = Query(None),
):
    """导出竞品数据 (JSON/CSV)"""
    db = SessionLocal()
    try:
        if competitor_ids:
            ids = [int(x.strip()) for x in competitor_ids.split(",")]
            rows = db.query(Competitor).filter(Competitor.id.in_(ids)).all()
        else:
            rows = db.query(Competitor).order_by(Competitor.id).all()

        if format == "csv":
            import io
            import csv

            output = io.StringIO()
            if rows:
                fieldnames = [c.name for c in Competitor.__table__.columns]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    d = {}
                    for fn in fieldnames:
                        val = getattr(r, fn)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        d[fn] = val
                    writer.writerow(d)
            return {"format": "csv", "data": output.getvalue()}

        return {"format": "json", "data": [{c.name: getattr(r, c.name) for c in Competitor.__table__.columns} for r in rows]}
    finally:
        db.close()


@router.get("/export/changes")
async def export_changes(
    format: str = Query("json", regex="^(json|csv)$"),
    competitor_id: Optional[int] = Query(None),
    days: int = Query(7, description="最近N天"),
):
    """导出变更记录 (JSON/CSV)"""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = db.query(Change).filter(Change.detected_at >= cutoff)
        if competitor_id:
            q = q.filter(Change.competitor_id == competitor_id)
        rows = q.order_by(Change.detected_at.desc()).all()

        if format == "csv":
            import io
            import csv

            output = io.StringIO()
            if rows:
                fieldnames = [c.name for c in Change.__table__.columns]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    d = {}
                    for fn in fieldnames:
                        val = getattr(r, fn)
                        if isinstance(val, datetime):
                            val = val.isoformat()
                        d[fn] = val
                    writer.writerow(d)
            return {"format": "csv", "data": output.getvalue()}

        return {"format": "json", "data": [{c.name: getattr(r, c.name) for c in Change.__table__.columns} for r in rows]}
    finally:
        db.close()


# ── P5: 通知配置 ──────────────────────────────────────────────

@router.get("/notifications/channels")
async def list_notification_channels():
    """列出已配置的通知通道"""
    from app.services.notification_service import notification_service
    return {"channels": notification_service.list_channels()}


@router.post("/notifications/test")
async def test_notification_channel(channel: str = Query(..., description="通道名称")):
    """测试通知通道连通性"""
    from app.services.notification_service import notification_service
    result = notification_service.test_channel(channel)
    return result


@router.post("/notifications/send")
async def send_notification(
    message: str = Query(..., description="消息内容"),
    channels: Optional[str] = Query(None, description="逗号分隔的通道名，为空则全部"),
):
    """发送通知消息"""
    from app.services.notification_service import notification_service
    ch_list = channels.split(",") if channels else None
    result = notification_service.send(message, channels=ch_list)
    return result
