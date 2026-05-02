from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置（支持 .env 环境变量覆盖）"""
    app_name: str = "竞品监控系统 API"
    app_version: str = "2.0"
    debug: bool = False

    # 数据库配置
    database_path: str = "competitor_watch.db"

    # 线程池配置
    max_workers: int = 10

    # CORS配置
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]

    # API 安全
    api_key: str = ""  # 空则不启用认证
    rate_limit_per_minute: int = 60

    # 通知
    notification_config_path: str = "config/notifications.json"

    # Demo 模式（启用模拟实时监控）
    demo_mode: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
