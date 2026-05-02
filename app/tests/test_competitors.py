import pytest
from fastapi.testclient import TestClient
from app.main import app
import random, string

client = TestClient(app)

def _rand_suffix():
    return ''.join(random.choices(string.ascii_lowercase, k=6))

class TestCompetitorsAPI:
    """竞品API测试"""

    def test_get_competitors_success(self):
        """测试获取竞品列表成功"""
        response = client.get("/api/competitors")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_competitors_v1_success(self):
        """测试获取竞品列表v1别名成功"""
        response = client.get("/api/v1/competitors")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_competitor_by_id_success(self):
        """测试获取竞品详情成功"""
        # 先获取列表，确保有数据
        list_response = client.get("/api/competitors")
        assert list_response.status_code == 200

        competitors = list_response.json()["data"]
        if len(competitors) > 0:
            comp_id = competitors[0]["id"]

            # 测试获取详情
            response = client.get(f"/api/competitors/{comp_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == comp_id
            assert "metrics" in data["data"]

    def test_get_competitor_not_found(self):
        """测试竞品不存在"""
        response = client.get("/api/competitors/99999")
        assert response.status_code == 404

    def test_create_competitor_success(self):
        """测试创建竞品成功"""
        new_competitor = {
            "name": f"TestCreate_{_rand_suffix()}",
            "url": "https://test-create.com",
            "status": "monitoring",
            "type": "all",
            "frequency": "30"
        }

        response = client.post("/api/competitors", json=new_competitor)
        assert response.status_code == 201

        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == new_competitor["name"]
        assert data["data"]["url"] == new_competitor["url"]

    def test_create_competitor_validation_error(self):
        """测试创建竞品验证失败"""
        invalid_competitor = {
            "name": "",  # 空名称，应该失败
            "url": "https://test.com"
        }

        response = client.post("/api/competitors", json=invalid_competitor)
        assert response.status_code == 422  # Validation error

    def test_update_competitor_success(self):
        """测试更新竞品成功"""
        suffix = _rand_suffix()
        new_competitor = {
            "name": f"UpdateTest_{suffix}",
            "url": "https://test-update.com"
        }
        create_response = client.post("/api/competitors", json=new_competitor)
        assert create_response.status_code == 201

        comp_id = create_response.json()["data"]["id"]

        update_data = {
            "name": f"Updated_{suffix}",
            "status": "paused"
        }
        response = client.put(f"/api/competitors/{comp_id}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == f"Updated_{suffix}"
        assert data["data"]["status"] == "paused"

    def test_delete_competitor_success(self):
        """测试删除竞品成功"""
        # 先创建一个竞品
        new_competitor = {
            "name": f"DeleteTest_{_rand_suffix()}",
            "url": "https://test-delete.com"
        }
        create_response = client.post("/api/competitors", json=new_competitor)
        assert create_response.status_code == 201

        comp_id = create_response.json()["data"]["id"]

        # 删除竞品
        response = client.delete(f"/api/competitors/{comp_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True

        # 验证已删除
        get_response = client.get(f"/api/competitors/{comp_id}")
        assert get_response.status_code == 404