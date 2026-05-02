param(
  [string]$RunId = "",
  [switch]$SkipPipeline,
  [string]$PipelineCommand = "python run_pipeline.py",
  [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
}

Push-Location $WorkspaceRoot
try {
  if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = (Get-Date -Format "yyyyMMdd_HHmmss")
  }

  $evalRoot = Join-Path $WorkspaceRoot "output\eval_runs"
  $runDir = Join-Path $evalRoot $RunId
  $metricsDir = Join-Path $evalRoot "metrics"
  $plotsDir = Join-Path $evalRoot "plots"
  New-Item -ItemType Directory -Force -Path $runDir | Out-Null
  New-Item -ItemType Directory -Force -Path $metricsDir | Out-Null
  New-Item -ItemType Directory -Force -Path $plotsDir | Out-Null

  $logPath = Join-Path $runDir "pipeline.log"
  $gtSeconds = $null

  if (-not $SkipPipeline) {
    Write-Host "Running pipeline: $PipelineCommand"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    # Use cmd.exe so complex commands work reliably.
    cmd.exe /c "$PipelineCommand" 2>&1 | Tee-Object -FilePath $logPath

    $sw.Stop()
    $gtSeconds = [Math]::Round($sw.Elapsed.TotalSeconds, 3)
    Write-Host "Pipeline duration (GT_seconds): $gtSeconds"
  } else {
    Write-Host "Skipping pipeline run (using existing output/ artifacts)."
  }

  $evalArgs = @(
    "tools/eval_metrics.py",
    "--run-id", $RunId,
    "--run-log", $logPath
  )
  if ($gtSeconds -ne $null) {
    $evalArgs += @("--gt-seconds", "$gtSeconds")
  }

  Write-Host "Computing metrics JSON..."
  python @evalArgs

  Write-Host "Generating plots..."
  python tools/plot_metrics.py --metrics-dir "output/eval_runs/metrics" --out-dir "output/eval_runs/plots"

  Write-Host "Done. Outputs:"
  Write-Host "- $metricsDir"
  Write-Host "- $plotsDir"
  Write-Host "- $runDir"
}
finally {
  Pop-Location
}
