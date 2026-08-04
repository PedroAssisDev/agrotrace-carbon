import numpy as np
import pandas as pd

from model_training_service.time_series.trainer import TimeSeriesTrainer


def test_time_series_is_univariate_and_horizon_is_three():
    periods = pd.date_range("2024-01-01", periods=24, freq="MS")
    data = pd.DataFrame(
        {
            "property_id": "farm-1",
            "period": periods,
            "granularity": "monthly",
            "lactating_cows": np.linspace(20, 30, 24),
            "milk_production_liters": 10_000 + np.arange(24) * 120,
        }
    )
    config = {
        "granularity": "monthly",
        "min_records": 12,
        "forecast_horizon": 3,
        "max_validation_folds": 3,
        "minimum_train_size": 8,
        "seasonal_period": 12,
        "enable_seasonal_models_from": 24,
    }
    result = TimeSeriesTrainer(
        config, {"metric": "mae", "minimum_improvement_over_baseline": 0.0}
    ).train(data, "farm-1", "milk_production_liters")
    assert result.training_series.columns.tolist() == [
        "property_id",
        "period",
        "milk_production_liters",
    ]
    assert result.selection_comparison["baseline_name"] == "naive"
    forecast = result.model.forecast(3)
    assert len(forecast) == 3
    assert np.isfinite(forecast).all()
