import json
from pathlib import Path

import pandas as pd

from model_training_service.orchestration.training_service import ModelTrainingService


def test_artifacts_schema_and_materialized_datasets(tmp_path: Path):
    rows = []
    for farm in range(3):
        for period_index, period in enumerate(pd.date_range("2024-01-01", periods=14, freq="MS")):
            cows = 30 + farm + period_index
            rows.append(
                {
                    "property_id": f"farm-{farm}",
                    "period": period,
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 680,
                    "total_ghg_emissions_tco2e": cows * 0.4,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )
        for year in range(2018, 2024):
            cows = 40 + farm
            rows.append(
                {
                    "property_id": f"farm-{farm}",
                    "period": f"{year}-01-01",
                    "granularity": "annual",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 8000,
                    "total_ghg_emissions_tco2e": cows * 5.0,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )

    config = {
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
            "granularities": ["monthly", "annual"],
            "targets": ["milk_production_liters"],
            "feature": "lactating_cows",
            "scope": "global",
            "min_records": 8,
            "random_state": 42,
            "max_cv_splits": 3,
            "candidate_profile": "core",
        },
        "time_series": {
            "enabled": True,
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
        "_meta": {"config_sha256": "schema-test"},
    }
    report = ModelTrainingService(config).run(pd.DataFrame(rows))
    assert report["datasets"]["monthly_global"]
    assert report["datasets"]["annual_global"]
    assert any(key.startswith("audit_only:annual:") for key in report["datasets"])
    assert (tmp_path / "processed" / "annual" / "properties").exists()

    model = report["models"][0]
    artifact_dir = Path(model["artifact_dir"])
    metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((artifact_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert "sha256" in manifest
    assert "row_count" in manifest
    assert "traceability" in metadata
    assert "selection_comparison" in metadata
    assert "skipped" in report
    assert "gap_policy" in report
