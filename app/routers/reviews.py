"""Reviews router — sentiment analysis and review data endpoints."""
from fastapi import APIRouter, Query
from app.models.common import SuccessResponse
from app.services.review_service import review_service
from app.core.executor import run_sync_function

router = APIRouter()


@router.get("/sentiment", response_model=SuccessResponse)
async def get_sentiment(
    competitor_id: int = Query(..., description="竞品ID"),
    days: int = Query(30, description="统计天数"),
):
    """获取竞品的情感分析汇总"""
    result = await run_sync_function(review_service.get_sentiment_summary, competitor_id, days)
    return SuccessResponse(data=result)


@router.get("/sentiment/trend", response_model=SuccessResponse)
async def get_sentiment_trend(
    competitor_id: int = Query(..., description="竞品ID"),
    days: int = Query(30, description="趋势天数"),
):
    """获取竞品情感趋势（按日分组）"""
    result = await run_sync_function(review_service.get_sentiment_trend, competitor_id, days)
    return SuccessResponse(data=result)


@router.get("/stats", response_model=SuccessResponse)
async def get_review_stats(
    competitor_id: int = Query(None, description="竞品ID（可选，不传则返回全局统计）"),
):
    """获取评论统计"""
    result = await run_sync_function(review_service.get_review_stats, competitor_id)
    return SuccessResponse(data=result)


@router.get("", response_model=SuccessResponse)
@router.get("/list", response_model=SuccessResponse)
async def get_reviews(
    competitor_id: int = Query(..., description="竞品ID"),
    limit: int = Query(50, description="每页数量"),
    offset: int = Query(0, description="偏移量"),
):
    """获取竞品的评论列表"""
    result = await run_sync_function(review_service.get_reviews, competitor_id, limit, offset)
    return SuccessResponse(data=result)
