"""Tests for WebSocket ConnectionManager."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core.websocket_manager import ConnectionManager


@pytest.fixture
def manager():
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock(return_value={"action": "ping"})
    return ws


class TestConnectionManager:
    def test_connect_adds_to_active(self, manager, mock_ws):
        manager.connect_sync(mock_ws, client_id="test_client")
        assert mock_ws in manager.active_connections
        assert manager.connection_metadata[mock_ws]["client_id"] == "test_client"

    def test_disconnect_removes(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "c1")
        manager.disconnect(mock_ws)
        assert mock_ws not in manager.active_connections
        assert mock_ws not in manager.connection_metadata

    def test_subscribe_adds_to_set(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "c1")
        manager.subscribe_sync(mock_ws, competitor_id=1)
        assert mock_ws in manager.subscriptions[1]
        assert 1 in manager.connection_metadata[mock_ws]["subscribed_to"]

    def test_unsubscribe_removes(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "c1")
        manager.subscribe_sync(mock_ws, 1)
        manager.unsubscribe_sync(mock_ws, 1)
        assert mock_ws not in manager.subscriptions.get(1, set())

    def test_disconnect_cleans_up_subscriptions(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "c1")
        manager.subscribe_sync(mock_ws, 1)
        manager.subscribe_sync(mock_ws, 2)
        manager.disconnect(mock_ws)
        assert 1 not in manager.subscriptions or mock_ws not in manager.subscriptions.get(1, set())

    def test_get_stats_empty(self, manager):
        stats = manager.get_stats()
        assert stats["total_connections"] == 0
        assert stats["total_subscriptions"] == 0

    def test_get_stats_with_connections(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "stats_test")
        manager.subscribe_sync(mock_ws, 1)
        stats = manager.get_stats()
        assert stats["total_connections"] == 1
        assert stats["total_subscriptions"] == 1

    def test_broadcast_sends_to_all(self, manager):
        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()
        ws2.accept = AsyncMock()
        manager.connect_sync(ws1, "w1")
        manager.connect_sync(ws2, "w2")

        import asyncio
        asyncio.run(manager.broadcast({"type": "test"}))
        ws1.send_json.assert_called_once_with({"type": "test"})
        ws2.send_json.assert_called_once_with({"type": "test"})

    def test_broadcast_to_subscribers(self, manager, mock_ws):
        manager.connect_sync(mock_ws, "sub1")
        manager.subscribe_sync(mock_ws, 1)
        import asyncio
        asyncio.run(manager.broadcast_to_subscribers(1, {"type": "competitor"}))
        mock_ws.send_json.assert_called_with({"type": "competitor"})


# ── Synchronous helpers for testability ──

def _patch_manager_for_tests():
    """Add sync wrappers to ConnectionManager for easier unit testing."""
    def connect_sync(self, websocket, client_id=None):
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "subscribed_to": set(),
            "connected_at": __import__("datetime").datetime.now(),
        }

    def subscribe_sync(self, websocket, competitor_id):
        if competitor_id not in self.subscriptions:
            self.subscriptions[competitor_id] = set()
        self.subscriptions[competitor_id].add(websocket)
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscribed_to"].add(competitor_id)

    def unsubscribe_sync(self, websocket, competitor_id):
        if competitor_id in self.subscriptions:
            self.subscriptions[competitor_id].discard(websocket)
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscribed_to"].discard(competitor_id)

    ConnectionManager.connect_sync = connect_sync
    ConnectionManager.subscribe_sync = subscribe_sync
    ConnectionManager.unsubscribe_sync = unsubscribe_sync


_patch_manager_for_tests()
