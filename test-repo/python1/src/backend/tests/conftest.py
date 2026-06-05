"""
pytest 公共 fixture：测试客户端、测试库等。
运行前会设置测试用数据库路径，避免污染开发库。
测试前自动执行 init_db 与 init_sample_data，确保表与默认数据存在。
"""
import os
import sys

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_test_db = os.path.abspath(os.path.join(_tests_dir, "test_db.db"))
os.environ["SQLITE_DATABASE"] = _test_db

if os.path.dirname(_tests_dir) not in sys.path:
    sys.path.insert(0, os.path.dirname(_tests_dir))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_db_initialized():
    """测试前确保测试库已初始化（建表 + 默认 admin 等）"""
    import asyncio
    from database import init_db
    from main import init_sample_data

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
        loop.run_until_complete(init_sample_data())
    finally:
        loop.close()


def _get_app():
    from main import app
    return app


@pytest.fixture(scope="session")
def app():
    return _get_app()


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """管理员 admin 的 Authorization header（依赖测试库已初始化 admin）"""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0 and data.get("data")
    token = data["data"].get("access_token") or data["data"].get("token")
    assert token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_headers(client, auth_headers):
    """先创建普通用户 testuser，再登录得到其 token，返回 header（用于测非 admin 权限）"""
    # 确保 testuser 存在（幂等）
    create = client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "testuser", "password": "test123", "nickname": "测试用户"},
    )
    j = create.json() or {}
    if create.status_code == 400 and ("已存在" in str(j.get("detail", "")) or "已存在" in str(j.get("msg", ""))):
        pass
    else:
        assert create.status_code == 200, create.text
    resp = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "test123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    token = data["data"].get("access_token") or data["data"].get("token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def extra_kb_id(client, auth_headers):
    """创建额外知识库「测试知识库2」，返回 kb_id（用于文档/列表等用例）"""
    import uuid
    kb_name = f"测试知识库2_{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/knowledge-bases",
        headers=auth_headers,
        json={
            "name": kb_name,
            "description": "用于 API 测试的第二个知识库",
            "icon": "📁",
            "color": "#ff9800",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("code") == 0
    kb = data.get("data", {}).get("knowledge_base") or data.get("data")
    return kb.get("id")
