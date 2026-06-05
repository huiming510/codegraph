---
name: test-report-with-screenshots
description: Runs backend/frontend/e2e tests, collects E2E screenshots, and generates a graphic+text test report (图文测试报告) in reports/test-report-with-screenshots.md. Use when the user asks for a test report, 测试报告, 图文报告, or screenshots of test results.
---

# 图文测试报告

生成包含截图与文字汇总的测试报告，便于归档或分享。

## 执行流程

1. **运行测试**（项目根目录）：
   ```powershell
   .\scripts\generate_test_report.ps1
   ```
   该脚本会依次执行：后端 pytest、前端 Vitest、Playwright E2E，并生成 `reports/test-report-with-screenshots.md`。

2. **若脚本不存在**，则手动执行：
   - 后端：`$env:PYTHONPATH=".\src"; pytest src/backend/tests -v --tb=line 2>&1 | Out-File reports/backend-test.log`
   - 前端单元：`cd src/frontend; npm run test:run 2>&1 | Out-File ../reports/frontend-unit.log`
   - E2E：`cd src/frontend; npx playwright test 2>&1 | Out-File ../reports/frontend-e2e.log`
   - 然后读取 `reports/test-report.md`、`src/frontend/test-results/screenshots/` 下的截图，按下方模板生成报告。

## 报告模板

生成的 `reports/test-report-with-screenshots.md` 应包含：

```markdown
# 图文测试报告

**生成时间**：{当前时间}

## 一、汇总

| 维度 | 通过 | 失败 | 合计 | 状态 |
|------|------|------|------|------|
| 后端 pytest | - | - | - | - |
| 前端 Vitest | - | - | - | - |
| 前端 E2E | - | - | - | - |

## 二、E2E 截图

### 登录页（成功时保存）

![登录页](screenshots/login-page.png)

（若存在失败用例的截图，在此列出：）

### 失败用例截图（如有）

![用例名](screenshots/xxx.png)

## 三、详细结果

（从 backend-test.log、frontend-unit.log、frontend-e2e.log 提取关键通过/失败信息）
```

## 截图路径

- **成功截图**：`src/frontend/test-results/screenshots/login-page.png`（E2E 用例「登录页截图」产出）
- **失败截图**：`src/frontend/test-results/login-xxx-chromium/test-failed-1.png`

生成报告时，将截图**复制到** `reports/screenshots/`，以便报告中的相对路径 `screenshots/xxx.png` 正确显示。

## 输出

- **报告文件**：`reports/test-report-with-screenshots.md`
- **截图目录**：`reports/screenshots/`（已复制，便于报告内引用）

## 触发场景

当用户说「测试报告」「图文报告」「带截图的测试报告」「生成测试报告」时，执行本技能。
