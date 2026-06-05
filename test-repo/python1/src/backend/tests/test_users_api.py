"""用户管理 API：列表、创建、更新、删除（均需管理员）"""
import pytest
from fastapi.testclient import TestClient


def test_get_users_requires_admin(client: TestClient, test_user_headers: dict):
    """GET /api/users 非管理员返回 403"""
    resp = client.get("/api/users", headers=test_user_headers)
    assert resp.status_code in (403, 401)


def test_get_users_as_admin(client: TestClient, auth_headers: dict):
    """GET /api/users 管理员返回用户列表"""
    resp = client.get("/api/users", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "users" in data.get("data", {})
    assert "total" in data.get("data", {})


def test_get_users_with_role(client: TestClient, auth_headers: dict):
    """GET /api/users?role=admin 按角色筛选"""
    resp = client.get("/api/users", headers=auth_headers, params={"role": "admin"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    for u in data.get("data", {}).get("users", []):
        assert u.get("role") == "admin"


def test_create_user_as_admin(client: TestClient, auth_headers: dict):
    """POST /api/users 管理员创建用户"""
    import uuid
    uname = f"api_created_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": uname, "password": "pwd123", "nickname": "API创建"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_update_user_as_admin(client: TestClient, auth_headers: dict, test_user_headers: dict):
    """PUT /api/users/{id} 管理员更新用户昵称"""
    me = client.get("/api/auth/userinfo", headers=test_user_headers).json()
    user_id = me.get("data", {}).get("id")
    if not user_id:
        pytest.skip("no testuser id")
    resp = client.put(
        f"/api/users/{user_id}",
        headers=auth_headers,
        json={"nickname": "更新后的昵称"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("code") == 0


def test_delete_user_requires_admin(client: TestClient, test_user_headers: dict):
    """DELETE /api/users/{id} 非管理员不可操作"""
    resp = client.delete("/api/users/999", headers=test_user_headers)
    assert resp.status_code in (403, 401, 404)
