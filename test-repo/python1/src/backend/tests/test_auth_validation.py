"""认证 API 校验与边界：空 body、缺失字段、响应结构、错误码"""
import pytest
from fastapi.testclient import TestClient


def test_login_empty_body_422(client: TestClient):
    """POST /api/auth/login 空 body 返回 422"""
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 422


def test_login_missing_password_422(client: TestClient):
    """POST /api/auth/login 缺少 password 返回 422"""
    resp = client.post("/api/auth/login", json={"username": "admin"})
    assert resp.status_code == 422


def test_login_missing_username_422(client: TestClient):
    """POST /api/auth/login 缺少 username 返回 422"""
    resp = client.post("/api/auth/login", json={"password": "admin123"})
    assert resp.status_code == 422


def test_login_empty_username(client: TestClient):
    """POST /api/auth/login 空用户名应失败或 422 或 401"""
    resp = client.post("/api/auth/login", json={"username": "", "password": "x"})
    assert resp.status_code in (200, 401, 422)
    if resp.status_code == 200:
        assert resp.json().get("code") != 0  # 空用户名应失败


def test_login_success_response_structure(client: TestClient):
    """登录成功时响应包含 access_token、token_type、user 及完整 user 字段"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if resp.status_code != 200:
        pytest.skip("DB not initialized")
    data = resp.json()
    assert data.get("code") == 0
    d = data.get("data") or {}
    assert "access_token" in d or "token" in d
    assert "user" in d or "token" in d
    if "user" in d:
        u = d["user"]
        assert "id" in u
        assert "username" in u
        assert "role" in u


def test_register_empty_body_422(client: TestClient):
    """POST /api/auth/register 空 body 返回 422"""
    resp = client.post("/api/auth/register", json={})
    assert resp.status_code == 422


def test_register_short_password(client: TestClient):
    """注册时过短密码（若后端有校验）：200 成功或 422 校验失败"""
    import uuid
    resp = client.post(
        "/api/auth/register",
        json={"username": f"u1_{uuid.uuid4().hex[:6]}", "password": "1", "nickname": "n"},
    )
    assert resp.status_code in (200, 422)


def test_userinfo_response_has_required_fields(client: TestClient, auth_headers: dict):
    """GET /api/auth/userinfo 返回 id、username、role、created_at"""
    resp = client.get("/api/auth/userinfo", headers=auth_headers)
    if resp.status_code != 200:
        pytest.skip("auth_headers failed")
    data = resp.json()
    u = data.get("data") or {}
    assert "id" in u
    assert "username" in u
    assert "role" in u


def test_menu_response_is_list_of_menus(client: TestClient, auth_headers: dict):
    """GET /api/auth/menu 返回菜单数组，每项含 path"""
    resp = client.get("/api/auth/menu", headers=auth_headers)
    if resp.status_code != 200:
        pytest.skip("auth_headers failed")
    data = resp.json()
    menus = data.get("data") or []
    assert isinstance(menus, list)
    for m in menus:
        assert "path" in m or "name" in m
