from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# ========== 竞品模型 ==========
class CompetitorBase(BaseModel):
    """竞品基础模型"""
    name: str = Field(..., description="竞品名称", min_length=1, max_length=100)
    url: str = Field(..., description="竞品URL")
    status: str = Field("monitoring", description="状态")
    type: str = Field("all", description="类型")
    frequency: str = Field("15", description="监控频率（分钟）")

class CompetitorCreate(CompetitorBase):
    """创建竞品请求模型"""
    market_share: Optional[float] = Field(0, ge=0, le=100)
    price_index: Optional[float] = Field(90, ge=0)
    user_rating: Optional[float] = Field(4.0, ge=0, le=5)
    growth: Optional[float] = Field(0)

class CompetitorUpdate(BaseModel):
    """更新竞品请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None
    market_share: Optional[float] = Field(None, ge=0, le=100)
    price_index: Optional[float] = Field(None, ge=0)
    user_rating: Optional[float] = Field(None, ge=0, le=5)
    growth: Optional[float] = None

class CompetitorMetrics(BaseModel):
    """竞品指标"""
    feature_count: int = 0
    price_index: float = 90.0
    innovation_velocity: float = 0.0
    security_mentions: int = 0
    market_share: float = 0.0
    user_rating: float = 4.0
    growth: float = 0.0

class CompetitorResponse(CompetitorBase):
    """竞品响应模型"""
    id: int
    created_at: str
    updated_at: str
    metrics: CompetitorMetrics

    model_config = ConfigDict(from_attributes=True)