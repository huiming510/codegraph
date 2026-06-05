# 使用 SonarScanner 执行 SonarQube 扫描（可选）
# 前置：已配置 sonar-project.properties 中的 sonar.host.url、sonar.login
# 前置：已安装 SonarScanner CLI 并加入 PATH，或使用 npx sonar-scanner（前端）
# 详见：docs/SonarQube与检查标准.md

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
Set-Location $ProjectRoot

if (-not (Test-Path "sonar-project.properties")) {
    Write-Error "未找到 sonar-project.properties，请在项目根目录配置。"
    exit 1
}

$scanner = Get-Command sonar-scanner -ErrorAction SilentlyContinue
if (-not $scanner) {
    Write-Host "未在 PATH 中找到 sonar-scanner。请安装 SonarScanner CLI 或使用 npx sonar-scanner。"
    Write-Host "参见: https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/"
    exit 1
}

& sonar-scanner
exit $LASTEXITCODE
