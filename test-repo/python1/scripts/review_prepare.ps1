# Review 准备：采集指标 + 生成 Review 清单，供人工或 AI 按清单做架构/业务 Review
# 用法：在项目根目录执行 .\scripts\review_prepare.ps1
# 输出：reports/metrics-*.json、reports/metrics-summary.md、reports/review-checklist.md

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$ReportsDir = Join-Path $ProjectRoot "reports"
if (-not (Test-Path $ReportsDir)) { New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null }

Set-Location $ProjectRoot

# 1) 采集指标
Write-Host "`n========== 1. 采集指标 ==========" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "collect_metrics.ps1")
if ($LASTEXITCODE -ne 0) { Write-Host "指标采集失败" -ForegroundColor Red; exit 1 }

# 2) 生成 Review 清单
$ChecklistPath = Join-Path $ReportsDir "review-checklist.md"
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$md = @"
# Review 清单

- **生成时间**：$time
- **用途**：按本清单执行架构 Review 与业务 Review，或交由 AI 使用对应技能完成。

## 已完成的准备

- [x] 已运行 \`scripts\collect_metrics.ps1\`
- [x] 指标文件已生成：\`reports/metrics-backend.json\`、\`reports/metrics-frontend.json\`

## 下一步（架构 Review）

1. 打开 \`docs/review-strategy.md\` 确认本期架构 Review 重点（可选）。
2. 对 AI 说：「请使用 **linkrag-architect-review** 做架构 Review」或「根据 reports 指标做架构师 Review」。
3. AI 会读取 \`reports/metrics-*.json\`、\`.cursor/review-memory.md\`、\`docs/review-strategy.md\` 后产出报告。

## 下一步（业务 Review）

1. 确认 \`docs/需求文档.md\`（或当前迭代需求文档）已更新。
2. 打开 \`docs/review-strategy.md\` 确认本期业务 Review 重点（可选）。
3. 对 AI 说：「请使用 **linkrag-business-review** 做业务 Review」或「根据需求文档做业务实现对照」。
4. AI 会读取需求文档、\`docs/业务实现检查标准.md\`、策略与记忆后产出报告。

## 相关文档

| 文档 | 说明 |
|------|------|
| docs/review-strategy.md | 架构/业务 Review 策略与权重 |
| docs/业务实现检查标准.md | 业务实现衡量维度 |
| .cursor/review-memory.md | 历史 Review 结论与待跟进（由 AI 写入） |
| docs/代码检查.md | 检查脚本与专家 Review 说明 |
"@
$md | Set-Content -Path $ChecklistPath -Encoding UTF8
Write-Host "`n========== 2. Review 清单已生成 ==========" -ForegroundColor Cyan
Write-Host "  $ChecklistPath" -ForegroundColor Green
Write-Host "`n请对 AI 说：「使用 linkrag-architect-review 做架构 Review」或「使用 linkrag-business-review 做业务 Review」" -ForegroundColor Cyan
exit 0
