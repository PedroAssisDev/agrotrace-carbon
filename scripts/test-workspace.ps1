# Run per-project tests + legacy verifier + quick regression.
# Usage: .\scripts\test-workspace.ps1
# Does not alter operational frontend/data (uses temp AGROTRACE_DATA_ROOT via regression).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python scripts/verify_no_active_legacy.py
if ($LASTEXITCODE -ne 0) { Write-Warning "Legacy verifier reported active markers" }

$suites = @(
  @{ Name = "save-file"; Dir = "agrotrace-carbon-save-file"; Cmd = "python -m unittest discover -s tests -q" },
  @{ Name = "wrappers"; Dir = "agrotrace-carbon-wrappers-service"; Cmd = "python -m pytest -q --tb=line" },
  @{ Name = "ontology"; Dir = "agrotrace-carbon-ontology-manager"; Cmd = "python -m pytest -q --tb=line" },
  @{ Name = "calculation"; Dir = "agrotrace-carbon-calculation-service"; Cmd = "python -m pytest -q --tb=line" },
  @{ Name = "model-training"; Dir = "agrotrace-carbon-model-training-service"; Cmd = "python -m pytest -q --tb=line" },
  @{ Name = "traceability"; Dir = "agrotrace-carbon-traceability-service"; Cmd = "python -m pytest -q --tb=line" },
  @{ Name = "blockchain"; Dir = "agrotrace-carbon-blockchain-service"; Cmd = "python -m pytest tests/ -m `"not blockchain_local and not sepolia`" -q --tb=line" }
)

$failed = 0
foreach ($s in $suites) {
  Write-Host "=== $($s.Name) ===" -ForegroundColor Cyan
  Push-Location $s.Dir
  try {
    Invoke-Expression $s.Cmd
    if ($LASTEXITCODE -ne 0) { $failed++ }
  } finally {
    Pop-Location
  }
}

Write-Host "=== frontend tests ===" -ForegroundColor Cyan
Push-Location frontend
python -m pytest tests/ -q --tb=line
if ($LASTEXITCODE -ne 0) { $failed++ }
Pop-Location

if ($failed -gt 0) {
  Write-Error "test-workspace failed ($failed suites)"
  exit 1
}
Write-Host "test-workspace OK" -ForegroundColor Green
