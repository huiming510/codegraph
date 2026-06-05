# 架构师视角：检查与 Review 是否足够、是否全面

从**系统架构师**角度对当前 Check、Review、测试与指标做一次「充分性」评估：已覆盖什么、缺什么、建议补什么。

---

## 一、当前已覆盖的能力

| 类别 | 内容 | 说明 |
|------|------|------|
| **代码检查（自动化）** | 语法、风格、格式 | 后端 py_compile + ruff check/format；前端 ESLint + Stylelint + Prettier；`check_all.ps1` 一键，CI 可门禁 |
| **指标采集（脚本）** | 结构、规模、关键列表 | 目录是否符合约定、文件行数、超 400 行文件、router 列表、前端 api 路径与 views；供 AI Review 使用 |
| **架构 Review（AI + 指标）** | 目录/命名、分层/依赖、复杂度、文档一致性、安全/性能 | linkrag-architect-review 基于指标 + 策略 + 记忆产出报告；**不替代** check，侧重 check 不覆盖的层面 |
| **业务 Review（AI）** | 需求覆盖、验收、偏差与遗漏 | linkrag-business-review 对照需求文档与业务实现检查标准 |
| **测试** | 疏通/冒烟 | pytest + Vitest，run_tests.ps1；CI 主分支门禁 |
| **全量门禁** | 检查 + 测试 | run_full_check.ps1，适合 MR 前 |
| **可选** | SonarQube | 参考其质量模型或直接跑 SonarScanner，见 docs/SonarQube与检查标准.md |

对**日常提交与 MR 门禁**、**定期架构/业务健康度检查**而言，上述组合已经能支撑「基本足够」：规范可执行、结构可量化、架构与业务有据可查。

---

## 二、从架构师视角看到的缺口

### 2.1 依赖与分层（未自动化）

- **现状**：分层与依赖是否合理，依赖**架构 Review 技能**抽样代码判断（如 router 是否直接写复杂 SQL、前后端依赖方向）。
- **缺口**：没有脚本自动检查「router 只依赖 crud/deps」「无循环 import」等；若项目变大，仅靠抽样容易漏。
- **建议**：  
  - **短期**：继续由架构 Review 按指标抽样，在 review-strategy 中把「分层与依赖」权重保持为高。  
  - **中期**：可增加轻量脚本（如解析 backend 的 import，禁止 `routers/` 直接 import `server/` 或 `llm/` 实现类），失败时 check 或单独 job 报错；或引入 layer-lint / dependency-cruiser 等按需接入。

### 2.2 前后端接口契约一致性（未自动化）

- **现状**：前后端路径、请求/响应是否一致，依赖 API 文档与人工/AI Review。
- **缺口**：没有自动对比「后端注册路由」与「前端 request 的 path」或「API 文档」；新增接口时容易漏改一端。
- **建议**：  
  - **短期**：在架构/业务 Review 中保留「前后端接口对应」检查项；API 文档与 Swagger 作为唯一来源。  
  - **中期**：可写脚本从 backend 路由注册与 frontend api 调用中提取路径列表，输出 diff 报告（如 `reports/api-path-diff.md`），在 CI 或 review_prepare 中可选执行。

### 2.3 测试覆盖率（未做门禁）

- **现状**：有疏通测试与 run_tests；覆盖率可本地跑（pytest --cov、npm run test:coverage），但**未在 CI 中设门禁**。
- **缺口**：无法从架构层面约束「关键模块覆盖率不低于 X」。
- **建议**：  
  - **短期**：保持现状，主分支门禁仍为「测试通过」即可。  
  - **中期**：若需质量门禁，可在 CI 中增加 coverage 采集与阈值（如 backend ≥60%、frontend ≥40%），未达标则失败；阈值写在 docs 或 GitLab 变量中。

### 2.4 安全与依赖漏洞（未纳入 Check）

- **现状**：安全在架构 Review 中为「可选」项（敏感接口鉴权、硬编码等）；无定期依赖漏洞扫描。
- **缺口**：未在 check 或 CI 中跑 `pip audit`、`npm audit`（或类似），已知漏洞依赖可能合入。
- **建议**：  
  - **短期**：在文档中约定「发布前或每月执行一次 pip audit / npm audit」；架构 Review 时提醒。  
  - **中期**：增加可选脚本 `scripts/check_audit.ps1`（pip audit + npm audit），在 release 分支或定时流水线中运行，失败仅告警或按团队策略阻断。

### 2.5 复杂度与重复（仅部分指标）

- **现状**：指标中有「超 400 行文件」；圈复杂度、重复代码块**未**由脚本产出，架构 Review 可抽样提及，SonarQube 可补足。
- **缺口**：无自动的圈复杂度或重复率报表。
- **建议**：  
  - **短期**：继续用「超 400 行」+ AI 抽样；与 SonarQube 质量模型对齐（见 docs/SonarQube与检查标准.md）。  
  - **中期**：若接入 SonarQube，直接使用其 Maintainability/Duplications；若不接入，可加 radon（Python）或 ESLint 复杂度规则，仅输出报告不强制门禁。

### 2.6 注释与契约（未脚本化）

- **现状**：代码注释与 API 契约依赖 .cursor/rules 与业务实现检查标准；无脚本强制「某目录下必须有 docstring/JSDoc」。
- **缺口**：无法用脚本 100% 保证「对外 API 必有注释」。
- **建议**：保持「规约 + 业务/架构 Review」为主；若需可加 ESLint 注释规则或 pydocstyle 仅对 `routers/` 检查，作为可选增强。

---

## 三、结论与优先级建议

| 结论 | 说明 |
|------|------|
| **是否足够** | 对当前阶段的**日常门禁**（规范、格式、疏通测试）和**定期架构/业务 Review**，已**基本足够**：可执行、可追溯、可配置策略与记忆。 |
| **是否全面** | 若按「企业级/发布级」标准，仍有**可补充**项：依赖与分层自动化、前后端路径一致性、覆盖率门禁、依赖漏洞扫描、复杂度/重复度报表；多数可**按优先级逐步加**，不必一次到位。 |

**建议优先级**（按架构师价值/成本比）：

1. **P0（已有）**：check_all、run_tests、collect_metrics + 架构/业务 Review 技能 + review_prepare — 保持并定期跑。
2. **P1（已实现）**：  
   - **依赖漏洞扫描**：`scripts/check_audit.ps1`（后端 pip audit + 前端 npm audit），报告写 `reports/check-audit.log`；可选 `-Strict` 或 `CHECK_AUDIT_STRICT=1` 时发现漏洞则退出码 1，可在 release 或定时流水线中调用。  
   - **前后端 API 路径 diff**：`scripts/collect_api_diff.ps1`（或 `python scripts/metrics/api_path_diff.py`），产出 `reports/api-path-diff.md`，可在 review_prepare 或 CI 中可选执行。  
   - **CI 覆盖率**：`backend-test` / `frontend-test` 已采集 coverage 并产出产物；门禁通过 GitLab 变量 `COVERAGE_BACKEND_MIN`（如 60）与前端 `vite.config.js` 中 `thresholds`（如 lines: 40）配置，详见 [测试体系](./测试体系.md)。
3. **P2（按需）**：依赖分层规则脚本或 layer-lint；SonarQube 直接使用；注释/契约的轻量规则。

---

## 四、与现有文档的对应

| 文档 | 说明 |
|------|------|
| [代码检查](./代码检查.md) | 检查脚本、报告、专家 Review 与 SonarQube |
| [review-strategy](./review-strategy.md) | 架构/业务 Review 策略与权重 |
| [SonarQube与检查标准](./SonarQube与检查标准.md) | 质量模型与参考/直接使用方式 |
| [scripts/README](../scripts/README.md) | 脚本索引与推荐顺序 |

本评估可作为「架构师视角下检查与 Review 是否足够、是否全面」的共识文档，随项目演进可更新「缺口」与「建议」列表。
