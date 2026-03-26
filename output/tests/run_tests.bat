@echo off
REM Test Execution Script for Leave Request Management System (Windows)
REM This script provides convenient commands to run different test categories

setlocal enabledelayedexpansion

REM Set project directory
set "PROJECT_DIR=%~dp0"
set "REPORT_DIR=%PROJECT_DIR%target"

REM Main menu loop
:menu
cls
echo ======================================
echo Test Execution Menu
echo ======================================
echo.
echo 1. Run all tests
echo 2. Run unit tests only
echo 3. Run integration tests only
echo 4. Run E2E tests only
echo 5. Run contract tests only
echo 6. Run with coverage report
echo 7. Run specific test class
echo 8. View coverage report
echo 9. View surefire report
echo 10. Clean build artifacts
echo 0. Exit
echo.
set /p choice="Select option (0-10): "

if "%choice%"=="1" goto run_all
if "%choice%"=="2" goto run_unit
if "%choice%"=="3" goto run_integration
if "%choice%"=="4" goto run_e2e
if "%choice%"=="5" goto run_contract
if "%choice%"=="6" goto run_coverage
if "%choice%"=="7" goto run_specific
if "%choice%"=="8" goto view_coverage
if "%choice%"=="9" goto view_surefire
if "%choice%"=="10" goto clean_build
if "%choice%"=="0" goto end
echo Invalid option. Please try again.
pause
goto menu

:run_all
cls
echo ======================================
echo Running All Tests
echo ======================================
echo.
cd /d "%PROJECT_DIR%"
call mvn clean test
echo.
echo Tests completed!
pause
goto menu

:run_unit
cls
echo ======================================
echo Running Unit Tests
echo ======================================
echo.
cd /d "%PROJECT_DIR%"
call mvn test -Dtest=*Service*Test
echo.
echo Unit tests completed!
pause
goto menu

:run_integration
cls
echo ======================================
echo Running Integration Tests
echo ======================================
echo.
REM Check if services are running
echo Note: Ensure services are running on:
echo   - Auth Service: http://localhost:9000
echo   - Leave Service: http://localhost:8080
echo.
cd /d "%PROJECT_DIR%"
call mvn test -Dtest=*IntegrationTest
echo.
echo Integration tests completed!
pause
goto menu

:run_e2e
cls
echo ======================================
echo Running E2E Tests
echo ======================================
echo.
echo Required: Services must be running on:
echo   - Auth Service: http://localhost:9000
echo   - Leave Service: http://localhost:8080
echo.
cd /d "%PROJECT_DIR%"
call mvn test -Dtest=*E2ETest
echo.
echo E2E tests completed!
pause
goto menu

:run_contract
cls
echo ======================================
echo Running Contract Tests
echo ======================================
echo.
cd /d "%PROJECT_DIR%"
call mvn test -Dtest=*ContractTest
echo.
echo Contract tests completed!
pause
goto menu

:run_coverage
cls
echo ======================================
echo Running Tests with Coverage Report
echo ======================================
echo.
cd /d "%PROJECT_DIR%"
call mvn clean test jacoco:report
echo.
echo Coverage report generated!
echo Open: target\site\jacoco\index.html
pause
goto menu

:run_specific
cls
echo ======================================
echo Running Specific Test Class
echo ======================================
echo.
set /p test_name="Enter test class name (e.g., AuthServiceTest): "
if "%test_name%"=="" (
    echo No test class specified!
    pause
    goto menu
)
cd /d "%PROJECT_DIR%"
call mvn test -Dtest="%test_name%"
echo.
echo Test completed!
pause
goto menu

:view_coverage
cls
if not exist "%REPORT_DIR%\site\jacoco\index.html" (
    echo Coverage report not found.
    echo Run tests with coverage first (option 6).
    pause
    goto menu
)
echo Opening coverage report...
start "%REPORT_DIR%\site\jacoco\index.html"
pause
goto menu

:view_surefire
cls
if not exist "%REPORT_DIR%\site\surefire-report.html" (
    echo Surefire report not found.
    echo Run tests first.
    pause
    goto menu
)
echo Opening surefire report...
start "%REPORT_DIR%\site\surefire-report.html"
pause
goto menu

:clean_build
cls
echo ======================================
echo Cleaning Build Artifacts
echo ======================================
echo.
cd /d "%PROJECT_DIR%"
call mvn clean
echo.
echo Build cleaned!
pause
goto menu

:end
cls
echo ======================================
echo Exiting Test Execution Script
echo ======================================
exit /b 0
