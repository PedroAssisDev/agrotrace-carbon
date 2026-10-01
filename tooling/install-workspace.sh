#!/usr/bin/env bash
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
    pip install -e "$p"
  elif [[ -f "$p/requirements.txt" ]]; then
    pip install -r "$p/requirements.txt"
  else
    echo "No install source for $p" >&2
    exit 1
  fi
done

pip check
echo "Workspace install complete."
