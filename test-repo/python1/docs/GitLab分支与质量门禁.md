# GitLab 分支与质量门禁

本文约定仓库分支类型、合并/发布前必须通过的检查与测试，便于在 GitLab CI 中落地「个人分支只跑 Check、主分支/发布分支跑 Check + 测试」。

---

## 一、分支类型与约定

| 分支类型 | 命名示例 | 用途 | 质量门禁（见下表） |
|----------|----------|------|--------------------|
| **发布分支** | `release/*`、打 tag 发布 | 对外发布版本，需最严门禁 | 发布门禁 |
| **内部开发主分支** | `main`、`develop` | 日常集成，合并前需通过测试 | 主分支门禁 |
| **个人/功能分支** | `feature/*`、`fix/*`、个人名等 | 开发与 MR，只要求代码规范 | 个人分支门禁 |

- **main**：与 GitLab 默认分支名一致，可作为「可发布」或「内部主分支」。
- **develop**：可选；若存在，作为集成开发分支，合并到 `main` 前应已通过主分支门禁。
- **release/xxx**：从 main/develop 拉出，用于发版；合并回 main 或打 tag 前需满足发布门禁。
- **feature/xxx、fix/xxx**：个人开发分支，合并到 main/develop 前只需满足个人分支门禁；MR 时由目标分支决定是否跑测试（见下）。

---

## 二、质量门禁定义

### 2.1 个人分支门禁（仅 Check，不强制测试）

**适用**：`feature/*`、`fix/*` 及未匹配到「主分支/发布」的任意分支上的 push 或 MR。

| 项 | 说明 | CI 对应 |
|----|------|--------|
| 后端 Check | 语法（py_compile）+ ruff check + ruff format --check | `backend-check` |
| 前端 Check | ESLint + Stylelint + Prettier check（npm run check） | `frontend-check` |

**通过条件**：上述两项均通过即可合并到 main/develop（若目标分支要求测试，则 MR 时会额外跑主分支门禁）。

**不要求**：后端 pytest、前端 Vitest 可不跑或选跑，由团队约定是否在 MR 到 main 时再跑。

---

### 2.2 主分支门禁（Check + 测试）

**适用**：分支名为 `main`、`develop` 的 push，以及 **MR 目标分支为 main 或 develop** 时的 MR 流水线。

| 项 | 说明 | CI 对应 |
|----|------|--------|
| 后端 Check | 同个人分支 | `backend-check` |
| 前端 Check | 同个人分支 | `frontend-check` |
| 后端测试 | pytest src/backend/tests（疏通/冒烟） | `backend-test` |
| 前端测试 | Vitest 单次运行（npm run test:run） | `frontend-test` |

**通过条件**：4 项全部通过才允许合并到 main/develop。

---

### 2.3 发布门禁（Check + 测试，可扩展）

**适用**：分支名为 `release/*` 的 push，或 **打 tag 触发发布** 的流水线。

| 项 | 说明 | CI 对应 |
|----|------|--------|
| 后端 Check | 同主分支 | `backend-check` |
| 前端 Check | 同主分支 | `frontend-check` |
| 后端测试 | 同主分支，建议必跑 | `backend-test` |
| 前端测试 | 同主分支，建议必跑 | `frontend-test` |
| 可选 | SonarQube 扫描、覆盖率报告、构建产物 | 按需在 CI 中增加 job |

**通过条件**：至少 Check + 后端测试 + 前端测试 全部通过后才允许合并到 main 或打 tag 发布。

---

## 三、CI 行为摘要（与 .gitlab-ci.yml 对应）

| 场景 | 跑 Check | 跑测试 |
|------|----------|--------|
| Push 到 feature/*、fix/*、个人分支 | ✅ | ❌ |
| Push 到 main、develop | ✅ | ✅ |
| Push 到 release/* | ✅ | ✅ |
| MR 目标为 main / develop | ✅ | ✅ |
| MR 目标为其他分支 | ✅ | ❌（或按需） |
| 按 tag 触发发布 | ✅ | ✅ |

- **Check**：每次 push 与 MR 都会跑，保证代码规范。
- **测试**：仅在「主分支 / 发布分支 / MR 进主分支」时跑，个人分支不强制测试，减少等待时间。

---

## 四、本地与 CI 命令对照

| 门禁项 | 本地（项目根） | CI 中（Linux） |
|--------|----------------|----------------|
| 后端 Check | `.\scripts\check_backend.ps1` | `ruff check src/backend`、`ruff format --check src/backend`、语法检查 |
| 前端 Check | `.\scripts\check_frontend.ps1` | `cd src/frontend && npm ci && npm run check` |
| 后端测试 | `.\scripts\run_tests.ps1` 或 `pytest src/backend/tests` | `pytest` + coverage（xml/term）；可选变量 `COVERAGE_BACKEND_MIN` 设覆盖率门禁 |
| 前端测试 | 在 src/frontend 下 `npm run test:run` | `npm run test:coverage`，产物在 `src/frontend/coverage/` |
| 依赖漏洞（P1 可选） | `.\scripts\check_audit.ps1` | 可在 release 或定时流水线中增加 job 调用 |

---

## 五、相关文档

| 文档 | 说明 |
|------|------|
| [测试体系](./测试体系.md) | 前后端测试约定、目录、运行方式 |
| [代码检查](./代码检查.md) | 检查脚本、报告、ruff/ESLint 等 |
| [文档体系](./文档体系.md) | 文档分类与维护 |

仓库根目录 **`.gitlab-ci.yml`** 已按上述分支与门禁实现：个人分支只跑 Check，main/develop/release 及 MR 进主分支时跑 Check + 测试。

若主分支名为 `master` 而非 `main`，在 `.gitlab-ci.yml` 的 `backend-test`、`frontend-test` 的 `rules` 中增加一行：`- if: $CI_COMMIT_BRANCH == "master"`，并在 MR 规则中把 `main` 改为 `master` 即可。
