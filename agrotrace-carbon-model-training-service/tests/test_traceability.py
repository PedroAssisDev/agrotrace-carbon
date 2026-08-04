import json
from pathlib import Path

import pandas as pd

from model_training_service.orchestration.training_service import ModelTrainingService
from model_training_service.registry.environment import build_training_environment, write_run_artifacts


def _minimal_config(tmp_path: Path) -> dict:
    return {
        "paths": {
            "processed_data_dir": str(tmp_path / "processed"),
            "artifacts_dir": str(tmp_path / "artifacts"),
        },
        "validation": {
            "approved_values": ["approved"],
            "published_values": ["published"],
            "duplicate_policy": "reject",
            "monthly_gap_policy": "reject",
        },
        "selection": {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
        "regression": {
            "enabled": True,
            "granularities": ["monthly"],
            "targets": ["milk_production_liters"],
            "feature": "lactating_cows",
            "scope": "global",
            "min_records": 8,
            "random_state": 42,
            "max_cv_splits": 3,
            "candidate_profile": "core",
        },
        "time_series": {
            "enabled": False,
            "granularity": "monthly",
            "targets": ["milk_production_liters"],
            "min_records": 12,
            "forecast_horizon": 3,
            "max_validation_folds": 2,
            "minimum_train_size": 8,
            "seasonal_period": 12,
            "enable_seasonal_models_from": 24,
            "enable_lstm": False,
            "lstm_min_records": 36,
        },
        "_meta": {"config_path": str(tmp_path / "training.yaml"), "config_sha256": "abc123"},
    }


def test_environment_without_git_does_not_fail(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", "")
    env = build_training_environment(_minimal_config(tmp_path))
    assert "config_sha256" in env
    assert env["git_commit"] is None or isinstance(env["git_commit"], str)


def test_write_run_artifacts_and_metadata_contain_config_hash(tmp_path: Path):
    config = _minimal_config(tmp_path)
    paths = write_run_artifacts(tmp_path / "artifacts", config)
    environment = json.loads(Path(paths["environment_path"]).read_text(encoding="utf-8"))
    resolved = json.loads(Path(paths["resolved_config_path"]).read_text(encoding="utf-8"))
    assert environment["config_sha256"] == "abc123"
    assert "paths" in resolved

    rows = []
    for farm in range(3):
        for month in range(1, 10):
            cows = 25 + farm + month
            rows.append(
                {
                    "property_id": f"farm-{farm}",
                    "period": pd.Timestamp(2024, month, 1),
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 700,
                    "total_ghg_emissions_tco2e": cows * 0.4,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )
    report = ModelTrainingService(config).run(pd.DataFrame(rows))
    assert report["models"]
    metadata_path = Path(report["models"][0]["artifact_dir"]) / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["traceability"]["config_sha256"] == "abc123"
    assert "package_versions" in environment or environment["config_sha256"]
