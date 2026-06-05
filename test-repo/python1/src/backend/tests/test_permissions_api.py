"""权限 API：列表（管理员）"""
import pytest
from fastapi.testclient import TestClient


def test_get_permissions_requires_admin(client: TestClient, test_user_headers: dict):
    """GET /api/permissions 非管理员返回 403"""
    resp = client.get("/api/permissions", headers=test_user_headers)
    assert resp.status_code in (403, 401)


def test_get_permissions_as_admin(client: TestClient, auth_headers: dict):
    """GET /api/permissions 管理员返回权限列表"""
    resp = client.get("/api/permissions", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "permissions" in data.get("data", {})


def test_get_permissions_filter_by_role(client: TestClient, auth_headers: dict):
    """GET /api/permissions?role=admin"""
    resp = client.get("/api/permissions", headers=auth_headers, params={"role": "admin"})
    assert resp.status_code == 200, resp.text
    perms = resp.json().get("data", {}).get("permissions", [])
    for p in perms:
        assert p.get("role") == "admin"
