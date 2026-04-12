<#
One-command: start both microservices with JaCoCo tcpserver, run the consolidated pipeline,
dump exec data, and generate fresh jacoco.xml/html.

Auth service (Swagger has /api/auth/login) : http://127.0.0.1:9000
Leave service (Swagger has /api/leave-*)  : http://127.0.0.1:9001

Usage:
  powershell -ExecutionPolicy Bypass -File .\run_real_coverage.ps1
  $env:MIN_TEST_PASS_RATE='50'; powershell -ExecutionPolicy Bypass -File .\run_real_coverage.ps1
    # Coverage quality gate controls:
    #   $env:MIN_BRANCH_COVERAGE='2.5'            # override branch threshold
    #   $env:ALLOW_COVERAGE_QG_FAILURE='1'        # don't fail the pipeline on QG
    #   $env:FAIL_ON_COVERAGE_QG='0'              # same as above
#>

$ErrorActionPreference = 'Stop'

$PROJECT_DIR  = $PSScriptRoot
$OUTPUT_DIR   = Join-Path $PROJECT_DIR 'output'
$COVERAGE_DIR = Join-Path $OUTPUT_DIR 'jacoco'
$LOG_DIR      = Join-Path $COVERAGE_DIR 'logs'

$AGENT_JAR = Join-Path $PROJECT_DIR 'jacocoagent.jar'
$CLI_JAR   = Join-Path $PROJECT_DIR 'jacococli.jar'


$AUTH_JAR  = if ($env:AUTH_JAR  -and $env:AUTH_JAR.Trim())  { $env:AUTH_JAR.Trim() }  else { 'C:\Bureau\Bureau\microservices\conge\target\congee-0.0.1-SNAPSHOT.jar' }
$LEAVE_JAR = if ($env:LEAVE_JAR -and $env:LEAVE_JAR.Trim()) { $env:LEAVE_JAR.Trim() } else { 'C:\Bureau\Bureau\microservices\DemandeConge\target\DemandeConge-0.0.1-SNAPSHOT.jar' }

$AUTH_CLASSES  = if ($env:AUTH_CLASSES  -and $env:AUTH_CLASSES.Trim())  { $env:AUTH_CLASSES.Trim() }  else { 'C:\Bureau\Bureau\microservices\conge\target\classes' }
$LEAVE_CLASSES = if ($env:LEAVE_CLASSES -and $env:LEAVE_CLASSES.Trim()) { $env:LEAVE_CLASSES.Trim() } else { 'C:\Bureau\Bureau\microservices\DemandeConge\target\classes' }

$JACOCO_INCLUDES = if ($env:JACOCO_INCLUDES -and $env:JACOCO_INCLUDES.Trim()) { $env:JACOCO_INCLUDES.Trim() } else { 'tn.enis.*' }

New-Item -ItemType Directory -Force -Path $COVERAGE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

if (-not (Test-Path $AGENT_JAR)) { throw "JaCoCo agent not found: $AGENT_JAR" }
if (-not (Test-Path $CLI_JAR)) { throw "jacococli.jar not found: $CLI_JAR" }
if (-not (Test-Path $AUTH_JAR)) { throw "Auth service jar not found: $AUTH_JAR" }
if (-not (Test-Path $LEAVE_JAR)) { throw "Leave service jar not found: $LEAVE_JAR" }
if (-not (Test-Path $AUTH_CLASSES)) { throw "Auth target/classes not found: $AUTH_CLASSES" }
if (-not (Test-Path $LEAVE_CLASSES)) { throw "Leave target/classes not found: $LEAVE_CLASSES" }

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    return $port
}

function Wait-ForPort {
    param(
        [Parameter(Mandatory=$true)][int]$Port,
        [Parameter(Mandatory=$true)][int]$TimeoutSeconds,
        [string]$Name = 'service'
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $ok = $false
        try {
            $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
        } catch {}
        if ($ok) {
            Write-Host "  $Name is listening on :$Port" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "  ERROR: $Name did not open port :$Port within ${TimeoutSeconds}s" -ForegroundColor Red
    return $false
}

function Stop-PortOwner {
    param([Parameter(Mandatory=$true)][int]$Port)

    $processIds = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($conns) {
            $processIds += ($conns | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue)
        }
    } catch {}

    if (-not $processIds -or $processIds.Count -eq 0) {
        try {
            $lines = (netstat -ano 2>$null | Select-String ":$Port")
            foreach ($line in $lines) {
                $parts = ($line.Line -split "\s+" | Where-Object { $_ })
                if ($parts.Count -ge 5) {
                    $netstatPid = $parts[-1]
                    if ($netstatPid -match '^\d+$') { $processIds += [int]$netstatPid }
                }
            }
        } catch {}
    }

    $processIds = $processIds | Where-Object { $_ -and ($_ -match '^\d+$') } | Select-Object -Unique
    foreach ($processId in $processIds) {
        try {
            Write-Host "  Freeing port $Port (PID $processId)" -ForegroundColor Yellow
            taskkill /PID $processId /F 2>$null | Out-Null
        } catch {}
    }
}

$AUTH_JACOCO_PORT  = Get-FreeTcpPort
$LEAVE_JACOCO_PORT = Get-FreeTcpPort
while ($LEAVE_JACOCO_PORT -eq $AUTH_JACOCO_PORT) { $LEAVE_JACOCO_PORT = Get-FreeTcpPort }
Write-Host "Using JaCoCo tcpserver ports: auth=$AUTH_JACOCO_PORT leave=$LEAVE_JACOCO_PORT" -ForegroundColor DarkCyan

$env:JACOCO_PORT_AUTH  = "$AUTH_JACOCO_PORT"
$env:JACOCO_PORT_LEAVE = "$LEAVE_JACOCO_PORT"

Write-Host "[1/5] Stopping existing services (ports 9000/9001)..." -ForegroundColor Cyan
Stop-PortOwner -Port 9000
Stop-PortOwner -Port 9001

# Also free the JaCoCo ports we plan to use (rare race, but avoids silent bind failures).
Stop-PortOwner -Port $AUTH_JACOCO_PORT
Stop-PortOwner -Port $LEAVE_JACOCO_PORT
Start-Sleep -Seconds 2

foreach ($p in @(9000,9001)) {
    $stillOpen = $false
    try { $stillOpen = Test-NetConnection -ComputerName 127.0.0.1 -Port $p -InformationLevel Quiet -WarningAction SilentlyContinue } catch {}
    if ($stillOpen) { throw "Port $p is still in use. Close the owning process and rerun." }
}

Write-Host "[2/5] Starting services with JaCoCo agent..." -ForegroundColor Cyan

$authOut  = Join-Path $LOG_DIR 'auth.out.log'
$authErr  = Join-Path $LOG_DIR 'auth.err.log'
$leaveOut = Join-Path $LOG_DIR 'leave.out.log'
$leaveErr = Join-Path $LOG_DIR 'leave.err.log'
Remove-Item -Force -ErrorAction SilentlyContinue $authOut,$authErr,$leaveOut,$leaveErr

$springProfile = if ($env:SPRING_PROFILE) { $env:SPRING_PROFILE } else { 'dev' }

$authArgs  = "-javaagent:$AGENT_JAR=output=tcpserver,port=$AUTH_JACOCO_PORT,address=127.0.0.1,includes=$JACOCO_INCLUDES -jar `"$AUTH_JAR`" --server.port=9000 --spring.profiles.active=$springProfile"
$leaveArgs = "-javaagent:$AGENT_JAR=output=tcpserver,port=$LEAVE_JACOCO_PORT,address=127.0.0.1,includes=$JACOCO_INCLUDES -jar `"$LEAVE_JAR`" --server.port=9001 --spring.profiles.active=$springProfile"

$leaveProc = Start-Process java -ArgumentList $leaveArgs -PassThru -NoNewWindow -RedirectStandardOutput $leaveOut -RedirectStandardError $leaveErr
$authProc  = Start-Process java -ArgumentList $authArgs  -PassThru -NoNewWindow -RedirectStandardOutput $authOut  -RedirectStandardError $authErr
Write-Host "  auth PID: $($authProc.Id)  leave PID: $($leaveProc.Id)" -ForegroundColor Green

Write-Host "  Waiting for ports 9000/9001..." -ForegroundColor Yellow
$authReady  = Wait-ForPort -Port 9000 -TimeoutSeconds 180 -Name 'auth'
$leaveReady = Wait-ForPort -Port 9001 -TimeoutSeconds 180 -Name 'leave'
if (-not $authReady -or -not $leaveReady) {
    Write-Host "  Dumping last 200 log lines:" -ForegroundColor Yellow
    if (Test-Path $authErr)  { Write-Host '--- auth.err.log ---'  -ForegroundColor Yellow; Get-Content $authErr  -Tail 200 }
    if (Test-Path $leaveErr) { Write-Host '--- leave.err.log ---' -ForegroundColor Yellow; Get-Content $leaveErr -Tail 200 }
    throw "Services failed to start; see $LOG_DIR"
}

Write-Host "  Waiting for JaCoCo tcpserver ports..." -ForegroundColor Yellow
$authJacocoReady  = Wait-ForPort -Port $AUTH_JACOCO_PORT  -TimeoutSeconds 60 -Name 'auth-jacoco'
$leaveJacocoReady = Wait-ForPort -Port $LEAVE_JACOCO_PORT -TimeoutSeconds 60 -Name 'leave-jacoco'
if (-not $authJacocoReady -or -not $leaveJacocoReady) {
    Write-Host "  ERROR: JaCoCo tcpserver did not start (connection refused)." -ForegroundColor Red
    Write-Host "  This usually means the -javaagent did not bind to the port or the port was taken." -ForegroundColor Red
    Write-Host "  Dumping last 200 stderr lines:" -ForegroundColor Yellow
    if (Test-Path $authErr)  { Write-Host '--- auth.err.log ---'  -ForegroundColor Yellow; Get-Content $authErr  -Tail 200 }
    if (Test-Path $leaveErr) { Write-Host '--- leave.err.log ---' -ForegroundColor Yellow; Get-Content $leaveErr -Tail 200 }
    throw "JaCoCo tcpserver ports not open (auth=$AUTH_JACOCO_PORT leave=$LEAVE_JACOCO_PORT)."
}

Write-Host "[3/5] Running pipeline..." -ForegroundColor Cyan
Set-Location $PROJECT_DIR

$pythonExe = Join-Path $PROJECT_DIR '.venv312\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) { $pythonExe = Join-Path $PROJECT_DIR '.venv\Scripts\python.exe' }

function Invoke-PipelinePython {
    param([Parameter(Mandatory=$true)][string[]]$Args)
    if (Test-Path $pythonExe) {
        & $pythonExe @Args
    } else {
        python @Args
    }
}

function Get-EnvFlag {
    param([Parameter(Mandatory=$true)][string]$Name)
    $v = [string][Environment]::GetEnvironmentVariable($Name)
    if (-not $v) { return $false }
    return $v.Trim().ToLowerInvariant() -in @('1','true','yes','y','on')
}

function Invoke-OptionalSeedBalances {
    $seedScript = Join-Path $PROJECT_DIR 'seed_balances.ps1'
    if (-not (Test-Path $seedScript)) { return }

    # Default ON (can be disabled with AUTO_SEED_BALANCES=0)
    $autoSeed = $true
    $v = [string][Environment]::GetEnvironmentVariable('AUTO_SEED_BALANCES')
    if ($v) {
        $autoSeed = $v.Trim().ToLowerInvariant() -in @('1','true','yes','y','on')
    }
    if (-not $autoSeed) {
        Write-Host "  AUTO_SEED_BALANCES disabled" -ForegroundColor DarkGray
        return
    }

    Write-Host "  Seeding leave balances for userId=1 (to avoid known 500s)..." -ForegroundColor Yellow
    try {
        powershell -ExecutionPolicy Bypass -File $seedScript -UserIds 1 -Annual 21 -Recovery 0 | Out-Host
    } catch {
        Write-Host "  WARN: seed_balances.ps1 failed; continuing (tests may hit 500 on /api/balances/1)" -ForegroundColor Yellow
    }
}

function Test-TcpPortOpen {
    param([Parameter(Mandatory=$true)][int]$Port)
    try {
        return (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Invoke-JaCoCoDump {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][int]$Port,
        [Parameter(Mandatory=$true)][string]$DestFile,
        [int]$Retries = 8,
        [int]$SleepSeconds = 2
    )

    for ($i = 1; $i -le $Retries; $i++) {
        if (-not (Test-TcpPortOpen -Port $Port)) {
            Write-Host "  [$Name] JaCoCo port $Port not open (attempt $i/$Retries)" -ForegroundColor Yellow
            Start-Sleep -Seconds $SleepSeconds
            continue
        }

        & java -jar $CLI_JAR dump --address 127.0.0.1 --port $Port --destfile $DestFile --reset
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0 -and (Test-Path $DestFile)) {
            $size = (Get-Item $DestFile).Length
            if ($size -gt 0) {
                Write-Host "  [$Name] dumped exec -> $DestFile ($size bytes)" -ForegroundColor Green
                return $true
            }
        }

        Write-Host "  [$Name] dump failed (exit=$exitCode) (attempt $i/$Retries)" -ForegroundColor Yellow
        Start-Sleep -Seconds $SleepSeconds
    }

    return $false
}

# Make sure we don't accidentally run in "generate-only" mode from a previous session.
Remove-Item Env:SKIP_TEST_EXECUTION -ErrorAction SilentlyContinue | Out-Null

# Default behavior for this script is "debug-friendly": keep services running, always
# generate coverage artifacts, and don't hard-fail the workflow just because tests or
# coverage thresholds aren't met yet. You can opt into strict gating by setting
# STRICT_GATES=1 (or override individual env vars).
if (-not (Get-EnvFlag 'STRICT_GATES')) {
    if (-not $env:ALLOW_TEST_FAILURES) { $env:ALLOW_TEST_FAILURES = '1' }
    if (-not $env:MIN_TEST_PASS_RATE) { $env:MIN_TEST_PASS_RATE = '0' }
    if (-not $env:MAX_TEST_FAILED_SCENARIOS) { $env:MAX_TEST_FAILED_SCENARIOS = '999999' }

    if (-not $env:FAIL_ON_COVERAGE_QG) { $env:FAIL_ON_COVERAGE_QG = '0' }
    if (-not $env:ALLOW_COVERAGE_QG_FAILURE) { $env:ALLOW_COVERAGE_QG_FAILURE = '1' }
}

if ((Get-EnvFlag 'ENABLE_RAG') -or (Get-EnvFlag 'RAG_ENABLE')) {
    Write-Host "  RAG enabled -> building CSV + Chroma index..." -ForegroundColor Yellow
    $env:RAG_ENABLE = '1'
    Invoke-PipelinePython -Args @("$PROJECT_DIR\main.py", 'extract-e2egit')
    if ($LASTEXITCODE -ne 0) { throw "extract-e2egit failed with exit code $LASTEXITCODE" }
    Invoke-PipelinePython -Args @("$PROJECT_DIR\main.py", 'ingest')
    if ($LASTEXITCODE -ne 0) { throw "ingest failed with exit code $LASTEXITCODE" }
}


# === STEP 1: Seeding database for E2E tests (userId=8) ===
Write-Host "=== STEP 1: Seeding database for userId=8 ===" -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File .\seed_balances.ps1 -Email "admin@test.com" -Password "admin123"

# === STEP 2: Running pipeline ===
Write-Host "=== STEP 2: Running E2E pipeline ===" -ForegroundColor Cyan

# (Retain the original optional seeding for other users if needed)
Invoke-OptionalSeedBalances

Invoke-PipelinePython -Args @("$PROJECT_DIR\run_pipeline.py", '--services', 'auth,leave')
$pipelineExitCode = $LASTEXITCODE
if ($pipelineExitCode -ne 0) {
    Write-Host "  Pipeline reported failure (exit=$pipelineExitCode). Continuing to dump JaCoCo for debugging..." -ForegroundColor Yellow
}

Write-Host "[4/5] Dumping coverage data from JaCoCo agents..." -ForegroundColor Cyan
$authExec  = Join-Path $COVERAGE_DIR 'auth.exec'
$leaveExec = Join-Path $COVERAGE_DIR 'leave.exec'

# Prevent stale exec files from a previous run being used when a dump fails.
Remove-Item -Force -ErrorAction SilentlyContinue $authExec,$leaveExec

if ($authProc -and $authProc.HasExited) {
    Write-Host "  WARNING: auth process has exited before JaCoCo dump (PID $($authProc.Id))." -ForegroundColor Yellow
}
if ($leaveProc -and $leaveProc.HasExited) {
    Write-Host "  WARNING: leave process has exited before JaCoCo dump (PID $($leaveProc.Id))." -ForegroundColor Yellow
}

$authDumpOk  = Invoke-JaCoCoDump -Name 'auth'  -Port $AUTH_JACOCO_PORT  -DestFile $authExec
$leaveDumpOk = Invoke-JaCoCoDump -Name 'leave' -Port $LEAVE_JACOCO_PORT -DestFile $leaveExec

if (-not $authDumpOk -or -not $leaveDumpOk) {
    Write-Host "  ERROR: Failed to dump JaCoCo exec from tcpserver." -ForegroundColor Red
    Write-Host "  Ports: auth=$AUTH_JACOCO_PORT leave=$LEAVE_JACOCO_PORT" -ForegroundColor Red
    Write-Host "  Dumping last 200 stderr lines (if available):" -ForegroundColor Yellow
    if (Test-Path $authErr)  { Write-Host '--- auth.err.log ---'  -ForegroundColor Yellow; Get-Content $authErr  -Tail 200 }
    if (Test-Path $leaveErr) { Write-Host '--- leave.err.log ---' -ForegroundColor Yellow; Get-Content $leaveErr -Tail 200 }

    # Keep the original pipeline exit code if it failed, otherwise fail explicitly.
    if ($pipelineExitCode -ne 0) { exit $pipelineExitCode }
    exit 2
}

Write-Host "[5/5] Generating jacoco.xml/html..." -ForegroundColor Cyan
$reportDir = Join-Path $COVERAGE_DIR 'report'
$htmlDir   = Join-Path $reportDir 'html'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$jacocoXml = Join-Path $reportDir 'jacoco.xml'
& java -jar $CLI_JAR report $authExec $leaveExec --classfiles $AUTH_CLASSES --classfiles $LEAVE_CLASSES --xml $jacocoXml --html $htmlDir
if ($LASTEXITCODE -ne 0) {
    throw "jacococli report failed with exit code $LASTEXITCODE"
}

Write-Host "Done." -ForegroundColor Green
Write-Host "  XML:  output/jacoco/report/jacoco.xml" -ForegroundColor Green
Write-Host "  HTML: output/jacoco/report/html/index.html" -ForegroundColor Green
Write-Host "  Open: Start-Process .\output\jacoco\report\html\index.html" -ForegroundColor Green

if ($pipelineExitCode -ne 0) {
    exit $pipelineExitCode
}
