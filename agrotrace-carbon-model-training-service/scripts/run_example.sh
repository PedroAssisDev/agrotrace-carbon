#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH=src python -m model_training_service.cli train-all \
  --csv examples/approved_results.csv \
  --config configs/training.yaml
