# 后端代码检查：语法 +（可选）ruff 规范与格式
# 用法：在项目根目录执行 .\scripts\check_backend.ps1
# 可选：pip install ruff 后会自动执行 ruff check 与 ruff format --check

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$BackendDir = Join-Path $ProjectRoot "src\backend"
$ReportsDir = Join-Path $ProjectRoot "reports"
if (-not (Test-Path $ReportsDir)) { New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null }
$BackendLog = Join-Path $ReportsDir "check-backend.log"
$logLines = @()

Set-Location $ProjectRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }

# 1) 语法检查
$logLines += "=== Backend: py_compile ==="
Write-Host "=== Backend: py_compile ===" -ForegroundColor Cyan
$pyFiles = Get-ChildItem -Path $BackendDir -Filter "*.py" -Recurse -File | Where-Object { $_.FullName -notmatch "\\__pycache__\\" }
$syntaxOk = $true
foreach ($f in $pyFiles) {
    $r = & $PythonExe -m py_compile $f.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        $logLines += "  FAIL: $($f.FullName)"; $r | ForEach-Object { $logLines += "    $_" }
        Write-Host "  FAIL: $($f.FullName)" -ForegroundColor Red
        $r | ForEach-Object { Write-Host "    $_" }
        $syntaxOk = $false
    }
}
if (-not $syntaxOk) {
    $logLines += "Syntax check failed"
    $logLines | Set-Content -Path $BackendLog -Encoding UTF8
    Write-Host "Syntax check failed" -ForegroundColor Red
    exit 1
}
$logLines += "  OK"; Write-Host "  OK" -ForegroundColor Green

# 2) ruff
$ruffCmd = Get-Command ruff -ErrorAction SilentlyContinue
if ($ruffCmd) {
    $logLines += "=== Backend: ruff check ==="
    Write-Host "=== Backend: ruff check ===" -ForegroundColor Cyan
    $ruffCheckOut = ruff check $BackendDir 2>&1
    $ruffCheckOut | ForEach-Object { $logLines += $_ }
    if ($LASTEXITCODE -ne 0) {
        $logLines | Set-Content -Path $BackendLog -Encoding UTF8
        Write-Host 'ruff check failed' -ForegroundColor Red
        exit 1
    }
    $logLines += "  OK"
    $logLines += "=== Backend: ruff format --check ==="
    Write-Host "  OK" -ForegroundColor Green
    Write-Host "=== Backend: ruff format check ===" -ForegroundColor Cyan
    $ruffFmtOut = ruff format --check $BackendDir 2>&1
    $ruffFmtOut | ForEach-Object { $logLines += $_ }
    if ($LASTEXITCODE -ne 0) {
        $logLines += "ruff format failed (run: ruff format src/backend)"
        $logLines | Set-Content -Path $BackendLog -Encoding UTF8
        Write-Host 'ruff format --check failed' -ForegroundColor Red
        exit 1
    }
    $logLines += "  OK"
    Write-Host "  OK" -ForegroundColor Green
} else {
    $logLines += "=== Skip ruff (not installed). pip install ruff ==="
    Write-Host "=== Skip ruff (not installed). pip install ruff ===" -ForegroundColor Yellow
}

$logLines | Set-Content -Path $BackendLog -Encoding UTF8
Write-Host "Backend check done" -ForegroundColor Green
exit 0
