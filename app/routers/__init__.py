# API路由层
from app.routers.competitors import router as competitors_router
from app.routers.prices import router as prices_router
from app.routers.reviews import router as reviews_router
from app.routers.monitoring import router as monitoring_router

__all__ = [
    'competitors_router',
    'prices_router',
    'reviews_router',
    'monitoring_router'
]
