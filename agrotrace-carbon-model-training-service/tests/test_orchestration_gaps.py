from pathlib import Path

import pandas as pd

from model_training_service.orchestration.training_service import ModelTrainingService


def _monthly_rows(property_id: str, periods, cows_base: int = 30) -> list[dict]:
    rows = []
    for index, period in enumerate(periods):
        cows = cows_base + (index % 3)
        rows.append(
            {
                "property_id": property_id,
                "period": period,
                "granularity": "monthly",
                "lactating_cows": cows,
                "milk_production_liters": cows * 680 + index * 10,
                "total_ghg_emissions_tco2e": cows * 0.4 + index * 0.01,
                "approval_status": "approved",
                "publication_status": "published",
            }
        )
    return rows


def test_skip_property_gap_keeps_regression_and_other_properties(tmp_path: Path):
    good_periods = pd.date_range("2024-01-01", periods=15, freq="MS")
    gapped_periods = list(pd.date_range("2024-01-01", periods=14, freq="MS"))
    # Remove one month to create a gap in farm-gap only.
    gapped_periods.pop(5)

    rows = []
    rows.extend(_monthly_rows("farm-good", good_periods, cows_base=30))
    rows.extend(_monthly_rows("farm-gap", gapped_periods, cows_base=40))
    for year in range(2018, 2026):
        for property_id, cows in (("farm-good", 35), ("farm-gap", 45)):
            rows.append(
                {
                    "property_id": property_id,
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
            "monthly_gap_policy": "skip_property",
        },
        "selection": {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
        "regression": {
            "enabled": True,
            "granularities": ["monthly", "annual"],
            "targets": ["milk_production_liters", "total_ghg_emissions_tco2e"],
            "feature": "lactating_cows",
            "scope": "global",
            "min_records": 8,
            "random_state": 42,
            "max_cv_splits": 2,
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
        "_meta": {"config_sha256": "skip-property-e2e"},
    }

    report = ModelTrainingService(config).run(
        pd.DataFrame(rows),
        data_source={"type": "csv", "location": str(tmp_path / "synthetic.csv")},
    )

    assert report["errors"] == []
    assert report["gap_policy"] == "skip_property"
    assert report["data_source"]["type"] == "csv"

    skipped_props = report["skipped_properties"]
    assert len(skipped_props) == 1
    assert skipped_props[0]["property_id"] == "farm-gap"
    assert skipped_props[0]["target"] == "milk_production_liters"
    assert "lacuna" in skipped_props[0]["reason"].lower() or "gap" in skipped_props[0][
        "reason"
    ].lower() or "ignorada" in skipped_props[0]["reason"].lower()

    regression_models = [m for m in report["models"] if m["model_family"] == "regression"]
    ts_models = [m for m in report["models"] if m["model_family"] == "time_series"]
    assert len(regression_models) == 4
    assert {m["property_id"] for m in ts_models} == {"farm-good"}
    assert len(ts_models) == 2
    assert all(m["feature_columns"] == ["lactating_cows"] for m in regression_models)
    assert all(m["forecast_horizon"] == 3 for m in ts_models)
    assert all("lactating_cows" not in (m.get("feature_schema") or []) for m in ts_models)
