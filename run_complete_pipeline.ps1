#!/usr/bin/env pwsh
# Complete pipeline runner for testing backend with agents

param(
    [ValidateSet('setup', 'python', 'maven', 'all')]
    [string]$Phase = 'all',
    [string]$Service = ''
)

# Colors
function Write-Success { Write-Host @args -ForegroundColor Green }
function Write-Info { Write-Host @args -ForegroundColor Cyan }
function Write-Warning { Write-Host @args -ForegroundColor Yellow }
function Write-CustomError { Write-Host @args -ForegroundColor Red }

$projectRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

Write-Success "================================"
Write-Success "  COMPLETE TEST PIPELINE"
Write-Success "================================"

# PHASE 1: SETUP
function Run-Setup {
    Write-Success "`n[1/4] SETUP"
    Push-Location $projectRoot
    
    Write-Info "Activating environment..."
    if (Test-Path ".\.venv\Scripts\Activate.ps1") {
        & ".\.venv\Scripts\Activate.ps1"
        Write-Success "OK"
    }
    
    Write-Info "Installing dependencies..."
    pip install -r requirements.txt -q 2>&1 | Out-Null
    Write-Success "OK"
    Pop-Location
}

# PHASE 2: PYTHON
function Run-Python {
    Write-Success "`n[2/4] PYTHON AGENTS"
    Push-Location $projectRoot
    
    Write-Info "Running agents..."
    if ($Service) {
        python run_pipeline.py --services $Service
    } else {
        python run_pipeline.py
    }
    Write-Success "OK"
    Pop-Location
}

# PHASE 3: MAVEN
function Run-Maven {
    Write-Success "`n[3/4] MAVEN TESTS"
    Push-Location "$projectRoot\output\tests"
    
    Write-Info "Running tests..."
    if ($Service) {
        mvn clean test jacoco:report -Dtest="*$($Service)*"
    } else {
        mvn clean test jacoco:report
    }
    Write-Success "OK"
    Pop-Location
}

# PHASE 4: RESULTS
function Run-Results {
    Write-Success "`n[4/4] RESULTS"
    Push-Location $projectRoot
    
    Write-Success "`nPIPELINE COMPLETE!"
    Write-Info "`nOutputs:"
    Write-Info "  - Features: output/features/"
    Write-Info "  - Reports: output/reports/"
    Write-Info "  - Tests: output/tests/target/"
    Write-Info "  - Coverage: output/tests/target/site/jacoco/index.html"
    
    Pop-Location
}

# MAIN
$start = Get-Date

try {
    switch ($Phase) {
        'setup' { Run-Setup }
        'python' { Run-Setup; Run-Python }
        'maven' { Run-Setup; Run-Maven }
        'all' { Run-Setup; Run-Python; Run-Maven; Run-Results }
    }
    
    $duration = (Get-Date) - $start
    Write-Success "`nTime: $($duration.TotalMinutes.ToString('F1')) min"
}
catch {
    Write-CustomError "ERROR: $_"
    exit 1
}
