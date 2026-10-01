#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python tooling/verify_no_active_legacy.py || echo "WARN: legacy markers remain"

(cd agrotrace-carbon-save-file && python -m unittest discover -s tests -q)
(cd agrotrace-carbon-wrappers-service && python -m pytest -q --tb=line)
(cd agrotrace-carbon-ontology-manager && python -m pytest -q --tb=line)
(cd agrotrace-carbon-calculation-service && python -m pytest -q --tb=line)
(cd agrotrace-carbon-model-training-service && python -m pytest -q --tb=line)
(cd agrotrace-carbon-traceability-service && python -m pytest -q --tb=line)
(cd agrotrace-carbon-blockchain-service && python -m pytest tests/ -m "not blockchain_local and not sepolia" -q --tb=line)
(cd frontend && python -m pytest tests/ -q --tb=line)

echo "test-workspace OK"
