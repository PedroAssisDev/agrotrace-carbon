import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut

from model_training_service.domain.errors import InsufficientDataError
from model_training_service.regression.trainer import ChronologicalHoldout, RegressionTrainer


def _rows(property_ids: list[str], months: int = 12) -> pd.DataFrame:
    rows = []
    for property_id in property_ids:
        for month in range(1, months + 1):
            cows = 20 + month
            rows.append(
                {
                    "property_id": property_id,
                    "period": pd.Timestamp(2024, month, 1) if month <= 12 else pd.Timestamp(2025, month - 12, 1),
                    "granularity": "monthly",
                    "lactating_cows": cows,
                    "milk_production_liters": cows * 700,
                }
            )
    return pd.DataFrame(rows)


def test_group_kfold_with_three_or_more_properties():
    data = _rows([f"farm-{i}" for i in range(3)])
    trainer = RegressionTrainer(
        {"feature": "lactating_cows", "min_records": 8, "max_cv_splits": 3, "random_state": 42},
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
    )
    cv, use_groups, strategy = trainer._build_cv(data)
    assert use_groups is True
    assert isinstance(cv, GroupKFold)
    assert strategy.startswith("group_kfold")


def test_leave_one_group_out_with_two_properties():
    data = _rows(["farm-a", "farm-b"])
    trainer = RegressionTrainer(
        {"feature": "lactating_cows", "min_records": 8, "max_cv_splits": 3, "random_state": 42},
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
    )
    cv, use_groups, strategy = trainer._build_cv(data)
    assert use_groups is True
    assert isinstance(cv, LeaveOneGroupOut)
    assert strategy == "leave_one_group_out"


def test_chronological_holdout_with_one_property_no_shuffle():
    data = _rows(["farm-only"], months=12)
    trainer = RegressionTrainer(
        {"feature": "lactating_cows", "min_records": 8, "max_cv_splits": 3, "random_state": 42},
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
    )
    cv, use_groups, strategy = trainer._build_cv(data)
    assert use_groups is False
    assert isinstance(cv, ChronologicalHoldout)
    assert strategy == "chronological_holdout"
    splits = list(cv.split(data))
    assert len(splits) == 1
    train_idx, test_idx = splits[0]
    assert train_idx.max() < test_idx.min()


def test_regression_uses_only_lactating_cows_in_x():
    data = _rows([f"farm-{i}" for i in range(3)])
    trainer = RegressionTrainer(
        {
            "feature": "lactating_cows",
            "min_records": 8,
            "max_cv_splits": 3,
            "random_state": 42,
            "candidate_profile": "core",
        },
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
    )
    result = trainer.train(data, "monthly", "milk_production_liters")
    assert result.feature_columns == ["lactating_cows"]
    assert list(result.training_data.columns) == [
        "property_id",
        "period",
        "lactating_cows",
        "milk_production_liters",
    ]


def test_insufficient_chronological_data_raises():
    data = _rows(["farm-only"], months=4)
    trainer = RegressionTrainer(
        {"feature": "lactating_cows", "min_records": 8, "max_cv_splits": 3, "random_state": 42},
        {"metric": "mae", "minimum_improvement_over_baseline": 0.0},
    )
    with pytest.raises(InsufficientDataError):
        trainer.train(data, "monthly", "milk_production_liters")
