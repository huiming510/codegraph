# RAG 知识库 (LinkRAG)

## 项目说明

本仓库为 RAG 知识库系统，日常开发目录为 **src/backend**（FastAPI 后端）与 **src/frontend**（Vue3 前端），其余目录为既有能力与依赖。

- **后端**：Python 3.12+，FastAPI，SQLite，JWT，可选 Elasticsearch。接口文档：启动后访问 `/docs`。
- **前端**：Vue 3 + Vite + Ant Design Vue，Pinia，Vue Router。开发端口默认 5174，代理 `/api` 到后端。

---

## 快速开始

### 后端

```powershell
$env:PYTHONPATH = ".\src"
cd src\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

依赖：项目根目录 `pip install -r src/backend/requirements.txt`（建议安装 PyYAML）。

### 前端

```powershell
cd src\frontend
npm.cmd install
npm.cmd run dev
```

PowerShell 下若无法执行 `npm`，请使用 `npm.cmd` 或改用 CMD。详见 [src/frontend/README.md](src/frontend/README.md)。

---

## 开发规范与使用指南

项目有一套完整规范：**代码检查**、**代码注释规则**、**业务实现与验收标准**、**专家 Review**（架构 + 业务）、以及可选的 **SonarQube**。下面说明各自做什么、怎么用，方便大家按规范协作并防止垃圾代码堆叠。

### 规范体系总览

| 类型 | 作用 | 入口 / 文档 |
|------|------|----------------|
| **代码规范与格式** | 语法、风格、格式（ESLint / Prettier / ruff） | `.\scripts\check_all.ps1` → [代码检查](docs/代码检查.md) |
| **代码注释规则** | 对外 API 与复杂逻辑必须注释，防止无注释垃圾代码 | [.cursor/rules/code-comments.mdc](.cursor/rules/code-comments.mdc) |
| **业务实现标准** | 需求覆盖、验收达成、偏差与遗漏、注释可维护性 | [业务实现检查标准](docs/业务实现检查标准.md) |
| **架构 Review** | 目录、分层、复杂度、与文档一致性 | 先跑 `collect_metrics.ps1`，再用技能 linkrag-architect-review |
| **业务 Review** | 需求与实现对照、可验收性、注释检查 | 技能 linkrag-business-review，标准见上 |
| **质量参考** | 与 SonarQube 质量模型对齐（可选直接跑 SonarQube） | [SonarQube与检查标准](docs/SonarQube与检查标准.md) |

---

### 1. 代码检查（提交前必做）

在**项目根目录**执行：

```powershell
.\scripts\check_all.ps1
```

- 依次执行后端（语法 + ruff）、前端（ESLint + Stylelint + Prettier）检查。
- 报告生成在 **reports/**：`check-report.md`（汇总）、`check-backend.log`、`check-frontend.log`。
- 让 AI 解读：对 AI 说「看下检查报告」「如何处理检查结果」，会按 **read-check-report** 技能给出修复建议。

| 目的 | 命令 |
|------|------|
| 后端 + 前端一起检查 | `.\scripts\check_all.ps1` |
| 仅后端 | `.\scripts\check_backend.ps1` |
| 仅前端 | `.\scripts\check_frontend.ps1` 或 `cd src/frontend && npm run check` |
| 前端检查并自动修复 | `cd src/frontend && npm run check:fix` |

详见 [docs/代码检查.md](docs/代码检查.md)。

---

### 2. 代码注释规则（防止垃圾代码堆叠）

- **规约文件**：[.cursor/rules/code-comments.mdc](.cursor/rules/code-comments.mdc)（后端 + 前端统一）。
- **必须注释**：文件/模块头、**对外 API**（后端路由、前端 `api/modules` 导出）、复杂业务逻辑；需写清「做什么」、参数/返回值或意图。
- **禁止**：大段注释掉的废代码（应删除）、无信息量注释（如「这里循环」）、与实现不符的注释。
- 业务 Review 时会按此规则抽查，缺注释会标注「需补充注释」。后端开发规约见 [.cursor/rules/backend-conventions.mdc](.cursor/rules/backend-conventions.mdc)，前端见 [.cursor/rules/frontend-conventions.mdc](.cursor/rules/frontend-conventions.mdc)。

---

### 3. 业务实现与验收标准

- **标准文档**：[docs/业务实现检查标准.md](docs/业务实现检查标准.md)。
- **衡量维度**：需求可追溯、功能覆盖、验收标准达成、偏差与遗漏、边界与异常、接口一致、**代码注释与可维护性**。
- **怎么用**：对 AI 说「对照需求文档 check 实现」「业务专家 review」「验收前检查」，会使用 **linkrag-business-review** 技能，按需求文档（默认 `docs/需求文档.md`）与上述标准产出对照报告。策略与权重在 [docs/review-strategy.md](docs/review-strategy.md) 中配置。

---

### 4. 专家 Review（架构 + 业务）

**架构师 Review**（目录、分层、复杂度、与文档一致）：

1. 在项目根目录先跑指标脚本：`.\scripts\collect_metrics.ps1`
2. 生成 `reports/metrics-backend.json`、`reports/metrics-frontend.json`
3. 对 AI 说「架构 review」「目录规范」「复杂度检查」，会使用 **linkrag-architect-review**，先读指标再出报告

**业务 Review**（需求与实现对照、可验收性、注释）：

- 对 AI 说「需求与实现对照」「业务专家 check」「验收前检查」，会使用 **linkrag-business-review**，按 [业务实现检查标准](docs/业务实现检查标准.md) 与 [code-comments.mdc](.cursor/rules/code-comments.mdc) 出报告。

**策略与记忆**：`docs/review-strategy.md` 可配置本期优先维度；Review 结论会追加到 `.cursor/review-memory.md`，下次会参考并检查「上次问题是否已改进」。

详见 [docs/代码检查.md#5-专家-review-与指标采集](docs/代码检查.md#5-专家-review-与指标采集)。

---

### 5. SonarQube（参考标准 / 可选直接使用）

- **参考标准**：不部署 SonarQube 时，架构与业务 Review 的维度已与 SonarQube 质量模型（可靠性、安全、可维护性、覆盖率、重复）对齐，见 [docs/SonarQube与检查标准.md](docs/SonarQube与检查标准.md)。
- **直接使用**：若已部署 SonarQube/SonarCloud，配置根目录 `sonar-project.properties` 后执行 `.\scripts\run_sonar.ps1`（需安装 SonarScanner CLI），与现有 check、metrics 可并行。

---

### 6. 规约与技能一览

| 类别 | 路径 | 说明 |
|------|------|------|
| **规约** | [.cursor/rules/project-overview.mdc](.cursor/rules/project-overview.mdc) | 项目范围、开发目录（仅 backend + frontend） |
| | [.cursor/rules/backend-conventions.mdc](.cursor/rules/backend-conventions.mdc) | 后端目录、路由、响应、认证、注释 |
| | [.cursor/rules/frontend-conventions.mdc](.cursor/rules/frontend-conventions.mdc) | 前端 API、路由、状态、注释 |
| | [.cursor/rules/code-comments.mdc](.cursor/rules/code-comments.mdc) | 代码注释规则（防垃圾代码） |
| **技能** | .cursor/skills/linkrag-backend | 后端开发时 AI 遵循后端规约 |
| | .cursor/skills/linkrag-frontend | 前端开发时 AI 遵循前端规约 |
| | .cursor/skills/read-check-report | 解读检查报告并给出修复建议 |
| | .cursor/skills/linkrag-test-cases | 生成后端 pytest / 前端 Vitest 测试用例 |
| | .cursor/skills/linkrag-architect-review | 架构师视角 Review（需先 run collect_metrics） |
| | .cursor/skills/linkrag-business-review | 业务专家视角：需求与实现对照、验收、注释 |

---

### 推荐使用流程

- **日常提交前**：运行 `.\scripts\check_all.ps1`，失败则修复后再提交；需要时让 AI「看下检查报告」。
- **迭代/提测前**：先跑 `.\scripts\collect_metrics.ps1`，再让 AI 做「架构 review」和「业务 review」；需求按 [业务实现检查标准](docs/业务实现检查标准.md) 与 [代码注释规则](.cursor/rules/code-comments.mdc) 做对照与注释抽查。
- **写需求/验收**：使用 [docs/需求文档.md](docs/需求文档.md) 模板，并在 [docs/review-strategy.md](docs/review-strategy.md) 中配置本期业务 Review 重点。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 文档总索引与目录结构 |
| [docs/开发框架说明.md](docs/开发框架说明.md) | 整体架构、前后端约定 |
| [docs/后端开发文档.md](docs/后端开发文档.md) | 后端环境、启动、规约 |
| [docs/前端开发文档.md](docs/前端开发文档.md) | 前端环境、启动、规约 |
| [docs/API文档.md](docs/API文档.md) | 接口模块与路径总览 |
| [docs/代码检查.md](docs/代码检查.md) | 检查脚本、报告、专家 Review、SonarQube |
| [docs/业务实现检查标准.md](docs/业务实现检查标准.md) | 业务实现衡量维度与注释规范 |
| [docs/SonarQube与检查标准.md](docs/SonarQube与检查标准.md) | SonarQube 参考标准与可选直接使用 |
| [docs/需求文档.md](docs/需求文档.md) | 需求模板与验收标准 |
| [docs/review-strategy.md](docs/review-strategy.md) | 架构/业务 Review 策略与权重 |

---

## 目录结构（简要）

```
linkrag/
├── docs/              # 文档（框架说明、API、需求、代码检查、业务标准、SonarQube 等）
├── scripts/           # 检查与指标脚本（check_all.ps1、collect_metrics.ps1、run_sonar.ps1）
├── src/
│   ├── backend/       # 后端（见 src/backend/README.md）
│   └── frontend/      # 前端（见 src/frontend/README.md）
├── .cursor/
│   ├── rules/         # 开发规约（project-overview、backend、frontend、code-comments）
│   └── skills/       # AI 技能（backend、frontend、read-check-report、test-cases、architect-review、business-review）
└── reports/           # 检查报告与指标（check-report.md、metrics-*.json 等，运行脚本后生成，已 gitignore）
```

---

*必须遥遥领先，也必然遥遥领先。*
