# 依赖漏洞扫描：后端 pip audit + 前端 npm audit
# 在项目根目录执行：.\scripts\check_audit.ps1
# 报告输出到 reports/check-audit.log；可选 -Strict 或 $env:CHECK_AUDIT_STRICT=1 时发现漏洞则退出码 1

param(
    [switch]$Strict   # 发现 high/critical 或 audit 命令非零时退出码 1
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$reportDir = Join-Path $root "reports"
$logFile = Join-Path $reportDir "check-audit.log"

if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }

$lines = @()
$lines += "=== Check Audit $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
$backendFailed = $false
$frontendFailed = $false

# ---------- 后端 pip audit ----------
$lines += ""
$lines += "--- Backend (pip audit) ---"
Push-Location $root
try {
    $pipAudit = $null
    try {
        $pipAudit = pip audit 2>&1
    } catch {
        $pipAudit = "pip audit 未找到或执行失败。可安装: pip install pip-audit"
    }
    if ($pipAudit -is [System.Array]) { $lines += $pipAudit } else { $lines += $pipAudit.ToString() }
    if ($LASTEXITCODE -ne 0) { $backendFailed = $true }
} finally {
    Pop-Location
}

# ---------- 前端 npm audit ----------
$lines += ""
$lines += "--- Frontend (npm audit) ---"
$frontendDir = Join-Path $root "src\frontend"
if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    try {
        $npmAudit = npm audit 2>&1
        if ($npmAudit -is [System.Array]) { $lines += $npmAudit } else { $lines += $npmAudit.ToString() }
        if ($LASTEXITCODE -ne 0) { $frontendFailed = $true }
    } catch {
        $lines += "npm audit 执行异常: $_"
        $frontendFailed = $true
    } finally {
        Pop-Location
    }
} else {
    $lines += "src/frontend 不存在，跳过 npm audit"
}

$lines += ""
$lines += "--- End ---"
$text = $lines -join "`r`n"
$text | Set-Content -Path $logFile -Encoding UTF8
Write-Host "Audit log written to $logFile"

$doStrict = $Strict -or ($env:CHECK_AUDIT_STRICT -eq "1")
if ($doStrict -and ($backendFailed -or $frontendFailed)) {
    Write-Host "CHECK_AUDIT: 发现漏洞或 audit 失败，Strict 模式下退出码 1" -ForegroundColor Red
    exit 1
}
exit 0
