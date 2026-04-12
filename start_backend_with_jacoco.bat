@echo off
REM START BACKEND SERVICES WITH JaCoCo PROFILING
REM This script starts both auth and leave microservices with JaCoCo agent enabled

setlocal enabledelayedexpansion

set PROJECT_ROOT=C:\Bureau\Bureau\project_test
set MAVEN_HOME=C:\Users\MSI\Downloads\apache-maven-3.9.10-bin\apache-maven-3.9.10
set JACOCO_JAR=%PROJECT_ROOT%\jacocoagent.jar

REM Check if JaCoCo agent exists
if not exist "%JACOCO_JAR%" (
    echo Downloading JaCoCo agent...
    powershell -Command "Invoke-WebRequest -Uri 'https://repo1.maven.org/maven2/org/jacoco/org.jacoco.agent/0.8.11/org.jacoco.agent-0.8.11-runtime.jar' -OutFile '%JACOCO_JAR%' -UseBasicParsing"
)

echo.
echo ===============================================
echo   STARTING BACKEND SERVICES WITH JaCoCo
echo ===============================================
echo.

REM Kill any existing Java processes
taskkill /F /IM java.exe 2>nul
timeout /t 2

REM Start Auth Service in a new window
echo Starting Auth Service on port 9000 with JaCoCo on port 36320...
start "Auth Service" cmd /k "cd %PROJECT_ROOT% && %MAVEN_HOME%\bin\mvn.cmd spring-boot:run -Dspring-boot.run.jvmArguments=\"-javaagent:%JACOCO_JAR%=destfile=jacoco-auth.exec,port=36320\""

timeout /t 5

REM Start Leave Service in a new window
echo Starting Leave Service on port 9001 with JaCoCo on port 36321...
start "Leave Service" cmd /k "cd %PROJECT_ROOT% && %MAVEN_HOME%\bin\mvn.cmd spring-boot:run -Dspring-boot.run.jvmArguments=\"-javaagent:%JACOCO_JAR%=destfile=jacoco-leave.exec,port=36321\""

echo.
echo ===============================================
echo   WAITING FOR SERVICES TO START (60 seconds)...
echo ===============================================
echo.

timeout /t 60

echo.
echo Verifying services...
powershell -Command "Test-NetConnection -ComputerName 127.0.0.1 -Port 9000 -InformationLevel Quiet; if ($?) { Write-Host '[OK] Auth Service (9000)' } else { Write-Host '[FAIL] Auth Service (9000)' }"
powershell -Command "Test-NetConnection -ComputerName 127.0.0.1 -Port 9001 -InformationLevel Quiet; if ($?) { Write-Host '[OK] Leave Service (9001)' } else { Write-Host '[FAIL] Leave Service (9001)' }"

echo.
echo Services are ready! Run: python collect_jacoco_coverage.py
echo.

pause
