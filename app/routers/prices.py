from fastapi import APIRouter, HTTPException, Query
from app.models.common import SuccessResponse
from app.services.price_service import price_service
from app.core.executor import run_sync_function
from typing import List

router = APIRouter()

@router.get("/history", response_model=SuccessResponse)
async def get_price_history(
    competitor_id: int = Query(..., description="竞品ID（必填）"),
    product_name: str = Query(None, description="产品名称（可选）"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD（可选）"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD（可选）"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数限制")
):
    """获取价格历史数据"""
    result = await run_sync_function(
        price_service.get_price_history,
        competitor_id, product_name, start_date, end_date, limit
    )
    return SuccessResponse(data=result)

@router.get("/compare", response_model=SuccessResponse)
async def compare_prices(
    competitor_ids: str = Query(..., description="竞品ID列表，逗号分隔"),
    product_name: str = Query(..., description="产品名称")
):
    """多竞品价格对比"""
    ids = [int(id.strip()) for id in competitor_ids.split(',')]
    result = await run_sync_function(
        price_service.compare_prices, ids, product_name
    )
    return SuccessResponse(data=result)

@router.get("/predict", response_model=SuccessResponse)
async def predict_price(
    competitor_id: int = Query(..., description="竞品ID"),
    product_name: str = Query(..., description="产品名称"),
    days: int = Query(7, ge=1, le=30, description="预测天数"),
    historical_days: int = Query(90, ge=30, le=365, description="历史数据天数")
):
    """预测未来价格"""
    result = await run_sync_function(
        price_service.predict_price,
        competitor_id, product_name, days, historical_days
    )

    if not result.get('success'):
        raise HTTPException(
            status_code=400,
            detail=result.get('error', '预测失败')
        )

    return SuccessResponse(data=result.get('data'))