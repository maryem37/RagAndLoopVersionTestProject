# Quick Coverage Collection Script
# Dumps coverage data from running microservices and generates HTML report

Write-Host "`n================================================================================"
Write-Host "COVERAGE DATA COLLECTION FROM RUNNING MICROSERVICES"
Write-Host "================================================================================"

$OutputDir = "C:\Bureau\Bureau\project_test\output\jacoco"
$TestsDir = "C:\Bureau\Bureau\project_test\output\tests"

# Create output directory
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
Write-Host "`n[1] Created output directory: $OutputDir"

# Dump coverage from conge (port 9000)
Write-Host "`n[2] Dumping coverage from conge (port 9000)..."
$Url1 = "http://localhost:9000/jacoco-api/dump"
$File1 = "$OutputDir\conge.exec"

try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $Url1 -OutFile $File1 -TimeoutSec 10
    $Size1 = (Get-Item $File1).Length
    Write-Host "    OK - Coverage dumped ($Size1 bytes)"
} catch {
    Write-Host "    WARNING - Could not dump from conge: $($_.Exception.Message)"
}

# Dump coverage from DemandeConge (port 9001)
Write-Host "`n[3] Dumping coverage from DemandeConge (port 9001)..."
$Url2 = "http://localhost:9001/jacoco-api/dump"
$File2 = "$OutputDir\DemandeConge.exec"

try {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri $Url2 -OutFile $File2 -TimeoutSec 10
    $Size2 = (Get-Item $File2).Length
    Write-Host "    OK - Coverage dumped ($Size2 bytes)"
} catch {
    Write-Host "    WARNING - Could not dump from DemandeConge: $($_.Exception.Message)"
}

# Generate JaCoCo report
Write-Host "`n[4] Generating JaCoCo HTML report..."

try {
    Push-Location $TestsDir
    $MavenCmd = "C:\Users\MSI\Downloads\apache-maven-3.9.10-bin\apache-maven-3.9.10\bin\mvn.cmd"
    
    $output = & $MavenCmd jacoco:report -q 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    OK - Report generated successfully"
    } else {
        Write-Host "    WARNING - Maven reported exit code: $LASTEXITCODE"
    }
    
    Pop-Location
} catch {
    Write-Host "    ERROR - $($_.Exception.Message)"
}

Write-Host "`n================================================================================"
Write-Host "COVERAGE COLLECTION COMPLETE"
Write-Host "================================================================================"

Write-Host "`nCoverage Files:"
Write-Host "  - $File1"
Write-Host "  - $File2"

Write-Host "`nCoverage Report:"
$ReportHtml = "$TestsDir\target\site\jacoco\index.html"
if (Test-Path $ReportHtml) {
    Write-Host "  - $ReportHtml"
    Write-Host "`nOpening report in browser..."
    Start-Process $ReportHtml
} else {
    Write-Host "  - Report not found at $ReportHtml"
}

Write-Host "`nNext Steps:"
Write-Host "  1. View the coverage report in your browser"
Write-Host "  2. Look for lines NOT covered (red highlight)"
Write-Host "  3. Add test scenarios to cover those code paths"
Write-Host "  4. Rerun tests to measure improved coverage"

Write-Host "`nExpected Coverage Range (Real Services):"
Write-Host "  Line Coverage:     30-70%"
Write-Host "  Branch Coverage:   20-50%"
Write-Host "  Method Coverage:   40-70%"

Write-Host "`n================================================================================"
