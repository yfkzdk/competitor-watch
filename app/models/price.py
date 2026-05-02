from pydantic import BaseModel, Field
from typing import List, Optional

# ========== 价格模型 ==========
class PriceHistoryItem(BaseModel):
    """价格历史记录"""
    id: int
    competitor_id: int
    product_name: str
    price: float
    currency: str = "CNY"
    billing_cycle: Optional[str] = None
    timestamp: str
    source: str
    confidence: float = 1.0

class PriceStatistics(BaseModel):
    """价格统计"""
    min_price: float
    max_price: float
    avg_price: float
    count: int
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None

class PriceHistoryResponse(BaseModel):
    """价格历史响应"""
    competitor_id: int
    product_name: Optional[str] = None
    prices: List[PriceHistoryItem]
    statistics: PriceStatistics

class PriceCompareItem(BaseModel):
    """价格对比项"""
    competitor_id: int
    product_name: str
    price: float
    currency: str
    timestamp: str

class PriceCompareAnalysis(BaseModel):
    """价格对比分析"""
    min_price: float
    max_price: float
    price_range: float
    avg_price: float
    best_value: Optional[PriceCompareItem] = None

class PriceCompareResponse(BaseModel):
    """价格对比响应"""
    product_name: str
    comparison: List[PriceCompareItem]
    analysis: PriceCompareAnalysis

class PricePrediction(BaseModel):
    """价格预测项"""
    date: str
    predicted_price: float
    confidence_lower: float
    confidence_upper: float

class PricePredictionResponse(BaseModel):
    """价格预测响应"""
    historical: Optional[List[PriceHistoryItem]] = None
    predictions: List[PricePrediction]