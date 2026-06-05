# 采集前后端指标，供 AI 专家 Review 使用。脚本出指标，AI 根据指标出报告。
# 用法：在项目根目录执行 .\scripts\collect_metrics.ps1
# 输出：reports/metrics-backend.json, reports/metrics-frontend.json, reports/metrics-summary.md

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$ReportsDir = Join-Path $ProjectRoot "reports"
$MetricsDir = Join-Path $PSScriptRoot "metrics"
if (-not (Test-Path $ReportsDir)) { New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null }

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }

Write-Host "=== Collect metrics for review ===" -ForegroundColor Cyan
Set-Location $ProjectRoot

# Backend
$BackendJson = Join-Path $ReportsDir "metrics-backend.json"
& $PythonExe (Join-Path $MetricsDir "backend_metrics.py") 2>&1 | Set-Content -Path $BackendJson -Encoding UTF8
if ($LASTEXITCODE -ne 0) { Write-Host "Backend metrics failed" -ForegroundColor Red; exit 1 }
Write-Host "  Backend: $BackendJson" -ForegroundColor Green

# Frontend
$FrontendJson = Join-Path $ReportsDir "metrics-frontend.json"
& $PythonExe (Join-Path $MetricsDir "frontend_metrics.py") 2>&1 | Set-Content -Path $FrontendJson -Encoding UTF8
if ($LASTEXITCODE -ne 0) { Write-Host "Frontend metrics failed" -ForegroundColor Red; exit 1 }
Write-Host "  Frontend: $FrontendJson" -ForegroundColor Green

# Summary (human-readable stub for AI)
$SummaryMd = Join-Path $ReportsDir "metrics-summary.md"
@"
# 指标采集摘要

本文件由 \`scripts\collect_metrics.ps1\` 触发后由 AI 或脚本补充。详细数据见：

- **后端指标**：reports/metrics-backend.json（目录结构、文件行数、超 400 行文件、router 列表）
- **前端指标**：reports/metrics-frontend.json（目录结构、文件行数、api 路径、views 列表）

AI 进行架构/业务 Review 时，应**先读取上述 JSON 指标**，再结合 \`docs/开发框架说明.md\`、\`.cursor/review-memory.md\`、\`docs/review-strategy.md\` 产出报告。

生成时间占位：请运行 collect_metrics 后由 AI 填入或忽略。
"@ | Set-Content -Path $SummaryMd -Encoding UTF8
Write-Host "  Summary: $SummaryMd" -ForegroundColor Green
Write-Host "Done. AI review should read metrics JSON + memory + strategy, then produce report." -ForegroundColor Cyan
exit 0
