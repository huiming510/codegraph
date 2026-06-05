# RAG 知识库 - 文档目录

本目录为项目开发与协作文档的统一入口，按「目录结构 → 开发文档 → API → 需求与待办」组织。

---

## 文档目录结构

```
docs/
├── README.md                 # 本文件：文档总索引与目录说明
├── 开发框架说明.md            # 整体架构、backend/frontend 职责、前后端约定
├── 后端开发文档.md            # 后端环境、目录、启动、调试、规约
├── 前端开发文档.md            # 前端环境、目录、启动、联调、规约
├── API文档.md                # 接口总览、模块列表、通用约定（详细可查 Swagger）
├── 接口契约.md                # 历史/外部接口契约（如 POS 知识库问答）
├── 需求文档.md                # 需求文档模板与示例
├── TODO.md                   # 项目待办 / 迭代 Todolist
├── 代码检查.md                # 检查脚本、报告、专家 Review、指标、SonarQube
├── 业务实现检查标准.md        # 业务实现衡量维度、验收、注释与可维护性
├── SonarQube与检查标准.md     # SonarQube 参考标准与可选直接使用
├── review-strategy.md        # 架构/业务 Review 策略与权重
├── 测试体系.md                # 前后端测试约定、运行方式、目录与扩展
├── 测试策略与用例生成.md       # 单元/疏通/集成分层、用例自动生成策略、TDD
├── 文档体系.md                # 文档分类、存放位置、维护约定与入口
├── GitLab分支与质量门禁.md     # 分支类型、个人/主分支/发布门禁、CI 行为
├── 数据库设计.md               # 表结构、字段、索引、迁移与初始化
├── 数据库管理与迁移.md          # 本地 DB 管理约定、SQLite/PG 切换、迁移步骤
├── 页面跳转与路由.md           # 前端路由、鉴权、页面与 path 对应、业务流程
├── 架构师视角-检查与Review充分性评估.md  # 检查与 Review 是否足够、全面及缺口与优先级
├── model_deploy.md           # 模型部署相关说明
└── mineru_install.md        # MinerU（PDF 转 Markdown）安装说明
```

---

## 快速导航

| 文档 | 适用场景 |
|------|----------|
| [开发框架说明](./开发框架说明.md) | 新人了解架构、backend/frontend 边界、前后端约定 |
| [后端开发文档](./后端开发文档.md) | 后端环境搭建、运行、目录说明、开发规约 |
| [前端开发文档](./前端开发文档.md) | 前端环境搭建、运行、目录说明、开发规约 |
| [API 文档](./API文档.md) | 接口模块总览、路径列表、请求/响应约定（细项见 Swagger） |
| [需求文档](./需求文档.md) | 写需求说明、版本范围、验收标准 |
| [TODO](./TODO.md) | 记录迭代待办、缺陷、优化项 |
| [代码检查](./代码检查.md) | 检查脚本、报告、专家 Review、指标采集、SonarQube |
| [业务实现检查标准](./业务实现检查标准.md) | 需求覆盖、验收、偏差与遗漏、注释与可维护性（业务 check 依据） |
| [SonarQube与检查标准](./SonarQube与检查标准.md) | 参考 SonarQube 质量模型或直接使用 SonarQube 扫描 |
| [review-strategy](./review-strategy.md) | 配置架构/业务 Review 本期优先与权重 |
| [测试体系](./测试体系.md) | 前后端测试约定、运行方式、目录与扩展 |
| [测试策略与用例生成](./测试策略与用例生成.md) | 单元/疏通/集成分层、用例自动生成策略、TDD 模式 |
| [文档体系](./文档体系.md) | 文档分类、存放位置、维护约定与入口 |
| [GitLab 分支与质量门禁](./GitLab分支与质量门禁.md) | 分支类型、个人/主分支/发布门禁、CI 行为 |
| [数据库设计](./数据库设计.md) | 表结构、字段、索引、迁移与初始化 |
| [数据库管理与迁移](./数据库管理与迁移.md) | `linkrag.db` 管理约定、SQLite/PG 配置、迁移到 PostgreSQL |
| [页面跳转与路由](./页面跳转与路由.md) | 前端路由、鉴权、页面与 path 对应、业务流程 |
| [架构师视角-检查与Review充分性评估](./架构师视角-检查与Review充分性评估.md) | 检查与 Review 是否足够、全面及缺口与优先级建议 |

---

## 项目代码目录结构（简要）

```
linkrag/
├── docs/                    # 文档（本目录）
├── src/
│   ├── backend/             # 后端开发目录（FastAPI）
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database/
│   │   ├── routers/
│   │   ├── llm/
│   │   ├── logger/
│   │   └── server/
│   └── frontend/             # 前端开发目录（Vue3 + Vite）
│       ├── src/
│       │   ├── api/
│       │   ├── views/
│       │   ├── router/
│       │   ├── stores/
│       │   └── ...
│       ├── vite.config.js
│       └── package.json
├── .cursor/rules/            # AI 开发规约（backend/frontend/project）
├── .venv/                    # Python 虚拟环境（项目根）
└── .venv-mineru/             # MinerU 专用环境（可选）
```

其他目录（如 `src/preprocess`、`src/index` 等）为仓库既有能力，开发时以 **backend + frontend** 为主，详见 [开发框架说明](./开发框架说明.md)。

---

## 与代码的对应关系

- **开发目录**：仅 `src/backend`（后端）、`src/frontend`（前端），详见 [开发框架说明](./开发框架说明.md)。
- **在线 API 文档**：后端启动后访问 <http://localhost:8000/docs>（Swagger）。
- **规约与 AI 约束**：见项目根目录 `.cursor/rules/`，与本文档体系配合使用。
- **Agent Skills**：见 `.cursor/skills/`。`linkrag-backend`、`linkrag-frontend` 供 AI 编写后端/前端代码时选用；`read-check-report` 供 AI 解读检查报告；`linkrag-test-cases` 供生成前后端疏通测试；`linkrag-architect-review` 供从架构师角度做目录/命名/分层/复杂度等系统级 Review；`linkrag-business-review` 供从业务专家角度对照需求文档与实现做覆盖与验收检查。
