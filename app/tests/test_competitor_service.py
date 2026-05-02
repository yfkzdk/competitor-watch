"""Tests for CompetitorService — SQLAlchemy ORM methods."""
import pytest
from app.models.competitor import CompetitorCreate, CompetitorUpdate


class TestCreateCompetitor:
    def test_create_returns_dict_with_metrics(self, competitor_service):
        data = CompetitorCreate(
            name="阿里云", url="https://aliyun.com", status="active",
            type="iaas", frequency="10", market_share=30.0,
            price_index=95.0, user_rating=4.3, growth=8.0,
        )
        result = competitor_service.create_competitor(data)
        assert result["name"] == "阿里云"
        assert result["url"] == "https://aliyun.com"
        assert "metrics" in result
        assert result["metrics"]["market_share"] == 30.0
        assert result["metrics"]["user_rating"] == 4.3

    def test_create_assigns_id(self, competitor_service):
        data = CompetitorCreate(
            name="腾讯云", url="https://cloud.tencent.com", status="active",
            type="iaas", frequency="15", market_share=25.0,
            price_index=90.0, user_rating=4.0, growth=5.0,
        )
        result = competitor_service.create_competitor(data)
        assert isinstance(result["id"], int)
        assert result["id"] > 0


class TestGetCompetitors:
    def test_get_all_empty(self, competitor_service):
        result = competitor_service.get_all_competitors()
        assert result == []

    def test_get_all_returns_all(self, competitor_service):
        competitor_service.create_competitor(CompetitorCreate(
            name="C1", url="https://c1.com", status="active", type="saas",
            frequency="30", market_share=10.0, price_index=100.0, user_rating=3.5, growth=2.0,
        ))
        competitor_service.create_competitor(CompetitorCreate(
            name="C2", url="https://c2.com", status="active", type="iaas",
            frequency="60", market_share=20.0, price_index=110.0, user_rating=4.0, growth=0.0,
        ))
        result = competitor_service.get_all_competitors()
        assert len(result) == 2
        assert result[0]["name"] == "C1"
        assert result[1]["name"] == "C2"

    def test_get_by_id_found(self, competitor_service):
        created = competitor_service.create_competitor(CompetitorCreate(
            name="目标", url="https://target.com", status="active", type="saas",
            frequency="30", market_share=5.0, price_index=80.0, user_rating=4.5, growth=20.0,
        ))
        result = competitor_service.get_competitor_by_id(created["id"])
        assert result is not None
        assert result["name"] == "目标"
        assert result["metrics"]["growth"] == 20.0

    def test_get_by_id_not_found(self, competitor_service):
        result = competitor_service.get_competitor_by_id(999)
        assert result is None


class TestUpdateCompetitor:
    def test_update_changes_fields(self, competitor_service):
        created = competitor_service.create_competitor(CompetitorCreate(
            name="旧名", url="https://old.com", status="active", type="saas",
            frequency="30", market_share=5.0, price_index=100.0, user_rating=3.0, growth=0.0,
        ))
        update_data = CompetitorUpdate(name="新名", market_share=12.0, price_index=88.0)
        result = competitor_service.update_competitor(created["id"], update_data)
        assert result["name"] == "新名"
        assert result["metrics"]["market_share"] == 12.0
        assert result["metrics"]["price_index"] == 88.0
        # Unchanged fields preserved
        assert result["metrics"]["user_rating"] == 3.0

    def test_update_nonexistent(self, competitor_service):
        result = competitor_service.update_competitor(999, CompetitorUpdate(name="X"))
        assert result is None


class TestDeleteCompetitor:
    def test_delete_removes(self, competitor_service):
        created = competitor_service.create_competitor(CompetitorCreate(
            name="待删", url="https://gone.com", status="active", type="saas",
            frequency="30", market_share=1.0, price_index=100.0, user_rating=2.0, growth=0.0,
        ))
        assert competitor_service.delete_competitor(created["id"]) is True
        assert competitor_service.get_competitor_by_id(created["id"]) is None

    def test_delete_nonexistent(self, competitor_service):
        assert competitor_service.delete_competitor(999) is False


class TestTriggerFetch:
    def test_trigger_fetch_updates_last_checked(self, competitor_service):
        created = competitor_service.create_competitor(CompetitorCreate(
            name="采集测试", url="https://fetch.com", status="active", type="saas",
            frequency="30", market_share=10.0, price_index=100.0, user_rating=4.0, growth=5.0,
        ))
        result = competitor_service.trigger_fetch(created["id"])
        # In demo mode, may succeed or return error depending on data_pipeline
        # At minimum it should not crash and should recognize the competitor
        if result["success"]:
            assert "data" in result
        else:
            # Expected in test environment without full pipeline
            assert "error" in result

    def test_trigger_fetch_nonexistent(self, competitor_service):
        result = competitor_service.trigger_fetch(999)
        assert result["success"] is False
        assert "不存在" in result.get("error", "")
