"""
告警中心 API — 告警历史、统计、规则管理
"""
from typing import Optional
from fastapi import APIRouter, Query
from app.core.executor import run_sync_function
from app.models.common import SuccessResponse
from app.services.alert_service import alert_service

router = APIRouter()


@router.get("/alerts", response_model=SuccessResponse)
async def api_get_alerts(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    data = await run_sync_function(alert_service.get_alerts, severity, status, limit)
    return SuccessResponse(data=data)


@router.get("/alerts/stats")
async def api_alert_stats():
    data = await run_sync_function(alert_service.get_full_stats)
    return {"success": True, "data": data}


@router.get("/alerts/rules", response_model=SuccessResponse)
async def api_alert_rules():
    data = await run_sync_function(alert_service.get_rules)
    return SuccessResponse(data=data)


@router.post("/alerts/{alert_id}/acknowledge")
async def api_acknowledge_alert(alert_id: int):
    await run_sync_function(alert_service.acknowledge_alert, alert_id)
    return {"success": True, "message": "已确认"}


@router.post("/alerts/rules")
async def api_create_rule(
    competitor_id: int = Query(...),
    rule_name: str = Query(...),
    rule_type: str = Query("price_change"),
    threshold: float = Query(5.0),
):
    rule_id = await run_sync_function(
        alert_service.create_rule_simple, competitor_id, rule_name, rule_type, threshold
    )
    return {"success": True, "data": {"id": rule_id}}
