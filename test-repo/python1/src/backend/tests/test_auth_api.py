"""认证相关 API：注册、userinfo、登出、修改密码、菜单"""
import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """POST /api/auth/register 注册新用户返回 200"""
    import uuid
    uname = f"newuser_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": uname,
            "password": "newpass123",
            "nickname": "新用户",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "data" in data


def test_register_duplicate_username(client: TestClient):
    """POST /api/auth/register 重复用户名返回错误"""
    client.post(
        "/api/auth/register",
        json={"username": "dupuser", "password": "pass123"},
    )
    resp = client.post(
        "/api/auth/register",
        json={"username": "dupuser", "password": "other123"},
    )
    assert resp.status_code in (200, 400)
    data = resp.json()
    assert data.get("code") != 0 or "已存在" in str(data.get("detail", "")) + str(data.get("msg", ""))


def test_userinfo_requires_auth(client: TestClient):
    """GET /api/auth/userinfo 无 token 返回 401"""
    resp = client.get("/api/auth/userinfo")
    assert resp.status_code == 401


def test_userinfo_with_token(client: TestClient, auth_headers: dict):
    """GET /api/auth/userinfo 带 token 返回当前用户信息"""
    resp = client.get("/api/auth/userinfo", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    user = data.get("data") or {}
    assert user.get("username")
    assert "role" in user


def test_logout_with_token(client: TestClient, auth_headers: dict):
    """POST /api/auth/logout 带 token 返回 200"""
    resp = client.post("/api/auth/logout", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_change_password_wrong_old(client: TestClient, auth_headers: dict):
    """PUT /api/auth/password 原密码错误返回 400"""
    resp = client.put(
        "/api/auth/password",
        headers=auth_headers,
        json={"old_password": "wrong", "new_password": "newpass123"},
    )
    assert resp.status_code in (200, 400)
    data = resp.json()
    assert data.get("code") != 0


def test_menu_with_token(client: TestClient, auth_headers: dict):
    """GET /api/auth/menu 带 token 返回菜单列表"""
    resp = client.get("/api/auth/menu", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert isinstance(data.get("data"), list)
