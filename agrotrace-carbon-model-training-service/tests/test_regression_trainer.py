import numpy as np
import pandas as pd

from model_training_service.regression.trainer import RegressionTrainer


def test_regression_uses_only_lactating_cows_and_trains():
    rows = []
    for property_index in range(4):
        for month in range(1, 9):
            cows = 20 + property_index * 5 + month
            rows.append(
                {
                    "property_id": f"farm-{property_index}",
                    "period": pd.Timestamp(2025, month, 1),
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 700 + property_index * 50,
                }
            )
    data = pd.DataFrame(rows)
    config = {
        "feature": "lactating_cows",
        "min_records": 8,
        "random_state": 42,
        "max_cv_splits": 3,
        "candidate_profile": "core",
    }
    result = RegressionTrainer(
        config, {"metric": "mae", "minimum_improvement_over_baseline": 0.0}
    ).train(data, "monthly", "milk_production_liters")
    assert result.training_data.columns.tolist() == [
        "property_id",
        "period",
        "lactating_cows",
        "milk_production_liters",
    ]
    assert result.selection_comparison["baseline_name"] == "mean_per_cow_baseline"
    prediction = result.model.predict(np.array([[40.0]]))
    assert prediction.shape == (1,)
    assert result.metrics["mae"] >= 0
