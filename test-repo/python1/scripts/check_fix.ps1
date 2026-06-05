# 一键修复可自动修复的规范与格式（不代替 check，修复后建议再跑 check_all）
# 用法：在项目根目录执行 .\scripts\check_fix.ps1
# 后端：ruff format + ruff check --fix；前端：npm run check:fix

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$BackendDir = Join-Path $ProjectRoot "src\backend"
$FrontendDir = Join-Path $ProjectRoot "src\frontend"

Set-Location $ProjectRoot

Write-Host "`n========== 后端自动修复 (ruff) ==========" -ForegroundColor Cyan
$ruff = Get-Command ruff -ErrorAction SilentlyContinue
if ($ruff) {
    ruff format $BackendDir
    ruff check $BackendDir --fix
    Write-Host "  后端 ruff 修复完成" -ForegroundColor Green
} else {
    Write-Host "  未安装 ruff，跳过。安装: pip install ruff" -ForegroundColor Yellow
}

Write-Host "`n========== 前端自动修复 (npm run check:fix) ==========" -ForegroundColor Cyan
if (Test-Path (Join-Path $FrontendDir "package.json")) {
    Push-Location $FrontendDir
    npm run check:fix 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Host "  前端 check:fix 未完全通过，请查看上方输出" -ForegroundColor Yellow } else { Write-Host "  前端修复完成" -ForegroundColor Green }
    Pop-Location
} else {
    Write-Host "  未找到 src/frontend，跳过前端" -ForegroundColor Gray
}

Write-Host "`n建议再执行: .\scripts\check_all.ps1" -ForegroundColor Cyan
exit 0
