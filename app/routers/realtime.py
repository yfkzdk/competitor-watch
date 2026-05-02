"""
实时监控WebSocket路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import manager
from app.core.database import SessionLocal
from app.core.models import Competitor, PriceHistory, UserReview, MonitoringLog
from sqlalchemy import func, case
import asyncio
from datetime import datetime, timedelta

router = APIRouter()

@router.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """实时监控WebSocket连接"""
    await manager.connect(websocket)

    try:
        # 发送欢迎消息
        await manager.send_personal_message({
            'type': 'connected',
            'message': 'WebSocket连接成功',
            'timestamp': datetime.now().isoformat()
        }, websocket)

        # 启动实时推送任务
        push_task = asyncio.create_task(push_realtime_data(websocket))

        # 监听客户端消息
        while True:
            data = await websocket.receive_json()

            # 处理订阅请求
            if data.get('action') == 'subscribe':
                competitor_id = data.get('competitor_id')
                if competitor_id:
                    await manager.subscribe(websocket, competitor_id)
                    await manager.send_personal_message({
                        'type': 'subscribed',
                        'competitor_id': competitor_id,
                        'message': f'已订阅竞品 {competitor_id} 的实时更新'
                    }, websocket)

            # 处理取消订阅
            elif data.get('action') == 'unsubscribe':
                competitor_id = data.get('competitor_id')
                if competitor_id:
                    await manager.unsubscribe(websocket, competitor_id)
                    await manager.send_personal_message({
                        'type': 'unsubscribed',
                        'competitor_id': competitor_id
                    }, websocket)

            # 处理心跳
            elif data.get('action') == 'ping':
                await manager.send_personal_message({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        push_task.cancel()
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        manager.disconnect(websocket)
        push_task.cancel()

async def push_realtime_data(websocket: WebSocket):
    """实时推送数据"""
    while True:
        try:
            # 每5秒推送一次
            await asyncio.sleep(5)

            # 获取实时统计数据
            stats = await get_realtime_stats()

            await manager.send_personal_message({
                'type': 'stats_update',
                'data': stats,
                'timestamp': datetime.now().isoformat()
            }, websocket)

            # 如果订阅了特定竞品，推送竞品详情
            if websocket in manager.connection_metadata:
                subscribed_to = manager.connection_metadata[websocket]['subscribed_to']
                for comp_id in subscribed_to:
                    comp_data = await get_competitor_realtime_data(comp_id)
                    await manager.send_personal_message({
                        'type': 'competitor_update',
                        'competitor_id': comp_id,
                        'data': comp_data,
                        'timestamp': datetime.now().isoformat()
                    }, websocket)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[WebSocket] 推送数据错误: {e}")
            break

async def get_realtime_stats() -> dict:
    """获取实时统计数据 — ORM 查询"""
    db = SessionLocal()
    try:
        competitors_total = db.query(func.count(Competitor.id)).scalar() or 0
        active_count = db.query(func.count(Competitor.id)).filter(
            Competitor.status == "monitoring"
        ).scalar() or 0

        cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_prices = db.query(func.count(PriceHistory.id)).filter(
            PriceHistory.recorded_at >= cutoff
        ).scalar() or 0
        recent_reviews = db.query(func.count(UserReview.id)).filter(
            UserReview.collected_at >= cutoff
        ).scalar() or 0

        log_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_logs = db.query(func.count(MonitoringLog.id)).filter(
            MonitoringLog.checked_at >= log_cutoff
        ).scalar() or 0

        return {
            'competitors_total': competitors_total,
            'active_competitors': active_count,
            'recent_prices': recent_prices,
            'recent_reviews': recent_reviews,
            'recent_logs': recent_logs,
            'websocket_connections': len(manager.active_connections),
        }
    finally:
        db.close()


async def get_competitor_realtime_data(competitor_id: int) -> dict:
    """获取特定竞品的实时数据 — ORM 查询"""
    db = SessionLocal()
    try:
        latest_price = db.query(PriceHistory).filter(
            PriceHistory.competitor_id == competitor_id
        ).order_by(PriceHistory.recorded_at.desc()).first()

        reviews = db.query(UserReview).filter(
            UserReview.competitor_id == competitor_id
        ).order_by(UserReview.collected_at.desc()).limit(5).all()

        sent_cutoff = datetime.utcnow() - timedelta(hours=24)
        sent_rows = db.query(
            case(
                (UserReview.sentiment_score > 0.05, "positive"),
                (UserReview.sentiment_score < -0.05, "negative"),
                else_="neutral",
            ).label("sentiment"),
            func.count(UserReview.id).label("count"),
        ).filter(
            UserReview.competitor_id == competitor_id,
            UserReview.collected_at >= sent_cutoff,
        ).group_by("sentiment").all()

        logs = db.query(MonitoringLog).filter(
            MonitoringLog.competitor_id == competitor_id
        ).order_by(MonitoringLog.checked_at.desc()).limit(5).all()

        return {
            'latest_price': {"price": latest_price.price, "recorded_at": latest_price.recorded_at} if latest_price else None,
            'latest_reviews': [{"id": r.id, "sentiment_score": r.sentiment_score, "content": r.content, "author": r.author, "rating": r.rating, "review_date": r.review_date.isoformat() if r.review_date else None, "collected_at": r.collected_at.isoformat() if r.collected_at else None, "platform": r.platform} for r in reviews],
            'sentiment_stats': {row.sentiment: row.count for row in sent_rows},
            'latest_logs': [{"event_type": log.status, "checked_at": log.checked_at, "severity": log.response_time} for log in logs],
        }
    finally:
        db.close()

@router.get("/ws/stats")
async def get_websocket_stats():
    """获取WebSocket连接统计"""
    return {
        'success': True,
        'data': manager.get_stats()
    }