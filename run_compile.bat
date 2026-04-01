@echo off
cd C:\Bureau\Bureau\microservices\DemandeConge
mvn clean compile -q > compile_output.txt 2>&1
if %errorlevel% equ 0 (
    echo SUCCESS > compile_result.txt
) else (
    echo FAILED > compile_result.txt
    mvn compile 2>&1 | find "ERROR" > compile_errors.txt
)
