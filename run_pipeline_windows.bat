@echo off
REM run_pipeline_windows.bat
REM Windows batch script to run the test automation pipeline with UTF-8 encoding
REM 
REM Usage:
REM   run_pipeline_windows.bat                  # Run all services
REM   run_pipeline_windows.bat auth             # Run specific service
REM   run_pipeline_windows.bat auth leave       # Multiple services

setlocal enabledelayedexpansion

REM Set UTF-8 encoding
set PYTHONIOENCODING=utf-8
chcp 65001 >nul 2>&1

REM Get arguments
set ARGS=%*
if "%ARGS%"=="" (
    echo [INFO] Running all services
    python run_pipeline_windows.py
) else (
    echo [INFO] Running with arguments: %ARGS%
    python run_pipeline_windows.py --services %ARGS%
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Pipeline completed successfully!
) else (
    echo.
    echo [ERROR] Pipeline failed with exit code %ERRORLEVEL%
)

exit /b %ERRORLEVEL%
