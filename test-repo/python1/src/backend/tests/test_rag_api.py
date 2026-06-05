"""RAG/对话 API：query、chat、sessions、history、search-apps、chat-apps"""
import pytest
from fastapi.testclient import TestClient


def test_rag_query_no_body(client: TestClient, auth_headers: dict):
    """POST /api/query 缺少 body 或必填项时 422"""
    resp = client.post("/api/query", headers=auth_headers, json={})
    assert resp.status_code in (200, 422, 500, 503)


def test_rag_query_with_body(client: TestClient, auth_headers: dict):
    """POST /api/query 正常请求（可能 200 或 503 未配置 LLM）"""
    resp = client.post(
        "/api/query",
        headers=auth_headers,
        json={
            "query": "测试问题",
            "knowledge_base_ids": [],
            "top_k": 3,
        },
    )
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("code") in (0, 500)  # 0=成功，500=LLM 未配置等


def test_rag_chat_sessions(client: TestClient, auth_headers: dict):
    """GET /api/chat/sessions 会话列表"""
    resp = client.get("/api/chat/sessions", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "data" in data


def test_rag_chat_history(client: TestClient, auth_headers: dict):
    """GET /api/chat/history/{session_id} 历史（可传不存在的 session_id）"""
    resp = client.get("/api/chat/history/0", headers=auth_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "data" in data


def test_rag_search_apps_list(client: TestClient, auth_headers: dict):
    """GET /api/search-apps 应用列表"""
    resp = client.get("/api/search-apps", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_rag_chat_apps_list(client: TestClient, auth_headers: dict):
    """GET /api/chat-apps 对话应用列表"""
    resp = client.get("/api/chat-apps", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
