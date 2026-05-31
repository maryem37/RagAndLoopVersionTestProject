<#
cleanup_share.ps1

Nettoie le projet avant partage (candidature / repo public / zip).
- Supprime caches et artefacts régénérables
- Met les secrets de .env en sécurité (backup + suppression du fichier)

Usage:
  powershell -ExecutionPolicy Bypass -File .\cleanup_share.ps1
  powershell -ExecutionPolicy Bypass -File .\cleanup_share.ps1 -KeepRagDb
  powershell -ExecutionPolicy Bypass -File .\cleanup_share.ps1 -KeepNodeModules

NOTE: Ce script ne touche PAS au code source (agents/, graph/, tools/, etc.).
#>

[CmdletBinding()]
param(
  [switch]$KeepRagDb,
  [switch]$KeepOutput,
  [switch]$KeepNodeModules,
  [switch]$KeepVenv,
  [switch]$KeepDist,
  [switch]$KeepLogs,
  [switch]$KeepEnv,
  [switch]$DeleteJacocoJars
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Remove-PathSafe([string]$path) {
  if (Test-Path -LiteralPath $path) {
    Write-Host "Removing $path" -ForegroundColor Yellow
    Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "== Cleanup for sharing ==" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor Gray

# 1) Secrets
if (-not $KeepEnv) {
  if (Test-Path -LiteralPath '.env') {
    $backup = ".env.private.backup.$(Get-Date -Format yyyyMMdd_HHmmss)"
    Copy-Item -LiteralPath '.env' -Destination $backup -Force
    Write-Host "Backed up .env -> $backup" -ForegroundColor Green
    Remove-Item -LiteralPath '.env' -Force
    Write-Host "Removed .env (DO NOT SHARE secrets)" -ForegroundColor Green
  }
}

# 2) Caches / generated
if (-not $KeepVenv) {
  Get-ChildItem -LiteralPath . -Directory -Force | Where-Object { $_.Name -like '.venv*' } | ForEach-Object {
    Remove-PathSafe $_.FullName
  }
}

if (-not $KeepNodeModules) {
  Remove-PathSafe 'node_modules'
}

if (-not $KeepDist) {
  Remove-PathSafe 'dist'
}

if (-not $KeepOutput) {
  Remove-PathSafe 'output'
  Remove-PathSafe 'test-results'
}

if (-not $KeepRagDb) {
  Remove-PathSafe 'chroma_db'
}

if (-not $KeepLogs) {
  Get-ChildItem -LiteralPath . -File -Force | Where-Object {
    $_.Name -like 'pipeline_*.log' -or $_.Name -like 'LLM_RAW_OUTPUT*.txt'
  } | ForEach-Object {
    Remove-PathSafe $_.FullName
  }
}

if ($DeleteJacocoJars) {
  Get-ChildItem -LiteralPath . -File -Force | Where-Object {
    $_.Name -in @('jacocoagent.jar','jacococli.jar','jacoco-cli.jar','jacoco-cli.jar')
  } | ForEach-Object {
    Remove-PathSafe $_.FullName
  }
}

Write-Host "Done." -ForegroundColor Cyan
Write-Host "Tip: if you plan to publish on GitHub, also ensure .env is gitignored." -ForegroundColor Gray
