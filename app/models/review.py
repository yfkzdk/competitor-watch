from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ========== 评论模型 ==========
class ReviewResponse(BaseModel):
    """评论响应"""
    id: int
    competitor_id: int
    user_name: str
    rating: float
    content: str
    sentiment: str
    sentiment_score: float
    keywords: List[str]
    timestamp: str
    source: str

class SentimentDistribution(BaseModel):
    """情感分布"""
    positive: int = 0
    neutral: int = 0
    negative: int = 0

class SentimentResponse(BaseModel):
    """情感分析响应"""
    competitor_id: int
    period_days: int
    sentiment_distribution: SentimentDistribution
    average_sentiment_score: float
    top_keywords: List[Dict[str, Any]]

class ReviewStatsResponse(BaseModel):
    """评论统计响应"""
    positive: int
    neutral: int
    negative: int