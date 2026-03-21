$AGENT_JAR   = "C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar"
$CLI_JAR     = "C:\Bureau\Bureau\project_test\jacococli.jar"
$PROJECT_DIR = "C:\Bureau\Bureau\project_test"
$OUTPUT_DIR  = "$PROJECT_DIR\output"
$COVERAGE_DIR= "$OUTPUT_DIR\jacoco"
$CONGE_JAR   = "C:\Bureau\Bureau\microservices\conge\target\congee-0.0.1-SNAPSHOT.jar"
$AUTH_JAR    = "C:\Bureau\Bureau\microservices1\user-service\target\user-service-0.0.1-SNAPSHOT.jar"
$CONGE_JACOCO_PORT = 6301
$AUTH_JACOCO_PORT  = 6300
$JWT = $env:TEST_JWT_TOKEN
if (-not $JWT) { Write-Host "ERROR: TEST_JWT_TOKEN not set" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Force -Path $COVERAGE_DIR | Out-Null

Write-Host "[1/6] Stopping existing services..." -ForegroundColor Cyan
Get-Process java -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmd -match "congee|user-service") { Write-Host "  Stopping PID $($_.Id)"; $_.Kill(); Start-Sleep -Seconds 3 }
}

Write-Host "[2/6] Starting services with JaCoCo agent..." -ForegroundColor Cyan
$congeAgent = "-javaagent:${AGENT_JAR}=output=tcpserver,port=${CONGE_JACOCO_PORT},address=127.0.0.1,includes=tn.enis.conge.* -jar `"$CONGE_JAR`""
$authAgent  = "-javaagent:${AGENT_JAR}=output=tcpserver,port=${AUTH_JACOCO_PORT},address=127.0.0.1,includes=tn.enis.conge.* -jar `"$AUTH_JAR`""
$congeProc = Start-Process java -ArgumentList $congeAgent -PassThru -WindowStyle Minimized
$authProc  = Start-Process java -ArgumentList $authAgent  -PassThru -WindowStyle Minimized
Write-Host "  conge PID: $($congeProc.Id)  auth PID: $($authProc.Id)" -ForegroundColor Green
Write-Host "  Waiting 30s for services to start..."
Start-Sleep -Seconds 30

Write-Host "[3/6] Running pipeline..." -ForegroundColor Cyan
Set-Location $PROJECT_DIR
& "$PROJECT_DIR\.venv312\Scripts\python.exe" -m graph.workflow

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
New-Item -ItemType Directory -Force -Path $congeClassDir | Out-Null
New-Item -ItemType Directory -Force -Path $authClassDir  | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Extract-AppClasses($jarPath, $outDir) {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($jarPath)
    foreach ($entry in $zip.Entries) {
        if ($entry.FullName -match "^BOOT-INF/classes/.*\.class$") {
            $rel  = $entry.FullName -replace "^BOOT-INF/classes/", ""
            $dest = Join-Path $outDir $rel
            $destDir = Split-Path $dest -Parent
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $dest, $true)
        }
    }
    $zip.Dispose()
}
Write-Host "  Extracting conge classes..."
Extract-AppClasses $CONGE_JAR $congeClassDir
Write-Host "  Extracting auth classes..."
Extract-AppClasses $AUTH_JAR $authClassDir
$congeCount = (Get-ChildItem $congeClassDir -Recurse -Filter "*.class").Count
$authCount  = (Get-ChildItem $authClassDir  -Recurse -Filter "*.class").Count
Write-Host "  conge: $congeCount classes   auth: $authCount classes" -ForegroundColor Green

Write-Host "[6/6] Generating jacoco.xml from application classes only..." -ForegroundColor Cyan
$jacocoDir = "$OUTPUT_DIR\jacoco\report"
New-Item -ItemType Directory -Force -Path $jacocoDir | Out-Null
if (Test-Path $congeExec) {
    & java -jar $CLI_JAR report $congeExec --classfiles $congeClassDir --xml "$jacocoDir\jacoco.xml" --html "$jacocoDir\html"
    if (Test-Path "$jacocoDir\jacoco.xml") {
        $sz = [Math]::Round((Get-Item "$jacocoDir\jacoco.xml").Length/1KB,1)
        Write-Host "  jacoco.xml written ($sz KB) -> coverage_analyst will find it" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: jacoco.xml not written" -ForegroundColor Yellow
    }
}

Write-Host "`nDone! Now run: python run_pipeline.py" -ForegroundColor Green
Write-Host "The pipeline will read jacoco.xml and show real coverage numbers." -ForegroundColor Green

