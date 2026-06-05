# 提交前/MR 前全量门禁：先代码检查，再测试；全部通过才退出 0
# 用法：在项目根目录执行 .\scripts\run_full_check.ps1
# 等同于：check_all.ps1 + run_tests.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptDir
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }

Set-Location $ProjectRoot

$checkFailed = $false
$testFailed = $false

Write-Host "`n========== 阶段 1：代码检查 ==========" -ForegroundColor Cyan
& (Join-Path $ScriptDir "check_all.ps1")
if ($LASTEXITCODE -ne 0) { $checkFailed = $true }

Write-Host "`n========== 阶段 2：测试 ==========" -ForegroundColor Cyan
& (Join-Path $ScriptDir "run_tests.ps1")
if ($LASTEXITCODE -ne 0) { $testFailed = $true }

Write-Host "`n========== 全量门禁汇总 ==========" -ForegroundColor Cyan
if ($checkFailed) { Write-Host "  代码检查: 未通过" -ForegroundColor Red } else { Write-Host "  代码检查: 通过" -ForegroundColor Green }
if ($testFailed) { Write-Host "  测试: 未通过" -ForegroundColor Red } else { Write-Host "  测试: 通过" -ForegroundColor Green }

if ($checkFailed -or $testFailed) {
    Write-Host "`n未通过全量门禁，请先修复后再提交/MR。" -ForegroundColor Red
    exit 1
}
Write-Host "`n全量门禁通过。" -ForegroundColor Green
exit 0
