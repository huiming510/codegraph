"""知识库 API：列表、详情、创建、更新、删除、文档列表"""
import pytest
from fastapi.testclient import TestClient


def test_get_knowledge_bases_list(client: TestClient):
    """GET /api/knowledge-bases 公开接口，无需 token"""
    resp = client.get("/api/knowledge-bases")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "knowledge_bases" in data.get("data", {})
    assert "total" in data.get("data", {})


def test_get_knowledge_bases_with_pagination(client: TestClient):
    """GET /api/knowledge-bases?skip=0&limit=2"""
    resp = client.get("/api/knowledge-bases", params={"skip": 0, "limit": 2})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    kbs = data.get("data", {}).get("knowledge_bases", [])
    assert len(kbs) <= 2


def test_create_knowledge_base(client: TestClient, auth_headers: dict):
    """POST /api/knowledge-bases 创建知识库"""
    import uuid
    kb_name = f"API测试知识库_{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={
            "name": kb_name,
            "description": "用于 pytest",
            "icon": "📚",
            "color": "#2196f3",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    kb = data.get("data", {}).get("knowledge_base") or data.get("data")
    assert kb.get("name") == kb_name


def test_get_knowledge_base_detail(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """GET /api/knowledge-bases/{kb_id} 获取详情"""
    resp = client.get(f"/api/knowledge-bases/{extra_kb_id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert data.get("data", {}).get("id") == extra_kb_id


def test_get_knowledge_base_not_found(client: TestClient):
    """GET /api/knowledge-bases/99999 不存在返回 404"""
    resp = client.get("/api/knowledge-bases/99999")
    assert resp.status_code == 404


def test_update_knowledge_base(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """PUT /api/knowledge-bases/{kb_id} 更新"""
    import uuid
    new_name = f"测试知识库2-已更新_{uuid.uuid4().hex[:6]}"
    resp = client.put(
        f"/api/knowledge-bases/{extra_kb_id}",
        headers=auth_headers,
        json={"name": new_name, "description": "更新描述"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_get_kb_documents(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """GET /api/knowledge-bases/{kb_id}/documents 文档列表"""
    resp = client.get(f"/api/knowledge-bases/{extra_kb_id}/documents", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "documents" in data.get("data", {})


def test_delete_knowledge_base(client: TestClient, auth_headers: dict):
    """DELETE /api/knowledge-bases/{kb_id} 删除（创建后删，避免影响其他用例）"""
    import uuid
    kb_name = f"待删除知识库_{uuid.uuid4().hex[:6]}"
    create = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"name": kb_name, "description": "delete me"},
    )
    assert create.status_code == 200
    kb_id = create.json().get("data", {}).get("knowledge_base", {}).get("id")
    if not kb_id:
        pytest.skip("create kb failed")
    resp = client.delete(f"/api/knowledge-bases/{kb_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
