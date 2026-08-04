from pathlib import Path

import pandas as pd

from model_training_service.orchestration.training_service import ModelTrainingService


def test_full_training_service_generates_artifacts(tmp_path: Path):
    rows = []
    for farm_index in range(3):
        for period_index, period in enumerate(pd.date_range("2024-01-01", periods=15, freq="MS")):
            cows = 30 + farm_index * 4 + (period_index % 3)
            rows.append(
                {
                    "property_id": f"farm-{farm_index}",
                    "period": period,
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 680 + period_index * 30,
                    "total_ghg_emissions_tco2e": cows * 0.42 + period_index * 0.01,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )
        for year in range(2018, 2026):
            cows = 35 + farm_index * 3 + (year - 2018)
            rows.append(
                {
                    "property_id": f"farm-{farm_index}",
                    "period": f"{year}-01-01",
                    "granularity": "annual",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 8_100,
                    "total_ghg_emissions_tco2e": cows * 5.2,
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
        "selection": {
            "metric": "mae",
            "minimum_improvement_over_baseline": 0.0,
        },
        "regression": {
            "enabled": True,
            "granularities": ["monthly", "annual"],
            "targets": ["milk_production_liters", "total_ghg_emissions_tco2e"],
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
            "targets": ["milk_production_liters", "total_ghg_emissions_tco2e"],
            "min_records": 12,
            "forecast_horizon": 3,
            "max_validation_folds": 2,
            "minimum_train_size": 8,
            "seasonal_period": 12,
            "enable_seasonal_models_from": 24,
            "enable_lstm": False,
            "lstm_min_records": 36,
        },
        "_meta": {"config_sha256": "test-full"},
    }
    report = ModelTrainingService(config).run(pd.DataFrame(rows))
    assert not report["errors"]
    assert len(report["models"]) == 10  # 4 regressões + 3 propriedades x 2 séries
    assert (tmp_path / "artifacts" / "registry.jsonl").exists()
    assert (tmp_path / "artifacts" / "training_environment.json").exists()
    assert (tmp_path / "artifacts" / "resolved_config.json").exists()
    assert "duration_seconds" in report
    assert report["gap_policy"] == "reject"
