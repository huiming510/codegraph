# Config API tests
import pytest
from fastapi.testclient import TestClient


def test_get_current_config(client: TestClient):
    resp = client.get("/api/config/current")
    assert resp.status_code == 200
    assert resp.json().get("code") == 0


def test_get_es_config(client: TestClient, auth_headers: dict):
    resp = client.get("/api/config/es", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json().get("code") == 0


def test_put_es_config(client: TestClient, auth_headers: dict):
    resp = client.put(
        "/api/config/es",
        headers=auth_headers,
        json={"linkrag_server_url": None, "elasticsearch_url": None},
    )
    assert resp.status_code == 200
    assert resp.json().get("code") == 0


def test_get_locale(client: TestClient):
    resp = client.get("/api/config/locale")
    assert resp.status_code == 200
    assert "locale" in (resp.json().get("data") or {})


def test_put_locale(client: TestClient, auth_headers: dict):
    resp = client.put("/api/config/locale", headers=auth_headers, json={"locale": "zh"})
    assert resp.status_code == 200
    assert resp.json().get("code") == 0
