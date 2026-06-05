# 前后端 API 路径 diff：生成 reports/api-path-diff.md
# 在项目根目录执行：.\scripts\collect_api_diff.ps1
# 可由 review_prepare.ps1 或 CI 可选调用

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$script = Join-Path $root "scripts\metrics\api_path_diff.py"

if (-not (Test-Path $script)) {
    Write-Error "Not found: $script"
    exit 1
}
& python $script
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
