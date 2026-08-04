import sys
from pathlib import Path

import pandas as pd

from model_training_service.orchestration.training_service import ModelTrainingService


def test_lstm_disabled_does_not_import_tensorflow(tmp_path: Path):
    sys.modules.pop("tensorflow", None)
    before = set(sys.modules)

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
    }
    ModelTrainingService(config).run(pd.DataFrame(rows))
    assert "tensorflow" not in sys.modules
    assert "tensorflow" not in (set(sys.modules) - before)


def test_lstm_enabled_records_explicit_skip(tmp_path: Path):
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
            "enabled": False,
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
            "enable_lstm": True,
            "lstm_min_records": 36,
        },
    }
    report = ModelTrainingService(config).run(
        pd.DataFrame(
            [
                {
                    "property_id": "farm-1",
                    "period": "2024-01-01",
                    "granularity": "monthly",
                    "lactating_cows": 10,
                    "milk_production_liters": 1000,
                    "total_ghg_emissions_tco2e": 1.0,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            ]
        )
    )
    assert any(item["model"] == "time_series/lstm" for item in report["skipped"])
    assert "tensorflow" not in sys.modules
