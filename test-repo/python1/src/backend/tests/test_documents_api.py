"""文档 API：列表、虚拟文件夹、分配"""
import pytest
from fastapi.testclient import TestClient


def test_get_documents_list(client: TestClient, auth_headers: dict):
    """GET /api/documents 文档列表"""
    resp = client.get("/api/documents", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    assert "documents" in data.get("data", {})


def test_get_documents_by_kb(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """GET /api/documents?knowledge_base_id="""
    resp = client.get(
        "/api/documents",
        headers=auth_headers,
        params={"knowledge_base_id": extra_kb_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_get_virtual_folders(client: TestClient, auth_headers: dict, extra_kb_id: int):
    """GET /api/doc-folders/virtual-folders"""
    resp = client.get(
        "/api/doc-folders/virtual-folders",
        headers=auth_headers,
        params={"knowledge_base_id": extra_kb_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0


def test_get_doc_folder_assignments(client: TestClient, auth_headers: dict):
    """GET /api/doc-folders/assignments"""
    resp = client.get("/api/doc-folders/assignments", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("code") == 0
