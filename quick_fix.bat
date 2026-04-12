@echo off
REM QUICK FIX: Start backend and run pipeline
REM Kill all existing Java
taskkill /F /IM java.exe 2>nul
timeout /t 3

REM Start services (adjust paths to your actual backend locations)
echo Starting mock services...

REM You need to start your actual backend services here
REM For now, create mock endpoints that respond

echo Services require running on 9000 and 9001
echo Please ensure your microservices are running BEFORE running pipeline

pause
