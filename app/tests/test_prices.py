import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPricesAPI:
    """价格API测试"""

    def test_get_price_history_success(self):
        """测试获取价格历史成功"""
        # 先获取一个有效的竞品ID
        list_response = client.get("/api/competitors")
        assert list_response.status_code == 200

        competitors = list_response.json()["data"]
        if len(competitors) > 0:
            comp_id = competitors[0]["id"]

            # 测试获取价格历史
            response = client.get(
                f"/api/v1/prices/history",
                params={"competitor_id": comp_id, "limit": 10}
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "competitor_id" in data["data"]
            assert "prices" in data["data"]
            assert "statistics" in data["data"]

    def test_get_price_history_with_filters(self):
        """测试带筛选条件的价格历史"""
        # 先获取一个有效的竞品ID
        list_response = client.get("/api/competitors")
        competitors = list_response.json()["data"]

        if len(competitors) > 0:
            comp_id = competitors[0]["id"]

            # 测试带筛选条件
            response = client.get(
                f"/api/v1/prices/history",
                params={
                    "competitor_id": comp_id,
                    "product_name": "云服务器",
                    "limit": 5
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert data["data"]["competitor_id"] == comp_id

    def test_get_price_history_missing_competitor_id(self):
        """测试缺少必填参数competitor_id"""
        response = client.get("/api/v1/prices/history")
        assert response.status_code == 422  # Validation error

    def test_get_price_history_empty_data(self):
        """测试无数据情况"""
        # 使用一个不存在的竞品ID
        response = client.get(
            f"/api/v1/prices/history",
            params={"competitor_id": 99999, "limit": 10}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["prices"] == []
        assert data["data"]["statistics"]["count"] == 0

    def test_get_price_history_with_date_range(self):
        """测试带日期范围的价格历史"""
        # 先获取一个有效的竞品ID
        list_response = client.get("/api/competitors")
        competitors = list_response.json()["data"]

        if len(competitors) > 0:
            comp_id = competitors[0]["id"]

            # 测试带日期范围
            response = client.get(
                f"/api/v1/prices/history",
                params={
                    "competitor_id": comp_id,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "limit": 20
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True

    def test_price_compare_success(self):
        """测试价格对比成功"""
        # 先获取两个有效的竞品ID
        list_response = client.get("/api/competitors")
        competitors = list_response.json()["data"]

        if len(competitors) >= 2:
            comp_ids = f"{competitors[0]['id']},{competitors[1]['id']}"

            # 测试价格对比
            response = client.get(
                f"/api/v1/prices/compare",
                params={
                    "competitor_ids": comp_ids,
                    "product_name": "云服务器"
                }
            )
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert "comparison" in data["data"]
            assert "analysis" in data["data"]

    def test_price_compare_missing_params(self):
        """测试价格对比缺少参数"""
        response = client.get("/api/v1/prices/compare")
        assert response.status_code == 422  # Validation error