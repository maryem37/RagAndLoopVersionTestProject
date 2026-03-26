$AGENT_JAR   = "C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar"
$CLI_JAR     = "C:\Bureau\Bureau\project_test\jacococli.jar"
$PROJECT_DIR = "C:\Bureau\Bureau\project_test"
$OUTPUT_DIR  = "$PROJECT_DIR\output"
$COVERAGE_DIR= "$OUTPUT_DIR\jacoco"
$LOG_DIR     = "$COVERAGE_DIR\logs"
$CONGE_JAR   = "C:\Bureau\Bureau\microservices\DemandeConge\target\DemandeConge-0.0.1-SNAPSHOT.jar"
$AUTH_JAR    = "C:\Bureau\Bureau\microservices\conge\target\congee-0.0.1-SNAPSHOT.jar"
New-Item -ItemType Directory -Force -Path $COVERAGE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $port = $listener.LocalEndpoint.Port
    $listener.Stop()
    return $port
}

$CONGE_JACOCO_PORT = Get-FreeTcpPort
$AUTH_JACOCO_PORT  = Get-FreeTcpPort
while ($AUTH_JACOCO_PORT -eq $CONGE_JACOCO_PORT) { $AUTH_JACOCO_PORT = Get-FreeTcpPort }
Write-Host "Using JaCoCo tcpserver ports: conge=$CONGE_JACOCO_PORT auth=$AUTH_JACOCO_PORT" -ForegroundColor DarkCyan

function Wait-ForPort {
    param(
        [Parameter(Mandatory=$true)][int]$Port,
        [Parameter(Mandatory=$true)][int]$TimeoutSeconds,
        [string]$Name = "service"
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $ok = Test-NetConnection -ComputerName 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
            if ($ok) {
                Write-Host "  $Name is listening on :$Port" -ForegroundColor Green
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 2
    }
    Write-Host "  ERROR: $Name did not open port :$Port within ${TimeoutSeconds}s" -ForegroundColor Red
    return $false
}

Write-Host "[1/6] Stopping existing services..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 9000,9001 -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $pid = $_.OwningProcess
        if ($pid) {
            Write-Host "  Freeing port $($_.LocalPort) (PID $pid)" -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    } catch {}
}

# Extra safety: stop previously launched service processes by jar name
Get-Process java -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmd -match "DemandeConge-0\.0\.1-SNAPSHOT\.jar|congee-0\.0\.1-SNAPSHOT\.jar") {
        Write-Host "  Stopping PID $($_.Id)" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

Write-Host "[2/6] Starting services with JaCoCo agent..." -ForegroundColor Cyan
$congeAgent = "-javaagent:${AGENT_JAR}=output=tcpserver,port=${CONGE_JACOCO_PORT},address=127.0.0.1,includes=tn.enis.DemandeConge.* -jar `"$CONGE_JAR`" --server.port=9001"
$authAgent  = "-javaagent:${AGENT_JAR}=output=tcpserver,port=${AUTH_JACOCO_PORT},address=127.0.0.1,includes=tn.enis.conge.* -jar `"$AUTH_JAR`" --server.port=9000"
$congeOut = Join-Path $LOG_DIR "conge.out.log"
$congeErr = Join-Path $LOG_DIR "conge.err.log"
$authOut  = Join-Path $LOG_DIR "auth.out.log"
$authErr  = Join-Path $LOG_DIR "auth.err.log"
Remove-Item -Force -ErrorAction SilentlyContinue $congeOut,$congeErr,$authOut,$authErr

$congeProc = Start-Process java -ArgumentList $congeAgent -PassThru -NoNewWindow -RedirectStandardOutput $congeOut -RedirectStandardError $congeErr
$authProc  = Start-Process java -ArgumentList $authAgent  -PassThru -NoNewWindow -RedirectStandardOutput $authOut  -RedirectStandardError $authErr
Write-Host "  conge PID: $($congeProc.Id)  auth PID: $($authProc.Id)" -ForegroundColor Green
Write-Host "  Waiting for services to start (ports 9000/9001)..."

$authReady  = Wait-ForPort -Port 9000 -TimeoutSeconds 120 -Name "auth"
$congeReady = Wait-ForPort -Port 9001 -TimeoutSeconds 120 -Name "conge"
if (-not $authReady -or -not $congeReady) {
    Write-Host "  Dumping last 120 log lines to help debug:" -ForegroundColor Yellow
    if (Test-Path $authErr)  { Write-Host "--- auth.err.log ---" -ForegroundColor Yellow;  Get-Content $authErr  -Tail 120 }
    if (Test-Path $authOut)  { Write-Host "--- auth.out.log ---" -ForegroundColor Yellow;  Get-Content $authOut  -Tail 120 }
    if (Test-Path $congeErr) { Write-Host "--- conge.err.log ---" -ForegroundColor Yellow; Get-Content $congeErr -Tail 120 }
    if (Test-Path $congeOut) { Write-Host "--- conge.out.log ---" -ForegroundColor Yellow; Get-Content $congeOut -Tail 120 }
    throw "Services failed to start; see logs in $LOG_DIR"
}

Write-Host "[3/6] Running pipeline..." -ForegroundColor Cyan
Set-Location $PROJECT_DIR
$pythonExe = "$PROJECT_DIR\.venv\Scripts\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe "$PROJECT_DIR\run_pipeline.py" --services auth,leave
} else {
    Write-Host "  WARNING: .venv Python not found at $pythonExe; falling back to 'python' from PATH" -ForegroundColor Yellow
    python "$PROJECT_DIR\run_pipeline.py" --services auth,leave
}

Write-Host "[4/6] Dumping coverage data..." -ForegroundColor Cyan
$congeExec = "$COVERAGE_DIR\conge.exec"
$authExec  = "$COVERAGE_DIR\auth.exec"
& java -jar $CLI_JAR dump --address 127.0.0.1 --port $CONGE_JACOCO_PORT --destfile $congeExec --reset
& java -jar $CLI_JAR dump --address 127.0.0.1 --port $AUTH_JACOCO_PORT  --destfile $authExec  --reset
if (Test-Path $congeExec) { Write-Host "  conge.exec: $([Math]::Round((Get-Item $congeExec).Length/1KB,1)) KB" -ForegroundColor Green }
if (Test-Path $authExec)  { Write-Host "  auth.exec:  $([Math]::Round((Get-Item $authExec).Length/1KB,1)) KB"  -ForegroundColor Green }

Write-Host "[5/6] Extracting application classes from fat JAR..." -ForegroundColor Cyan
$congeClassDir = "$COVERAGE_DIR\conge-classes"
$authClassDir  = "$COVERAGE_DIR\auth-classes"
if (Test-Path $congeClassDir) { Remove-Item -Recurse -Force -Path $congeClassDir -ErrorAction SilentlyContinue }
if (Test-Path $authClassDir)  { Remove-Item -Recurse -Force -Path $authClassDir  -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force -Path $congeClassDir | Out-Null
New-Item -ItemType Directory -Force -Path $authClassDir  | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Extract-AppClasses($jarPath, $outDir, $includePathPrefix) {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($jarPath)
    foreach ($entry in $zip.Entries) {
        if ($entry.FullName -match "^BOOT-INF/classes/.*\.class$") {
            $rel  = $entry.FullName -replace "^BOOT-INF/classes/", ""
            if ($includePathPrefix -and (-not $rel.StartsWith($includePathPrefix))) {
                continue
            }
            $dest = Join-Path $outDir $rel
            $destDir = Split-Path $dest -Parent
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $dest, $true)
        }
    }
    $zip.Dispose()
}
Write-Host "  Extracting conge classes..."
Extract-AppClasses $CONGE_JAR $congeClassDir "tn/enis/DemandeConge/"
Write-Host "  Extracting auth classes..."
Extract-AppClasses $AUTH_JAR $authClassDir "tn/enis/conge/"
$congeCount = (Get-ChildItem $congeClassDir -Recurse -Filter "*.class").Count
$authCount  = (Get-ChildItem $authClassDir  -Recurse -Filter "*.class").Count
Write-Host "  conge: $congeCount classes   auth: $authCount classes" -ForegroundColor Green

Write-Host "[6/6] Generating jacoco.xml from application classes only..." -ForegroundColor Cyan
$jacocoDir = "$OUTPUT_DIR\jacoco\report"
New-Item -ItemType Directory -Force -Path $jacocoDir | Out-Null
$execFiles = @()
if (Test-Path $congeExec) { $execFiles += $congeExec }
if (Test-Path $authExec)  { $execFiles += $authExec }

if ($execFiles.Count -eq 0) {
    Write-Host "  WARNING: No .exec files found to report" -ForegroundColor Yellow
} else {
    & java -jar $CLI_JAR report @execFiles --classfiles $congeClassDir --classfiles $authClassDir --xml "$jacocoDir\jacoco.xml" --html "$jacocoDir\html"
    if (Test-Path "$jacocoDir\jacoco.xml") {
        $sz = [Math]::Round((Get-Item "$jacocoDir\jacoco.xml").Length/1KB,1)
        Write-Host "  jacoco.xml written ($sz KB) -> coverage_analyst will find it" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: jacoco.xml not written" -ForegroundColor Yellow
    }
}

Write-Host "[post] Running Coverage Analyst on generated jacoco.xml..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = 'utf-8'
if (Test-Path $pythonExe) {
    & $pythonExe -c "import sys; sys.path.insert(0,'.'); from graph.state import TestAutomationState; from agents.coverage_analyst import CoverageAnalystAgent; s=TestAutomationState(workflow_id='run_with_coverage', user_story='', service_name='auth_leave', swagger_spec={}, swagger_specs={}); s.execution_result={'total':0,'passed':0,'failed':0,'skipped':0,'raw_output_tail':''}; CoverageAnalystAgent().analyze(s)"
} else {
    python -c "import sys; sys.path.insert(0,'.'); from graph.state import TestAutomationState; from agents.coverage_analyst import CoverageAnalystAgent; s=TestAutomationState(workflow_id='run_with_coverage', user_story='', service_name='auth_leave', swagger_spec={}, swagger_specs={}); s.execution_result={'total':0,'passed':0,'failed':0,'skipped':0,'raw_output_tail':''}; CoverageAnalystAgent().analyze(s)"
}

Write-Host "`nDone! Now run: python run_pipeline.py" -ForegroundColor Green
Write-Host "The pipeline will read jacoco.xml and show real coverage numbers." -ForegroundColor Green

