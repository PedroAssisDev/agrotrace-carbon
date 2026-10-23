#!/usr/bin/env bash
# Install all AgroTrace Carbon / AgroMRV-Flow projects into the active Python environment.
# Usage (from repo root, with venv activated):
#   ./tooling/install-workspace.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

projects=(
  agrotrace-carbon-save-file
  agrotrace-carbon-wrappers-service
  agrotrace-carbon-ontology-manager
  agrotrace-carbon-calculation-service
  agrotrace-carbon-model-training-service
  agrotrace-carbon-traceability-service
  agrotrace-carbon-blockchain-service
  frontend
)

for p in "${projects[@]}"; do
  echo "=== Installing $p ==="
  if [[ -f "$p/pyproject.toml" ]]; then
    if [[ "$p" == "frontend" ]]; then
      pip install -e "$p[dev]"
    elif [[ "$p" == "agrotrace-carbon-wrappers-service" ]]; then
      pip install -e "$p[test]"
    else
      pip install -e "$p"
      case "$p" in
        agrotrace-carbon-blockchain-service|agrotrace-carbon-model-training-service|agrotrace-carbon-traceability-service)
          pip install -e "$p[dev]" 2>/dev/null || true
          ;;
      esac
    fi
  elif [[ -f "$p/requirements.txt" ]]; then
    pip install -r "$p/requirements.txt"
  else
    echo "No install source for $p" >&2
    exit 1
  fi
done

pip check
echo "Workspace install complete."
