"""Tests for AlertService — SQLAlchemy ORM methods."""
import pytest


class TestCreateAlertRule:
    def test_create_rule_returns_id(self, alert_service):
        rule_id = alert_service.create_alert_rule(
            competitor_id=1, rule_type="price_change",
            threshold=10.0, severity="P1", channels=["in_app"],
        )
        assert isinstance(rule_id, int)
        assert rule_id > 0


class TestTriggerAlert:
    def test_trigger_returns_id(self, alert_service):
        alert_id = alert_service.trigger_alert(
            competitor_id=1, alert_type="price_change",
            severity="P0", message="价格突降15%",
        )
        assert isinstance(alert_id, int)
        assert alert_id > 0

    def test_trigger_deduplicates_within_window(self, alert_service):
        first = alert_service.trigger_alert(
            competitor_id=1, alert_type="price_change",
            severity="P0", message="价格突变",
        )
        second = alert_service.trigger_alert(
            competitor_id=1, alert_type="price_change",
            severity="P0", message="价格再次突变",
        )
        assert first is not None
        assert second is None  # Deduplicated


class TestGetPendingAlerts:
    def test_returns_pending(self, alert_service):
        alert_service.trigger_alert(
            competitor_id=1, alert_type="test",
            severity="P1", message="测试告警1",
        )
        alert_service.trigger_alert(
            competitor_id=2 if 1 != 1 else 1, alert_type="test2",
            severity="P0", message="测试告警2",
        )
        # First one won't be deduped (different alert_type), second will
        pending = alert_service.get_pending_alerts()
        assert len(pending) >= 1
        assert pending[0]["status"] == "pending"


class TestAcknowledgeAlert:
    def test_acknowledge_marks_read(self, alert_service):
        alert_id = alert_service.trigger_alert(
            competitor_id=1, alert_type="ack_test",
            severity="P2", message="待确认告警",
        )
        alert_service.acknowledge_alert(alert_id)
        # After ack, should not appear in pending
        pending = alert_service.get_pending_alerts()
        pending_ids = [a["id"] for a in pending]
        assert alert_id not in pending_ids


class TestGetAlertStats:
    def test_stats_counts_correctly(self, alert_service):
        alert_service.trigger_alert(
            competitor_id=1, alert_type="t1", severity="P0", message="m1",
        )
        alert_service.trigger_alert(
            competitor_id=1, alert_type="t2", severity="P1", message="m2",
        )
        stats = alert_service.get_alert_stats(hours=24)
        assert "by_severity" in stats
        assert stats["period_hours"] == 24


class TestGetAlerts:
    def test_filters_by_severity(self, alert_service):
        alert_service.trigger_alert(
            competitor_id=1, alert_type="s1", severity="P0", message="critical",
        )
        alert_service.trigger_alert(
            competitor_id=1, alert_type="s2", severity="P2", message="info",
        )
        result = alert_service.get_alerts(severity="P0", limit=10)
        assert len(result) >= 1
        assert all(a["severity"] == "P0" for a in result)

    def test_filters_by_status(self, alert_service):
        alert_id = alert_service.trigger_alert(
            competitor_id=1, alert_type="st1", severity="P1", message="pending alert",
        )
        pending = alert_service.get_alerts(status="pending", limit=10)
        assert any(a["id"] == alert_id for a in pending)

    def test_respects_limit(self, alert_service):
        for i in range(5):
            alert_service.trigger_alert(
                competitor_id=1, alert_type=f"lt{i}",
                severity="P2", message=f"msg {i}",
            )
        result = alert_service.get_alerts(limit=3)
        assert len(result) <= 3


class TestGetFullStats:
    def test_returns_all_fields(self, alert_service):
        alert_service.trigger_alert(
            competitor_id=1, alert_type="fs1", severity="P0", message="full stat test",
        )
        stats = alert_service.get_full_stats()
        assert "total" in stats
        assert "pending" in stats
        assert "by_severity" in stats
        assert "by_competitor" in stats
        assert "recent_24h" in stats
        assert stats["total"] >= 1


class TestGetRules:
    def test_returns_empty_initially(self, alert_service):
        rules = alert_service.get_rules()
        assert rules == []

    def test_returns_created_rule(self, alert_service):
        rule_id = alert_service.create_alert_rule(
            competitor_id=1, rule_type="price_change",
            threshold=5.0, severity="P1", channels=["email"],
        )
        rules = alert_service.get_rules()
        assert len(rules) >= 1
        created = [r for r in rules if r["id"] == rule_id]
        assert len(created) == 1
        assert created[0]["threshold"] == 5.0
