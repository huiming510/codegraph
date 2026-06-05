"""日志 API：查询日志、系统日志（管理员）"""
import pytest
from fastapi.testclient import TestClient


def test_logs_query_requires_admin(client: TestClient, test_user_headers: dict):
    """GET /api/logs/query 非管理员返回 403"""
    resp = client.get("/api/logs/query", headers=test_user_headers)
    assert resp.status_code in (403, 401)


def test_logs_query_as_admin(client: TestClient, auth_headers: dict):
    """GET /api/logs/query 管理员返回 200"""
    resp = client.get("/api/logs/query", headers=auth_headers, params={"skip": 0, "limit": 10})
    assert resp.status_code == 200, resp.text
    assert resp.json().get("code") == 0


def test_logs_system_requires_admin(client: TestClient, test_user_headers: dict):
    """GET /api/logs/system 非管理员返回 403"""
    resp = client.get("/api/logs/system", headers=test_user_headers)
    assert resp.status_code in (403, 401)


def test_logs_system_as_admin(client: TestClient, auth_headers: dict):
    """GET /api/logs/system 管理员返回 200"""
    resp = client.get("/api/logs/system", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("code") == 0
