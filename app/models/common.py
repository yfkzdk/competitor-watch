from pydantic import BaseModel
from typing import Any, Optional

# ========== 通用响应模型 ==========
class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    data: Any

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    error_code: Optional[str] = None