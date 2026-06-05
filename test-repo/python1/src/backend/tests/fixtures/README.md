# 后端测试数据说明

## 自动初始化的数据（main.py lifespan）

- **默认管理员**：`admin` / `admin123`（若不存在则创建）
- **默认知识库**：若库内无知识库则创建「默认知识库」
- **默认权限**：`init_default_permissions` 为 admin 写入文档/对话/查询/日志/用户/知识库等权限

测试使用独立库：`tests/test_db.db`（由 conftest 设置 `SQLITE_DATABASE`）。

## conftest 提供的 fixture 数据

| fixture | 说明 |
|--------|------|
| `auth_headers` | 管理员 admin 登录后的 `Authorization: Bearer <token>` |
| `test_user_headers` | 普通用户 `testuser` / `test123` 的 token header（若不存在会先由 admin 创建该用户） |
| `extra_kb_id` | 通过 API 创建的「测试知识库2」的 `kb_id`，用于文档/知识库相关用例 |

## 在用例中增加数据

- 需要更多用户：用 `auth_headers` 调 `POST /api/users` 创建，再登录取 header。
- 需要更多知识库：用 `auth_headers` 调 `POST /api/knowledge-bases`。
- 需要文档：可调 `POST /api/documents/upload`（需 multipart 文件）或依赖 ES 的 `ingest-by-path`（需环境）。

## 请求体示例（供手写或生成用例参考）

### 登录
```json
{"username": "admin", "password": "admin123"}
```

### 创建用户（管理员）
```json
{"username": "newuser", "password": "pass123", "nickname": "新用户", "email": ""}
```

### 创建知识库
```json
{"name": "测试库", "description": "描述", "icon": "📚", "color": "#667eea"}
```

### RAG 检索
```json
{"query": "测试问题", "knowledge_base_ids": [], "top_k": 3}
```
