"""
WebSocket连接管理器 - 实时推送服务
"""
from fastapi import WebSocket
from typing import List, Dict, Set
import asyncio
import json
from datetime import datetime

class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 活跃连接列表
        self.active_connections: List[WebSocket] = []
        # 竞品订阅映射 {competitor_id: set(websocket)}
        self.subscriptions: Dict[int, Set[WebSocket]] = {}
        # 连接元数据 {websocket: {client_id, subscribed_to}}
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            'client_id': client_id or f'client_{len(self.active_connections)}',
            'subscribed_to': set(),
            'connected_at': datetime.now()
        }
        print(f"[WebSocket] 新连接建立: {client_id}, 当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 清理订阅
        if websocket in self.connection_metadata:
            subscribed_competitors = self.connection_metadata[websocket]['subscribed_to']
            for comp_id in subscribed_competitors:
                if comp_id in self.subscriptions:
                    self.subscriptions[comp_id].discard(websocket)

            del self.connection_metadata[websocket]

        print(f"[WebSocket] 连接断开, 当前连接数: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, competitor_id: int):
        """订阅特定竞品"""
        if competitor_id not in self.subscriptions:
            self.subscriptions[competitor_id] = set()

        self.subscriptions[competitor_id].add(websocket)

        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]['subscribed_to'].add(competitor_id)

        print(f"[WebSocket] 客户端订阅竞品 {competitor_id}")

    async def unsubscribe(self, websocket: WebSocket, competitor_id: int):
        """取消订阅"""
        if competitor_id in self.subscriptions:
            self.subscriptions[competitor_id].discard(websocket)

        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]['subscribed_to'].discard(competitor_id)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket] 发送消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """广播消息到所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_subscribers(self, competitor_id: int, message: dict):
        """广播消息到订阅特定竞品的客户端"""
        if competitor_id not in self.subscriptions:
            return

        disconnected = []
        for connection in self.subscriptions[competitor_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            'total_connections': len(self.active_connections),
            'total_subscriptions': sum(len(subs) for subs in self.subscriptions.values()),
            'subscribed_competitors': list(self.subscriptions.keys()),
            'connections': [
                {
                    'client_id': meta['client_id'],
                    'subscribed_to': list(meta['subscribed_to']),
                    'connected_at': meta['connected_at'].isoformat()
                }
                for meta in self.connection_metadata.values()
            ]
        }

# 全局连接管理器
manager = ConnectionManager()
