# API 文档

本文档提供接口**模块总览**与**路径列表**，便于前后端对齐。详细请求/响应体、参数说明以后端 **Swagger** 为准：启动后端后访问 <http://localhost:8000/docs>。

---

## 1. 通用约定

### 1.1 基础地址与前缀

- 开发环境：前端通过 Vite 代理将 `/api` 转发到后端（如 `http://localhost:8000`）。
- 所有业务接口前缀：**/api**。

### 1.2 统一响应体（测试用例必须依此断言）

```json
{
  "code": 0,
  "data": { ... },
  "msg": "success"
}
```

| 字段 | 类型 | 约定 |
|------|------|------|
| **code** | int | **成功固定为 0**；失败为 4xx/5xx 或业务错误码。测试断言成功时用 `code == 0`。 |
| **data** | object \| null | 成功时有效载荷；失败时多为 `null`。 |
| **msg** | string | 提示信息。 |

> **测试依据**：后端 `success_response()` 返回 `code: 0`。生成或编写接口测试时，必须以本文档为准，断言 `data.get("code") == 0`（成功）或 `data.get("code") != 0`（失败），勿使用 `code == 200`。

### 1.3 认证

- 需要登录的接口：请求头携带 `Authorization: Bearer <token>`。
- 未登录或 token 无效：返回 401，前端跳转登录页。

---

## 2. 模块与路径总览

### 2.1 认证 / 登录（/api/auth）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 登录 |
| POST | /api/auth/register | 注册 |
| POST | /api/auth/logout | 登出 |
| GET  | /api/auth/userinfo | 当前用户信息 |
| PUT  | /api/auth/password | 修改密码 |
| GET  | /api/auth/menu | 菜单（用于动态路由） |

### 2.2 用户管理（/api/users）

角色（鉴权中心）：**admin**=管理员，**user**=开发人员，**guest**=用户。创建/更新用户时可传 `role`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | /api/users | 用户列表（可选 ?role=） |
| POST   | /api/users | 创建用户（body 可含 role） |
| PUT    | /api/users/{user_id} | 更新用户（含 role） |
| PUT    | /api/users/{user_id}/password | 管理员重置用户密码（body: { password }） |
| DELETE | /api/users/{user_id} | 删除用户 |

### 2.3 权限（/api/permissions）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/permissions | 权限列表 |

### 2.4 知识库（/api/knowledge-bases）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET    | /api/knowledge-bases | 知识库列表 |
| POST   | /api/knowledge-bases | 创建知识库 |
| GET    | /api/knowledge-bases/{kb_id} | 知识库详情 |
| PUT    | /api/knowledge-bases/{kb_id} | 更新知识库 |
| DELETE | /api/knowledge-bases/{kb_id} | 删除知识库 |
| GET    | /api/knowledge-bases/{kb_id}/documents | 知识库下文档列表 |

### 2.5 文档（/api）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传文件 |
| POST | /api/ingest-by-path | 按路径入库 |
| POST | /api/documents/{doc_id}/parse-status | 上报解析状态 |
| POST | /api/documents/{doc_id}/trigger-parse | 触发解析 |
| GET  | /api/documents | 文档列表 |
| DELETE | /api/documents/{doc_id} | 删除文档 |
| GET  | /api/doc-folders/virtual-folders | 虚拟文件夹列表 |
| POST | /api/doc-folders/virtual-folders | 创建虚拟文件夹 |
| DELETE | /api/doc-folders/virtual-folders/{vf_id} | 删除虚拟文件夹 |
| GET  | /api/doc-folders/assignments | 文件夹与文档关联 |
| PUT  | /api/doc-folders/assignments | 更新关联 |

### 2.6 LLM（/api/llm）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | /api/llm/default-models | 默认模型列表 |
| GET  | /api/llm/default-model-options | 默认模型选项 |
| POST | /api/llm/default-models | 设置默认模型 |
| GET  | /api/llm/added-providers | 已添加的提供商 |
| GET  | /api/llm/optional-providers | 可选提供商 |
| GET  | /api/llm/optional-models | 可选模型 |
| GET  | /api/llm/tree | 模型树 |
| GET  | /api/llm/models | 模型列表 |
| GET  | /api/llm/providers | 提供商列表 |
| GET  | /api/llm/config | 当前配置 |
| DELETE | /api/llm/config | 删除配置 |
| POST | /api/llm/config | 保存配置 |
| POST | /api/llm/test | 测试连接 |

### 2.7 嵌入模型（/api/embedding）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | /api/embedding/providers | 提供商列表 |
| POST | /api/embedding/config | 保存配置 |
| POST | /api/embedding/test | 测试 |

### 2.8 系统配置（/api/config）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/config/current | 当前配置 |
| GET | /api/config/es | ES 配置 |
| PUT | /api/config/es | 更新 ES 配置 |
| GET | /api/config/locale | 语言配置 |
| PUT | /api/config/locale | 更新语言配置 |

### 2.9 RAG / 对话（/api）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/query | RAG 问答 |
| POST | /api/chat | 对话（非流式） |
| POST | /api/chat/stream | 对话（流式） |
| POST | /api/chat/stream-external | 多轮流式对话代理（转发外部 API，并持久化消息到 chat_messages） |
| GET  | /api/chat/history/{session_id} | 会话历史（仅返回当前用户归属的对话） |
| PUT  | /api/chat/sessions/{session_key} | 更新会话/对话标题 |
| GET  | /api/chat/sessions | 会话列表 |
| POST | /api/search-apps | 创建检索应用 |
| GET  | /api/search-apps | 检索应用列表 |
| GET  | /api/search-apps/{app_id} | 检索应用详情 |
| PUT  | /api/search-apps/{app_id} | 更新检索应用 |
| DELETE | /api/search-apps/{app_id} | 删除检索应用 |
| POST | /api/chat-apps | 创建助手（对话应用） |
| GET  | /api/chat-apps | 助手列表（仅 app_ 且无 parent） |
| GET  | /api/chat-apps/{session_key} | 助手详情 |
| GET  | /api/chat-apps/{app_session_key}/conversations | 某助手下对话列表 |
| POST | /api/chat-apps/{app_session_key}/conversations | 在助手下新建对话 |
| PUT  | /api/chat-apps/{session_key} | 更新助手 |
| PUT  | /api/chat-apps/{session_key}/config | 仅更新助手对话配置（search_options、generate_options） |
| DELETE | /api/chat-apps/{session_key} | 删除助手 |

### 2.10 日志（/api/logs）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/logs/query | 查询日志 |
| GET | /api/logs/system | 系统日志 |

---

## 3. 前端 API 模块对应关系

| 后端模块 | 前端 api/modules 文件 |
|----------|------------------------|
| auth | login.js |
| users | user.js |
| knowledge-bases | knowledgeBase.js |
| documents / upload | document.js |
| config | esConfig.js、llmConfig.js、locale.js |
| llm | llmConfig.js |
| rag / chat | chat.js、chatApp.js、queryRag.js、searchApp.js |
| logs | logs.js |

新增接口时，在对应 `api/modules/xxx.js` 中增加方法，路径与上表保持一致（请求时 baseURL 已含 `/api`，故写相对路径如 `/knowledge-bases` 即可）。
