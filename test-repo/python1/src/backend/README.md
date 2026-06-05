# LinkRAG Backend

FastAPI 后端，负责认证、知识库/文档管理、LLM 配置、RAG 问答与解析入库等。本文说明目录结构、可用工具、开发规约与文档入口。

---

## 目录结构

```
src/backend/
├── main.py              # 应用入口：FastAPI、生命周期、异常处理、路由挂载
├── config.py            # 应用配置（Pydantic Settings，.env）
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量示例
├── database/            # 数据层
│   ├── models.py        # SQLAlchemy 模型（表结构）
│   ├── crud.py          # 增删改查封装
│   └── connection.py    # 异步会话与引擎
├── routers/             # 业务路由（按模块拆分）
│   ├── common.py        # success_response 等公共工具
│   ├── deps.py          # JWT、require_user、require_admin
│   ├── auth.py          # 登录、注册、登出、菜单
│   ├── users.py         # 用户 CRUD
│   ├── permissions.py   # 权限列表
│   ├── knowledge_bases.py  # 知识库 CRUD、文档列表
│   ├── documents.py     # 文档上传、解析状态、文件夹
│   ├── llm.py           # LLM 配置与模型
│   ├── embedding.py     # 嵌入模型配置
│   ├── config.py        # 系统配置（ES、locale）
│   ├── rag.py           # RAG 问答、对话、应用
│   └── logs.py          # 查询日志、系统日志
├── llm/                 # LLM 抽象与多厂商实现
├── logger/              # 日志配置与请求日志中间件
└── server/              # 解析 worker、ES、RAG 服务（依赖项目 preprocess、index）
```

---

## 工具与命令

### 启动服务

在**项目根目录**设置 `PYTHONPATH` 后，在本目录或项目根执行：

```powershell
# 项目根目录
$env:PYTHONPATH = ".\src"   # 或绝对路径，如 d:\ai-rag\linkrag\src
cd src\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 接口文档（Swagger）：<http://localhost:8000/docs>
- 首次运行前在项目根安装依赖：`pip install -r src/backend/requirements.txt`，建议安装 `PyYAML`（解析 worker 需要）。

### 代码检查

在**项目根目录**执行：

| 命令 | 说明 |
|------|------|
| `.\scripts\check_backend.ps1` | 语法检查（py_compile）+ 若已安装 ruff 则做规范与格式检查 |
| `.\scripts\check_all.ps1` | 后端 + 前端一起检查 |

安装 ruff 后可做规范与格式检查及自动修复：

```powershell
pip install ruff
ruff check src/backend --fix
ruff format src/backend
```

ruff 配置在项目根 `pyproject.toml` 的 `[tool.ruff]`。

---

## 开发规约与文档

- **规约（AI 与人工均遵守）**：项目根 `.cursor/rules/backend-conventions.mdc`  
  - 统一响应 `success_response(data=...)`、认证用 `require_user`/`require_admin`、新路由在 `main.py` 挂载等。
- **技能（AI 生成后端代码时）**：项目根 `.cursor/skills/linkrag-backend/`  
  - 含约定摘要与最小模板，便于生成符合项目的代码。

**文档（均在项目根 `docs/` 下）：**

| 文档 | 说明 |
|------|------|
| [开发框架说明](../../docs/开发框架说明.md) | 整体架构、backend/frontend 边界、前后端约定 |
| [后端开发文档](../../docs/后端开发文档.md) | 环境、目录、启动、配置、规约摘要、常见问题 |
| [API 文档](../../docs/API文档.md) | 接口模块与路径总览（细项见 Swagger） |
| [代码检查](../../docs/代码检查.md) | 检查脚本用法与报告位置；可让 AI 解读 `reports/check-report.md`（read-check-report 技能） |

---

## 响应与认证约定

- 所有接口统一响应体：`{ "code": number, "data": any, "msg": string }`。成功用 `success_response(data=...)`，失败用 `HTTPException`。
- 需要登录：`Depends(require_user)`；需要管理员：`Depends(require_admin)`。从 `routers.deps` 导入，勿重复实现 JWT。
