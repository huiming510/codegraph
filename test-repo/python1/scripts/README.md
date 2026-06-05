# 脚本说明（Check / Review / Test）

所有脚本均在**项目根目录**执行，例如：`.\scripts\check_all.ps1`。输出目录统一为 `reports/`（已 gitignore）。

---

## 一、Check（代码检查）

| 脚本 | 用途 | 说明 |
|------|------|------|
| **check_all.ps1** | 一键检查 | 先后端、再前端，生成 `reports/check-report.md` 与 log；任一失败退出码 1 |
| **check_backend.ps1** | 仅后端 | 语法（py_compile）+ 若已安装 ruff 则 `ruff check`、`ruff format --check` |
| **check_frontend.ps1** | 仅前端 | 在 `src/frontend` 下执行 `npm run check`（ESLint + Stylelint + Prettier） |
| **check_fix.ps1** | 一键修复 | 后端 ruff format + ruff check --fix；前端 npm run check:fix；仅修复可自动修复项 |

**报告**：`reports/check-report.md`、`reports/check-backend.log`、`reports/check-frontend.log`。用 AI 技能 **read-check-report** 可解读并给出修复建议。

---

## 二、Review（专家审核前置）

| 脚本 | 用途 | 说明 |
|------|------|------|
| **collect_metrics.ps1** | 采集指标 | 生成 `reports/metrics-backend.json`、`reports/metrics-frontend.json`、`reports/metrics-summary.md`，供 AI 架构/业务 Review 使用 |
| **review_prepare.ps1** | Review 准备 | 先执行 collect_metrics，再生成 `reports/review-checklist.md`，并提示使用 linkrag-architect-review / linkrag-business-review |
| **collect_api_diff.ps1** | 前后端 API 路径 diff | 运行 `scripts/metrics/api_path_diff.py`，生成 `reports/api-path-diff.md`（仅后端有/仅前端有/两端一致），可在 review_prepare 或 CI 中可选执行 |

**流程**：先跑 `review_prepare.ps1` 或 `collect_metrics.ps1`，再让 AI 使用 **linkrag-architect-review**、**linkrag-business-review** 根据指标与策略出报告。策略见 `docs/review-strategy.md`，记忆见 `.cursor/review-memory.md`。

---

## 三、Test（测试）

| 脚本 | 用途 | 说明 |
|------|------|------|
| **run_tests.ps1** | 前后端测试 | 后端 pytest、前端 vitest run；任一失败退出码 1 |
| **generate_test_report.ps1** | 图文测试报告 | 运行后端+前端+E2E 测试，收集截图，生成 `reports/test-report-with-screenshots.md`；配合技能 **test-report-with-screenshots** 使用 |

**依赖**：后端 `pip install pytest pytest-asyncio httpx`；前端在 `src/frontend` 下 `npm install`；E2E 需 `npx playwright install chromium`。

---

## 四、全量门禁与可选

| 脚本 | 用途 | 说明 |
|------|------|------|
| **run_full_check.ps1** | 提交前全量 | 先 check_all，再 run_tests；全部通过才退出 0，适合 MR 前或本地自检 |
| **run_sonar.ps1** | SonarQube 扫描 | 需配置 `sonar-project.properties` 与 SonarScanner CLI；详见 `docs/SonarQube与检查标准.md` |

---

## 五、发布（Linux）

| 脚本 | 用途 | 说明 |
|------|------|------|
| **deploy_linux.sh** | 前后端 + Nginx 发布 | 传统发布方式，前端静态资源由 Nginx 托管，后端由 systemd 管理 |
| **deploy_python_only.sh** | 无 Nginx 一体化发布 | 前端打包后复制到 `src/backend/frontend_dist`，由 FastAPI 直接托管（`SERVE_FRONTEND=true`） |

一体化发布适合内网/轻量场景；生产高并发场景仍建议 Nginx 反向代理与静态加速。

---

## 六、推荐顺序

| 场景 | 建议命令 |
|------|----------|
| 提交前只做规范/格式 | `.\scripts\check_all.ps1` |
| 提交前自动修格式 | `.\scripts\check_fix.ps1`，再 `.\scripts\check_all.ps1` |
| 提交前全量（检查 + 测试） | `.\scripts\run_full_check.ps1` |
| 做架构/业务 Review 前 | `.\scripts\review_prepare.ps1`，再让 AI 执行对应 Review 技能 |
| 仅跑测试 | `.\scripts\run_tests.ps1` |

---

## 七、与文档的对应

| 文档 | 说明 |
|------|------|
| [代码检查](docs/代码检查.md) | 检查脚本用法、报告位置、专家 Review 与 SonarQube |
| [review-strategy](docs/review-strategy.md) | 架构/业务 Review 策略与权重 |
| [测试体系](docs/测试体系.md) | 测试目录、运行方式、分层 |
| [GitLab 分支与质量门禁](docs/GitLab分支与质量门禁.md) | CI 中对应 job 与分支规则 |
| [架构师视角-检查与Review充分性评估](docs/架构师视角-检查与Review充分性评估.md) | 检查与 Review 是否足够、全面及缺口与优先级 |
