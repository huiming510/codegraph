# Execute tests and generate graphic+text report. From project root: .\scripts\generate_test_report.ps1
$scriptDir = Split-Path -Parent $PSCommandPath
Set-Location (Split-Path -Parent $scriptDir)
python (Join-Path $scriptDir "generate_test_report.py")
exit $LASTEXITCODE
