"""
健康检查与认证相关疏通测试：根路径、登录、登出、菜单（需 token）。
"""
import pytest
from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    """GET / 返回 200 及统一响应体"""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("code") == 0
    assert "data" in data
    assert "message" in data["data"]


def test_login_success(client: TestClient):
    """POST /api/auth/login 正确账号密码返回 200 与 token"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert data.get("data") is not None
    assert "access_token" in data["data"] or "token" in data["data"]


def test_login_wrong_password(client: TestClient):
    """POST /api/auth/login 错误密码返回 401 或 200 且 code!=0"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code in (200, 401)
    if resp.status_code == 200:
        assert resp.json().get("code") != 0


def test_menu_requires_auth(client: TestClient):
    """GET /api/auth/menu 无 token 返回 401"""
    resp = client.get("/api/auth/menu")
    assert resp.status_code == 401


def test_menu_with_token(client: TestClient, auth_headers: dict):
    """GET /api/auth/menu 带 token 返回 200 与菜单数据"""
    resp = client.get("/api/auth/menu", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "data" in data
