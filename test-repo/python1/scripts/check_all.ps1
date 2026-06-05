# 一键执行后端 + 前端代码检查，并生成汇总报告 reports/check-report.md
# 用法：在项目根目录执行 .\scripts\check_all.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptDir
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$ReportsDir = Join-Path $ProjectRoot "reports"
$ReportMd = Join-Path $ReportsDir "check-report.md"
if (-not (Test-Path $ReportsDir)) { New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null }

Set-Location $ProjectRoot

$backendFailed = $false
$frontendFailed = $false

Write-Host "`n========== 后端检查 ==========" -ForegroundColor Cyan
& (Join-Path $ScriptDir "check_backend.ps1")
if ($LASTEXITCODE -ne 0) { $backendFailed = $true }

Write-Host "`n========== 前端检查 ==========" -ForegroundColor Cyan
& (Join-Path $ScriptDir "check_frontend.ps1")
if ($LASTEXITCODE -ne 0) { $frontendFailed = $true }

# 生成汇总报告
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$backendStatus = if ($backendFailed) { "FAIL" } else { "OK" }
$frontendStatus = if ($frontendFailed) { "FAIL" } else { "OK" }
$overall = if ($backendFailed -or $frontendFailed) { "部分未通过" } else { "全部通过" }

$backendSnippet = ""
if ($backendFailed) {
    $logPath = Join-Path $ReportsDir "check-backend.log"
    if (Test-Path $logPath) {
        $backendSnippet = "### 最近输出`n" + "``````" + "`n" + (Get-Content $logPath -Tail 50 -Encoding UTF8 -ErrorAction SilentlyContinue | Out-String) + "`n" + "``````" + "`n"
    }
}
$frontendSnippet = ""
if ($frontendFailed) {
    $logPath = Join-Path $ReportsDir "check-frontend.log"
    if (Test-Path $logPath) {
        $frontendSnippet = "### 最近输出`n" + "``````" + "`n" + (Get-Content $logPath -Tail 80 -Encoding UTF8 -ErrorAction SilentlyContinue | Out-String) + "`n" + "``````" + "`n"
    }
}
$suggestBackend = if ($backendFailed) { "- **后端**: 若为 ruff 规范/格式问题，可执行: ruff format src/backend ; ruff check src/backend --fix. 若为语法错误，请按 check-backend.log 中的文件与行号修改.`n" } else { "" }
$suggestFrontend = if ($frontendFailed) { "- **前端**: 可尝试自动修复: cd src/frontend ; npm.cmd run check:fix . 再运行 scripts/check_frontend.ps1 或 check_all.ps1 验证.`n" } else { "" }

$md = @"
# 代码检查报告

- **生成时间**: $time
- **汇总**: $overall

## 后端 (src/backend)

- **状态**: $backendStatus
- **详情**: 见 [reports/check-backend.log](check-backend.log)

$backendSnippet
## 前端 (src/frontend)

- **状态**: $frontendStatus
- **详情**: 见 [reports/check-frontend.log](check-frontend.log)

$frontendSnippet
## 处理建议

$suggestBackend$suggestFrontend
"@

$md | Set-Content -Path $ReportMd -Encoding UTF8

Write-Host "`n========== 汇总 ==========" -ForegroundColor Cyan
if ($backendFailed) { Write-Host "  后端: 未通过" -ForegroundColor Red } else { Write-Host "  后端: 通过" -ForegroundColor Green }
if ($frontendFailed) { Write-Host "  前端: 未通过" -ForegroundColor Red } else { Write-Host "  前端: 通过" -ForegroundColor Green }
Write-Host "`n报告已写入: $ReportMd" -ForegroundColor Cyan

if ($backendFailed -or $frontendFailed) {
    Write-Host "`n部分检查未通过" -ForegroundColor Red
    exit 1
}
Write-Host "`n全部检查通过" -ForegroundColor Green
exit 0
