#!/usr/bin/env pwsh
# Complete pipeline runner for testing backend with agents

param(
    [ValidateSet('setup', 'python', 'maven', 'all')]
    [string]$Phase = 'all',
    [string]$Service = ''

    ,
    [switch]$OptionBRealServices = $false,

    # If enabled, build the local RAG index (extract + ingest) and inject
    # retrieved context into the Gherkin generator prompt.
    [switch]$EnableRag = $false,

    # By default, the Python agent pipeline already runs Maven (via test_executor).
    # Use this switch only if you explicitly want a second Maven run after agents.
    [switch]$RunMavenAfterAgents = $false,

    # Relax quality gates so the workflow can complete while debugging backend auth (403) issues.
    # Sets: ALLOW_TEST_FAILURES=1, MIN_TEST_PASS_RATE=0, MAX_TEST_FAILED_SCENARIOS=999999,
    # and disables failing the workflow on coverage quality gate.
    [switch]$RelaxQualityGates = $false,

    # Skip phase 1 setup (venv activation + pip install). Useful when iterating quickly.
    [switch]$NoSetup = $false,

    # Skip test execution during the Python agent workflow (skips test_executor + coverage_analyst).
    # Use this when backend services are not running and you only want to generate features/tests.
    [switch]$SkipTestExecution = $false,

    # Skip service port health check warnings in Maven phase.
    [switch]$NoHealthCheck = $false,

    # If set, do not fail the script when the Python pipeline returns a non-zero exit code.
    [switch]$IgnorePythonFailures = $false
)

# Colors
function Write-Success { Write-Host @args -ForegroundColor Green }
function Write-Info { Write-Host @args -ForegroundColor Cyan }
function Write-Warning { Write-Host @args -ForegroundColor Yellow }
function Write-CustomError { Write-Host @args -ForegroundColor Red }

$projectRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

function Get-VenvActivateScript {
    # If we're already in a venv, prefer it.
    if ($env:VIRTUAL_ENV) {
        $candidate = Join-Path $env:VIRTUAL_ENV "Scripts\Activate.ps1"
        if (Test-Path $candidate) { return $candidate }
    }

    # Prefer newer venvs if present.
    $venvDirs = @(".venv312", ".venv311", ".venv")
    foreach ($dir in $venvDirs) {
        $candidate = Join-Path $projectRoot (Join-Path $dir "Scripts\Activate.ps1")
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Test-ServiceHealth {
    param(
        [int[]]$Ports = @(9000, 9001),
        [int]$TimeoutSec = 2
    )

    $allOk = $true
    foreach ($p in $Ports) {
        try {
            $ok = Test-NetConnection -ComputerName '127.0.0.1' -Port $p -InformationLevel Quiet
            if (-not $ok) {
                Write-Warning "Port $p is not listening"
                $allOk = $false
            }
        } catch {
            Write-Warning "Health check failed for port $($p): $_"
            $allOk = $false
        }
    }
    return $allOk
}

function Assert-SurefirePassed {
    param(
        [string]$SurefireDir
    )

    if (-not (Test-Path $SurefireDir)) {
        Write-Warning "Surefire reports not found at: $SurefireDir"
        return
    }

    $pattern = 'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)' 
    $matches = Select-String -Path (Join-Path $SurefireDir '*.txt') -Pattern $pattern -ErrorAction SilentlyContinue

    if (-not $matches) {
        Write-Warning "Could not find test summary lines in $SurefireDir"
        return
    }

    $totalFailures = 0
    $totalErrors = 0
    foreach ($m in $matches) {
        if ($m.Matches.Count -gt 0) {
            $failures = [int]$m.Matches[0].Groups[2].Value
            $errors = [int]$m.Matches[0].Groups[3].Value
            $totalFailures += $failures
            $totalErrors += $errors
        }
    }

    if ($totalFailures -gt 0 -or $totalErrors -gt 0) {
        throw "Maven tests reported Failures=$totalFailures Errors=$totalErrors (see output/tests/target/surefire-reports)."
    }
}

Write-Success "================================"
Write-Success "  COMPLETE TEST PIPELINE"
Write-Success "================================"

# PHASE 1: SETUP
function Run-Setup {
    Write-Success "`n[1/4] SETUP"
    Push-Location $projectRoot
    
    Write-Info "Activating environment..."
    $activateScript = Get-VenvActivateScript
    if ($activateScript) {
        & $activateScript
        Write-Success "OK ($activateScript)"
    } else {
        Write-Warning "No venv activation script found; continuing with system Python"
    }
    
    Write-Info "Installing dependencies..."
    python -m pip install -r requirements.txt -q 2>&1 | Out-Null
    Write-Success "OK"
    Pop-Location
}

# PHASE 2: PYTHON
function Run-Python {
    Write-Success "`n[2/4] PYTHON AGENTS"
    Push-Location $projectRoot

    if ($RelaxQualityGates) {
        Write-Warning "Relaxing quality gates for debug (ALLOW_TEST_FAILURES=1, MIN_TEST_PASS_RATE=0, FAIL_ON_COVERAGE_QG=0)"
        $env:ALLOW_TEST_FAILURES = "1"
        $env:MIN_TEST_PASS_RATE = "0"
        $env:MAX_TEST_FAILED_SCENARIOS = "999999"
        $env:FAIL_ON_COVERAGE_QG = "0"
    }

    if ($EnableRag) {
        Write-Info "RAG enabled: generating CSV + building Chroma index..."

        # Enable prompt-level RAG injection for the agent.
        $env:RAG_ENABLE = "1"

        python main.py extract-e2egit
        if ($LASTEXITCODE -ne 0) { throw "extract-e2egit failed with exit code $LASTEXITCODE" }

        python main.py ingest
        if ($LASTEXITCODE -ne 0) { throw "ingest failed with exit code $LASTEXITCODE" }

        Write-Success "RAG index ready (chroma_db/)"
    }

    if ($SkipTestExecution) {
        Write-Warning "SkipTestExecution is set: skipping test execution in the workflow (SKIP_TEST_EXECUTION=1)"
        $env:SKIP_TEST_EXECUTION = "1"
    } else {
        Remove-Item Env:SKIP_TEST_EXECUTION -ErrorAction SilentlyContinue | Out-Null
    }
    
    Write-Info "Running agents..."
    if ($Service) {
        python run_pipeline.py --services $Service
    } else {
        python run_pipeline.py
    }

    if ($LASTEXITCODE -ne 0 -and -not $IgnorePythonFailures) {
        throw "Python pipeline failed with exit code $LASTEXITCODE"
    }
    Write-Success "OK"
    Pop-Location
}

# PHASE 3: MAVEN
function Run-Maven {
    Write-Success "`n[3/4] MAVEN TESTS"

    if ($OptionBRealServices) {
        Write-Info "Option B enabled: running real-services coverage flow (start services + E2E + merge/report)..."
        Push-Location $projectRoot
        try {
            $script = Join-Path $projectRoot 'run_real_coverage.ps1'
            if (-not (Test-Path $script)) {
                throw "Missing script: $script"
            }
            powershell -ExecutionPolicy Bypass -File $script
            if ($LASTEXITCODE -ne 0) {
                throw "run_real_coverage.ps1 failed with exit code $LASTEXITCODE"
            }

            Write-Info "Updating Option B markdown report..."
            python .\run_option_b_coverage_agent.py
            if ($LASTEXITCODE -ne 0) {
                throw "run_option_b_coverage_agent.py failed with exit code $LASTEXITCODE"
            }
        } finally {
            Pop-Location
        }

        Write-Success "OK"
        return
    }

    # Default (non-Option B): run Maven tests. These tests often require services to be up.
    if (-not $NoHealthCheck -and -not (Test-ServiceHealth)) {
        Write-Warning "Backend services do not look reachable on ports 9000/9001. Maven E2E tests may fail with 'Connection refused'."
        Write-Warning "If you want the script to start real services + generate JaCoCo HTML, re-run with: .\\run_complete_pipeline.ps1 -OptionBRealServices"
    }

    Push-Location "$projectRoot\output\tests"
    try {
        Write-Info "Running tests..."
        if ($Service) {
            mvn clean test -Dtest="*$($Service)*"
        } else {
            mvn clean test
        }

        # Because pom.xml has testFailureIgnore=true, Maven can still exit 0.
        if (-not $RelaxQualityGates) {
            Assert-SurefirePassed -SurefireDir (Join-Path (Get-Location) 'target\surefire-reports')
        } else {
            Write-Warning "RelaxQualityGates is set: skipping strict Surefire failure check"
        }
    } finally {
        Pop-Location
    }

    Write-Success "OK"
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
        'setup' {
            if (-not $NoSetup) { Run-Setup }
        }
        'python' {
            if (-not $NoSetup) { Run-Setup }
            Run-Python
        }
        'maven' {
            if (-not $NoSetup) { Run-Setup }
            Run-Maven
        }
        'all' {
            if (-not $NoSetup) { Run-Setup }
            Run-Python

            # The Python agent pipeline already runs Maven as part of test_executor.
            # Run this phase only if explicitly requested or when Option B flow is enabled.
            if ($OptionBRealServices -or $RunMavenAfterAgents) {
                Run-Maven
            }

            Run-Results
        }
    }
    
    $duration = (Get-Date) - $start
    Write-Success "`nTime: $($duration.TotalMinutes.ToString('F1')) min"
}
catch {
    Write-CustomError "ERROR: $_"
    exit 1
}
