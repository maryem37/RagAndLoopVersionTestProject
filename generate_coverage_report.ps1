# Generate JaCoCo Coverage Report
$testProjectPath = "C:\Bureau\Bureau\project_test\output\tests"
$congePath = "C:\Bureau\Bureau\microservices\conge"
$jacocoExecFile = "$testProjectPath\target\jacoco.exec"
$reportOutputDir = "$testProjectPath\target\site\jacoco"

Write-Host "=== JaCoCo Coverage Report Generation ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $jacocoExecFile)) {
    Write-Host "ERROR: jacoco.exec not found" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Checking prerequisites..." -ForegroundColor Yellow
$execSize = (Get-Item $jacocoExecFile).Length
Write-Host "[OK] Coverage data: $execSize bytes"
Write-Host "[OK] Conge classes: $congePath\target\classes"
Write-Host ""

Write-Host "[2/3] Creating output directory..." -ForegroundColor Yellow
if (-not (Test-Path $reportOutputDir)) {
    New-Item -ItemType Directory -Path $reportOutputDir -Force | Out-Null
}
Write-Host "[OK] Output directory ready"
Write-Host ""

Write-Host "[3/3] Generating report using Maven..." -ForegroundColor Yellow
$tempPom = "$testProjectPath\target\temp-pom.xml"

$pomContent = @"
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>tn.enis</groupId>
    <artifactId>coverage-report</artifactId>
    <version>1.0</version>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.11</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>report</goal>
                        </goals>
                        <configuration>
                            <dataFile>$jacocoExecFile</dataFile>
                            <outputDirectory>$reportOutputDir</outputDirectory>
                            <classesDirectory>$congePath\target\classes</classesDirectory>
                            <sourceEncoding>UTF-8</sourceEncoding>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
"@

$pomContent | Out-File $tempPom -Encoding UTF8

cd $testProjectPath
mvn -f $tempPom jacoco:report -q

if (Test-Path "$reportOutputDir\index.html") {
    Write-Host "[OK] Report generated successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Report location: $reportOutputDir\index.html" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] Report not generated" -ForegroundColor Red
}

if (Test-Path $tempPom) {
    Remove-Item $tempPom -Force
}
