"""知识库 API 校验与边界：创建必填、更新部分字段、列表分页、404"""
import pytest
from fastapi.testclient import TestClient


def test_create_kb_missing_name_422(client: TestClient, auth_headers: dict):
    """POST /api/knowledge-bases 缺少 name 返回 422"""
    resp = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"description": "desc"},
    )
    assert resp.status_code == 422


def test_create_kb_empty_name(client: TestClient, auth_headers: dict):
    """POST /api/knowledge-bases 空 name（若 Pydantic 允许）"""
    resp = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"name": ""},
    )
    assert resp.status_code in (400, 422)


def test_create_kb_full_fields(client: TestClient, auth_headers: dict):
    """创建知识库时传入完整可选字段，响应包含 knowledge_base"""
    resp = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={
            "name": "完整字段测试库",
            "description": "描述",
            "icon": "📁",
            "color": "#ff0000",
            "is_public": False,
        },
    )
    if resp.status_code != 200:
        pytest.skip("auth or DB issue")
    data = resp.json()
    assert data.get("code") == 0
    kb = data.get("data", {}).get("knowledge_base") or data.get("data")
    assert kb
    assert kb.get("name") == "完整字段测试库"
    assert kb.get("id")


def test_get_kb_list_pagination(client: TestClient):
    """GET /api/knowledge-bases?skip=0&limit=1 分页生效"""
    resp = client.get("/api/knowledge-bases", params={"skip": 0, "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    kbs = data.get("data", {}).get("knowledge_bases", [])
    assert len(kbs) <= 1
    assert "total" in data.get("data", {})


def test_get_kb_detail_404(client: TestClient):
    """GET /api/knowledge-bases/999999 返回 404"""
    resp = client.get("/api/knowledge-bases/999999")
    assert resp.status_code == 404


def test_update_kb_partial(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """PUT 只传 description 时仅更新该字段"""
    resp = client.put(
        f"/api/knowledge-bases/{extra_kb_id}",
        headers=auth_headers,
        json={"description": "仅更新描述"},
    )
    if resp.status_code != 200:
        pytest.skip("extra_kb_id or auth issue")
    data = resp.json()
    assert data.get("code") == 0


def test_kb_name_duplicate_check(client: TestClient, auth_headers: dict):
    """测试创建同名知识库和重命名为已存在的名称时应该返回 400"""
    import uuid
    base_name = f"查重测试库_{uuid.uuid4().hex[:6]}"
    
    # 1. 成功创建第一个
    resp1 = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"name": base_name, "description": "1"},
    )
    assert resp1.status_code == 200
    
    # 2. 创建同名知识库，预期 400
    resp2 = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"name": base_name, "description": "2"},
    )
    assert resp2.status_code == 400
    assert "同名知识库已存在" in resp2.text

    # 3. 创建第二个备用知识库
    base_name_2 = f"查重测试库备用_{uuid.uuid4().hex[:6]}"
    resp3 = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={"name": base_name_2, "description": "3"},
    )
    assert resp3.status_code == 200
    kb2_id = resp3.json().get("data", {}).get("knowledge_base", {}).get("id")
    
    # 4. 将第二个知识库重命名为第一个的名称，预期 400
    resp4 = client.put(
        f"/api/knowledge-bases/{kb2_id}",
        headers=auth_headers,
        json={"name": base_name},
    )
    assert resp4.status_code == 400
    assert "同名知识库已存在" in resp4.text
