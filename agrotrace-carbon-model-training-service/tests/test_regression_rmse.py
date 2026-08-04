from pathlib import Path

import pandas as pd

from model_training_service.regression.trainer import RegressionTrainer


def test_regression_trainer_selects_by_rmse():
    rows = []
    for property_index in range(3):
        for month in range(1, 10):
            cows = 20 + property_index * 5 + month
            rows.append(
                {
                    "property_id": f"farm-{property_index}",
                    "period": pd.Timestamp(2025, month, 1),
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 700 + property_index * 40,
                }
            )
    data = pd.DataFrame(rows)
    trainer = RegressionTrainer(
        {
            "feature": "lactating_cows",
            "min_records": 8,
            "random_state": 42,
            "max_cv_splits": 3,
            "candidate_profile": "core",
        },
        {"metric": "rmse", "minimum_improvement_over_baseline": 0.0},
    )
    result = trainer.train(data, "monthly", "milk_production_liters")

    assert result.selection_comparison["metric_name"] == "rmse"
    assert result.feature_columns == ["lactating_cows"]
    successful = [
        item for item in result.candidate_results if item.get("status") == "success"
    ]
    assert successful
    assert all("cv_rmse" in item for item in successful)
    assert all("cv_mae" not in item for item in successful)
    # MAE continua disponível nas métricas finais agregadas do vencedor.
    assert "mae" in result.metrics
    assert "rmse" in result.metrics
    assert result.selection_comparison["selected_candidate"] == result.selected_candidate
