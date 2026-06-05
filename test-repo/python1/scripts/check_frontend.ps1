# 前端代码检查：ESLint + Stylelint + Prettier
# 用法：在项目根目录执行 .\scripts\check_frontend.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$FrontendDir = Join-Path $ProjectRoot "src\frontend"
$ReportsDir = Join-Path $ProjectRoot "reports"
if (-not (Test-Path $ReportsDir)) { New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null }
$FrontendLog = Join-Path $ReportsDir "check-frontend.log"

Set-Location $FrontendDir

Write-Host "=== Frontend: npm run check ===" -ForegroundColor Cyan
$out = npm.cmd run check 2>&1
$out | Tee-Object -FilePath $FrontendLog
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend check failed. Try: npm.cmd run check:fix" -ForegroundColor Red
    exit 1
}
Write-Host "Frontend check done" -ForegroundColor Green
exit 0
