# SonarQube 与检查标准

本项目支持两种与 SonarQube 的衔接方式：**参考其检查标准**（不跑 SonarQube），或**直接使用 SonarQube** 做扫描并查看报告。

---

## 一、SonarQube 质量模型（可参考的标准）

SonarQube 按以下维度评估代码质量，我们的架构 Review 与指标可与之一致：

| 维度 | 说明 | 对应本项目的关注点 |
|------|------|---------------------|
| **Reliability（可靠性）** | Bug：可能导致错误行为的代码 | 空指针、逻辑错误、异常处理；ESLint/ruff 规则中的部分项 |
| **Security（安全）** | Vulnerability：可能被利用的安全问题；Security Hotspot：需人工确认的敏感点 | 硬编码密钥、SQL 注入、XSS、敏感接口鉴权 |
| **Maintainability（可维护性）** | Code Smell：可维护性差、技术债 | 重复代码、过长函数/文件、圈复杂度、命名与结构 |
| **Coverage（覆盖率）** | 单元测试/集成测试覆盖 | 本项目的 linkrag-test-cases 与 pytest/Vitest |
| **Duplications（重复）** | 重复代码块比例 | 可被指标脚本或 Sonar 扫描产出 |

**规则**：SonarQube 为各语言提供大量规则（如 Python、JavaScript/TypeScript、Vue），详见 [SonarQube Rules](https://docs.sonarsource.com/sonarqube/latest/user-guide/rules/)。「参考标准」时，可让架构 Review 的结论与上述维度对齐；「直接使用」时，由 SonarQube 按规则产出 Issues 与质量门禁。

---

## 二、方式一：参考 SonarQube 标准（不跑 SonarQube）

- **做法**：不部署 SonarQube 服务，也不跑 SonarScanner。在**架构 Review 技能**、**指标脚本**和**文档**中，明确「检查维度与 SonarQube 质量模型对齐」。
- **优点**：无额外基础设施，现有 `check_*.ps1`、`collect_metrics.ps1` 与 AI Review 即可；规则与阈值可由团队在 `docs/review-strategy.md` 中自定。
- **可对齐的项**：
  - **可维护性**：目录结构、文件/函数行数、超 400 行文件（已有）、圈复杂度（可加）、重复代码（可加工具或人工抽样）。
  - **可靠性/安全**：依赖 ESLint、ruff、Bandit 等已有或可加的规则；Review 时提示「与 Sonar 的 Bug/Vulnerability 概念一致」。
  - **覆盖率/重复**：测试用例与覆盖率由 pytest/Vitest 产出；重复可由脚本或 Sonar 规则描述参考。
- **实施**：在 `.cursor/skills/linkrag-architect-review` 的 SKILL 或 reference 中增加一句：架构 Review 的维度与 **SonarQube 质量模型**（Reliability、Security、Maintainability、Coverage、Duplications）对齐，便于团队统一话术和后续接入 SonarQube。

---

## 三、方式二：直接使用 SonarQube

- **做法**：部署 SonarQube Server（或使用 [SonarCloud](https://sonarcloud.io/)），在项目中配置 SonarScanner，对**后端（Python）**与**前端（JavaScript/Vue）**分别或一起扫描，在 SonarQube 界面查看质量门禁、Issues、覆盖率等。
- **优点**：规则与质量门禁开箱可用、报告可视化、可与 CI 集成、支持多语言统一视图。
- **前置**：
  - 已安装 **SonarQube Server**（或已创建 SonarCloud 项目）。
  - 已安装 **SonarScanner CLI**（或使用 npm `sonar-scanner` 用于前端），并配置好 `sonar.host.url`、`sonar.login`（Token）、项目 `projectKey`。

### 3.1 项目配置示例

可在项目根目录放置 **`sonar-project.properties`**（单项目扫描 backend + frontend）或拆成多模块。以下为**单项目、多语言**示例（按需修改 `projectKey`、`sonar.host.url`、`sonar.login`）：

```properties
# sonar-project.properties（项目根目录）
sonar.projectKey=linkrag
sonar.projectName=LinkRAG
sonar.sourceEncoding=UTF-8

# 多语言：同时扫描后端 Python 与前端 JS/Vue
sonar.sources=src/backend,src/frontend/src
sonar.exclusions=**/node_modules/**,**/__pycache__/**,**/.venv/**,**/dist/**,**/coverage/**,**/*.min.js

# 若使用 SonarCloud 或远程 Server，取消注释并填写：
# sonar.host.url=https://your-sonarqube.example.com
# sonar.login=你的Token
```

- **仅扫描后端**：`sonar.sources=src/backend`，排除 `src/frontend`。
- **仅扫描前端**：`sonar.sources=src/frontend/src`，排除 `src/backend`。

### 3.2 运行扫描

- **CLI**（需已安装 [SonarScanner CLI](https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/) 并加入 PATH）：

  ```powershell
  cd 项目根目录
  sonar-scanner
  ```

- **npm**（仅前端时可用）：在 `src/frontend` 下安装 `sonar-scanner`，并在该目录下配置 `sonar.projectKey` 等后执行 `npx sonar-scanner`。

可将上述命令封装为 **`scripts/run_sonar.ps1`**，便于统一执行（见下节）。

### 3.3 与现有检查的关系

- **check_all.ps1**：负责 ESLint/Prettier/Stylelint/ruff 等**格式与基础规范**，建议保留，在 CI 中先跑。
- **collect_metrics.ps1**：产出**目录、行数、复杂度等指标**，供 AI 架构 Review 使用；与 SonarQube 的**可维护性/重复**等维度互补。
- **SonarQube**：提供**完整规则集、质量门禁、安全/可靠性/重复/覆盖率**等，适合作为「高标准」或 CI 门禁。三者可并存：先跑 check + metrics，再跑 Sonar（若已配置）。

---

## 四、推荐选择

| 场景 | 建议 |
|------|------|
| 暂无 SonarQube 服务、希望统一「检查话术」 | **参考标准**：在架构 Review 与文档中写明「与 SonarQube 质量模型对齐」，指标与策略照常使用。 |
| 已有或计划部署 SonarQube/SonarCloud | **直接使用**：在根目录或前后端分别配置 `sonar-project.properties`，用 `scripts/run_sonar.ps1`（见下）执行扫描，并在 CI 中可选接入。 |
| 两者都要 | 参考标准用于日常 AI Review 与策略；SonarQube 用于正式门禁与历史趋势。 |

---

## 五、参考链接

- [SonarQube 用户指南 - 概念与规则](https://docs.sonarsource.com/sonarqube/latest/user-guide/concepts/)
- [Code metrics](https://docs.sonarsource.com/sonarqube/latest/user-guide/code-metrics/)
- [SonarScanner CLI](https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/)
- [SonarCloud](https://sonarcloud.io/)（无需自建服务器）
