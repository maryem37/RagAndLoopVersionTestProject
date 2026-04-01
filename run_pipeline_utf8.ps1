# run_pipeline_utf8.ps1
# ──────────────────────
# PowerShell wrapper for the test automation pipeline on Windows
# Configures console encoding to UTF-8 before running Python
#
# Usage:
#   .\run_pipeline_utf8.ps1                  # Run all services
#   .\run_pipeline_utf8.ps1 -Services auth   # Run specific service
#   .\run_pipeline_utf8.ps1 -Services "auth,leave"

param(
    [string]$Services = $null,
    [switch]$List = $false,
    [switch]$Order = $false
)

# Step 1: Configure UTF-8 encoding for the console
Write-Host "[INFO] Configuring console for UTF-8 output..." -ForegroundColor Cyan
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Step 2: Build the Python command
$pythonCmd = "python run_pipeline_windows.py"

if ($List) {
    $pythonCmd += " --list"
}
elseif ($Order) {
    $pythonCmd += " --order"
}
elseif ($Services) {
    $pythonCmd += " --services $Services"
}

# Step 3: Run the pipeline
Write-Host "[INFO] Running: $pythonCmd" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Gray
Invoke-Expression $pythonCmd
$exitCode = $LASTEXITCODE

Write-Host "=" * 80 -ForegroundColor Gray
if ($exitCode -eq 0) {
    Write-Host "[SUCCESS] Pipeline completed successfully!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Pipeline failed with exit code $exitCode" -ForegroundColor Red
}

exit $exitCode
