import pandas as pd
import pytest

from model_training_service.domain.errors import DataValidationError
from model_training_service.time_series.trainer import PropertySkippedError, TimeSeriesTrainer


def _contiguous(property_id: str = "farm-1", n: int = 15) -> pd.DataFrame:
    periods = pd.date_range("2024-01-01", periods=n, freq="MS")
    return pd.DataFrame(
        {
            "property_id": property_id,
            "period": periods,
            "granularity": "monthly",
            "lactating_cows": range(20, 20 + n),
            "milk_production_liters": [10_000 + i * 100 for i in range(n)],
        }
    )


def _gapped() -> pd.DataFrame:
    data = _contiguous(n=14)
    return data.drop(index=[5]).reset_index(drop=True)


def _ts_config():
    return {
        "granularity": "monthly",
        "min_records": 12,
        "forecast_horizon": 3,
        "max_validation_folds": 2,
        "minimum_train_size": 8,
        "seasonal_period": 12,
        "enable_seasonal_models_from": 24,
    }


def test_gap_policy_reject_raises():
    trainer = TimeSeriesTrainer(
        _ts_config(),
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
        monthly_gap_policy="reject",
    )
    with pytest.raises(DataValidationError):
        trainer.train(_gapped(), "farm-1", "milk_production_liters")


def test_gap_policy_skip_property_raises_property_skipped():
    trainer = TimeSeriesTrainer(
        _ts_config(),
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
        monthly_gap_policy="skip_property",
    )
    with pytest.raises(PropertySkippedError):
        trainer.train(_gapped(), "farm-1", "milk_production_liters")


def test_contiguous_series_trains():
    trainer = TimeSeriesTrainer(
        _ts_config(),
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
        monthly_gap_policy="reject",
    )
    result = trainer.train(_contiguous(), "farm-1", "milk_production_liters")
    assert result.selection_comparison["baseline_name"] == "naive"
    assert "lactating_cows" not in result.training_series.columns
