# Install all AgroTrace Carbon projects into the active Python environment.
# Usage (from repo root, with venv activated):
#   .\scripts\install-workspace.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$projects = @(
  "agrotrace-carbon-save-file",
  "agrotrace-carbon-wrappers-service",
  "agrotrace-carbon-ontology-manager",
  "agrotrace-carbon-calculation-service",
  "agrotrace-carbon-model-training-service",
  "agrotrace-carbon-traceability-service",
  "agrotrace-carbon-blockchain-service",
  "frontend"
)

foreach ($p in $projects) {
  Write-Host "=== Installing $p ===" -ForegroundColor Cyan
  if (Test-Path "$p\pyproject.toml") {
    if ($p -eq "frontend") {
      pip install -e "$p[dev]"
    } elseif (Test-Path "$p\requirements.txt" -and $p -eq "agrotrace-carbon-wrappers-service") {
      pip install -e "$p[test]"
    } else {
      pip install -e "$p"
      if ($p -match "blockchain|model-training|traceability") {
        pip install -e "$p[dev]" 2>$null
      }
    }
  } elseif (Test-Path "$p\requirements.txt") {
    pip install -r "$p\requirements.txt"
  } else {
    Write-Error "No install source for $p"
  }
}

pip check
Write-Host "Workspace install complete." -ForegroundColor Green
