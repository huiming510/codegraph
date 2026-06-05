# Run backend + frontend tests. From project root: .\scripts\run_tests.ps1
# Requires: pip install pytest pytest-asyncio httpx; cd src/frontend && npm install
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptDir
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
Set-Location $ProjectRoot

$backendFailed = $false
$frontendFailed = $false

Write-Host "`n========== Backend (pytest) ==========" -ForegroundColor Cyan
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
try {
    python -m pytest (Join-Path $ProjectRoot "src\backend\tests") -v --tb=short 2>&1
    if ($LASTEXITCODE -ne 0) { $backendFailed = $true }
}
catch {
    Write-Host "Backend failed. Install: pip install pytest pytest-asyncio httpx" -ForegroundColor Yellow
    $backendFailed = $true
}

Write-Host "`n========== Frontend (vitest) ==========" -ForegroundColor Cyan
$frontendDir = Join-Path $ProjectRoot "src\frontend"
$hasFrontend = Test-Path (Join-Path $frontendDir "package.json")
if ($hasFrontend) {
    Push-Location $frontendDir
    try {
        npm run test:run 2>&1
        if ($LASTEXITCODE -ne 0) { $frontendFailed = $true }
    }
    catch {
        Write-Host "Frontend failed. Run: cd src/frontend && npm install" -ForegroundColor Yellow
        $frontendFailed = $true
    }
    Pop-Location
}
else {
    Write-Host "src/frontend not found, skip frontend" -ForegroundColor Gray
}

Write-Host "`n========== Summary ==========" -ForegroundColor Cyan
if ($backendFailed) { Write-Host "  Backend: FAIL" -ForegroundColor Red } else { Write-Host "  Backend: OK" -ForegroundColor Green }
if ($frontendFailed) { Write-Host "  Frontend: FAIL" -ForegroundColor Red } else { Write-Host "  Frontend: OK" -ForegroundColor Green }
if ($backendFailed -or $frontendFailed) { Write-Host "`nSome tests failed" -ForegroundColor Red; exit 1 }
exit 0
