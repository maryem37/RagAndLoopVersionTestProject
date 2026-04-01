#!/usr/bin/env pwsh
# Start DemandeConge microservice
Set-Location "C:\Bureau\Bureau\microservices\DemandeConge"
Write-Host "Starting DemandeConge from: $(Get-Location)" -ForegroundColor Green
mvn org.springframework.boot:spring-boot-maven-plugin:run
