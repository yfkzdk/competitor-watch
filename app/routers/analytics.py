"""
分析API路由 - 趋势/异常/相关性/摘要
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.common import SuccessResponse
from app.services.analytics_service import analytics_service
from app.core.executor import run_sync_function
from typing import Optional

router = APIRouter()


@router.get("/analytics/trend/{competitor_id}", response_model=SuccessResponse)
async def get_trend_analysis(
    competitor_id: int,
    metric: str = Query('price', description="指标类型: price/stock"),
    days: int = Query(7, ge=1, le=90, description="分析天数")
):
    """获取趋势分析（线性回归+移动平均+方向判断）"""
    result = await run_sync_function(
        analytics_service.get_trend_analysis, competitor_id, metric, days
    )
    return SuccessResponse(data=result)


@router.get("/analytics/anomalies/{competitor_id}", response_model=SuccessResponse)
async def detect_anomalies(
    competitor_id: int,
    metric: str = Query('price', description="指标类型: price/stock"),
    days: int = Query(30, ge=1, le=90, description="检测窗口天数"),
    sensitivity: float = Query(2.0, ge=1.0, le=4.0, description="Z-score阈值")
):
    """异常检测（Z-score + IQR双重检测）"""
    result = await run_sync_function(
        analytics_service.detect_anomalies, competitor_id, metric, days, sensitivity
    )
    return SuccessResponse(data=result)


@router.get("/analytics/correlation", response_model=SuccessResponse)
async def get_correlation(
    competitor_id_1: int = Query(..., description="竞品1 ID"),
    competitor_id_2: int = Query(..., description="竞品2 ID"),
    metric: str = Query('price', description="指标类型"),
    days: int = Query(30, ge=1, le=90, description="分析天数")
):
    """计算两个竞品的相关系数"""
    result = await run_sync_function(
        analytics_service.get_correlation, competitor_id_1, competitor_id_2, metric, days
    )
    return SuccessResponse(data=result)


@router.get("/analytics/correlation-matrix", response_model=SuccessResponse)
async def get_correlation_matrix(
    metric: str = Query('price', description="指标类型"),
    days: int = Query(30, ge=1, le=90, description="分析天数")
):
    """获取所有竞品间相关性矩阵"""
    result = await run_sync_function(
        analytics_service.get_all_correlations, metric, days
    )
    return SuccessResponse(data=result)


@router.get("/analytics/summary/{competitor_id}", response_model=SuccessResponse)
async def get_competitor_summary(
    competitor_id: int,
    days: int = Query(7, ge=1, le=90, description="摘要天数")
):
    """竞品综合分析摘要"""
    result = await run_sync_function(
        analytics_service.get_competitor_summary, competitor_id, days
    )
    return SuccessResponse(data=result)
