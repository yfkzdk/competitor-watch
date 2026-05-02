import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.routers import competitors_router, prices_router, reviews_router, monitoring_router
from app.routers.realtime import router as realtime_router
from app.routers.monitoring_management import router as monitoring_management_router
from app.routers.scraper_management import router as scraper_management_router
from app.routers.analytics import router as analytics_router
from app.routers.diff import router as diff_router
from app.routers.enhanced import router as enhanced_router
from app.routers.system import router as system_router
from app.core.config import settings
from app.core.executor import executor
from app.services.scheduler_service import scheduler_service
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="竞品监控系统 API — 采集→检测→告警闭环",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── API 限流 ──────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ── API Key 认证中间件 ────────────────────────────────────────
class APIKeyMiddleware(BaseHTTPMiddleware):
    """API Key 认证（仅在 settings.api_key 非空时启用）"""

    PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json", "/static"}

    async def dispatch(self, request: Request, call_next):
        if not settings.api_key:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API Key")

        return await call_next(request)


app.add_middleware(APIKeyMiddleware)

# 静态文件目录
STATIC_DIR = Path(__file__).parent.parent / "dashboard" / "static"
TEMPLATES_DIR = Path(__file__).parent.parent / "dashboard" / "templates"

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# 注册路由
app.include_router(competitors_router, prefix="/api", tags=["竞品管理"])
app.include_router(prices_router, prefix="/api/v1/prices", tags=["价格分析"])
app.include_router(reviews_router, prefix="/api/v1/reviews", tags=["评论分析"])
app.include_router(monitoring_router, prefix="/api", tags=["监控统计"])
app.include_router(realtime_router, tags=["实时监控"])
app.include_router(monitoring_management_router, prefix="/api", tags=["监控管理"])
app.include_router(scraper_management_router, prefix="/api", tags=["采集管理"])
app.include_router(analytics_router, prefix="/api", tags=["数据分析"])
app.include_router(diff_router, prefix="/api", tags=["差异对比"])
app.include_router(enhanced_router, tags=["增强功能"])
app.include_router(system_router, prefix="/api", tags=["系统与报告"])

# 告警中心路由
from app.routers.alerts import router as alerts_router
app.include_router(alerts_router, prefix="/api", tags=["告警中心"])

# ========== 页面路由 ==========
@app.get("/", tags=["页面"])
async def index_page():
    """主页"""
    return FileResponse(str(TEMPLATES_DIR / "index_v2.html"))

@app.get("/v1", tags=["页面"])
async def index_v1_page():
    """主页（旧版，重定向到新版）"""
    return FileResponse(str(TEMPLATES_DIR / "index_v2.html"))

@app.get("/v3", tags=["页面"])
async def index_v3_page():
    """主页（Vue 3 组件化架构）"""
    return FileResponse(str(TEMPLATES_DIR / "index_v3.html"))

@app.get("/product", tags=["页面"])
@app.get("/product/", tags=["页面"])
async def product_page():
    """产品详情页"""
    return FileResponse(str(TEMPLATES_DIR / "product_detail_v2.html"))

@app.get("/product/v2", tags=["页面"])
async def product_v2_page():
    """产品详情页v2"""
    return FileResponse(str(TEMPLATES_DIR / "product_detail_v2.html"))

@app.get("/diagnostic", tags=["页面"])
async def diagnostic_page():
    """诊断页面"""
    return FileResponse(str(TEMPLATES_DIR / "diagnostic.html"))

@app.get("/websocket-test", tags=["页面"])
async def websocket_test_page():
    """WebSocket测试页面"""
    return FileResponse(str(TEMPLATES_DIR / "websocket_test.html"))

@app.get("/monitoring/dashboard", tags=["页面"])
async def monitoring_dashboard_page():
    """监控仪表板页面"""
    return FileResponse(str(TEMPLATES_DIR / "monitoring_dashboard.html"))

@app.get("/report", tags=["页面"])
async def report_page():
    """竞品分析报告页面"""
    return FileResponse(str(TEMPLATES_DIR / "report_v2.html"))

@app.get("/alerts", tags=["页面"])
async def alerts_page():
    """告警中心页面"""
    return FileResponse(str(TEMPLATES_DIR / "alerts_v2.html"))

# 健康检查端点（真实探测）
@app.get("/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    checks = {}

    try:
        from app.core.database import SessionLocal
        from app.core.models import Competitor
        db = SessionLocal()
        try:
            count = db.query(Competitor).count()
            checks["database"] = {"status": "ok", "competitors": count}
        finally:
            db.close()
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)[:100]}

    try:
        checks["scheduler"] = {
            "status": "running" if scheduler_service.scheduler.running else "stopped",
            "active_jobs": len(scheduler_service.jobs),
        }
    except Exception as e:
        checks["scheduler"] = {"status": "error", "message": str(e)[:100]}

    overall = "healthy" if all(c.get("status") in ("ok", "running") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "version": settings.app_version}


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    await scheduler_service.start()

    # Demo 模式: 启动实时监控模拟
    if settings.demo_mode:
        from app.services.simulation_service import simulation
        simulation.start()

    logger.info(f"{settings.app_name} v{settings.app_version} 启动完成")
    logger.info(f"API Key 认证: {'启用' if settings.api_key else '未启用'}")
    logger.info(f"数据库: {settings.database_path}")
    logger.info(f"线程池: max_workers={settings.max_workers}")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    await scheduler_service.shutdown()
    executor.shutdown(wait=True)
    logger.info("应用已关闭")


def main():
    """Entry point for `competitor-watch` console script."""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
