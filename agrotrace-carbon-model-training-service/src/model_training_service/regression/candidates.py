from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sklearn.base import RegressorMixin
from sklearn.ensemble import (
    AdaBoostRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

from model_training_service.regression.baseline import MeanPerCowRegressor


@dataclass(frozen=True)
class RegressionCandidate:
    name: str
    estimator: RegressorMixin
    param_grid: dict[str, list[Any]]
    requires_scaling: bool = False


def build_regression_candidates(
    random_state: int,
    record_count: int,
    profile: str = "core",
) -> list[RegressionCandidate]:
    """Build the candidate catalogue.

    ``core`` is the default operational profile and keeps training time predictable.
    ``extended`` additionally enables the algorithms preserved from the original sketches.
    """
    core = [
        RegressionCandidate("mean_per_cow_baseline", MeanPerCowRegressor(), {}),
        RegressionCandidate("linear_regression", LinearRegression(), {}),
        RegressionCandidate("ridge", Ridge(), {"alpha": [0.1, 1.0, 10.0]}, True),
        RegressionCandidate(
            "svr",
            SVR(),
            {"C": [1.0, 10.0], "epsilon": [0.1, 1.0], "kernel": ["linear", "rbf"]},
            True,
        ),
        RegressionCandidate(
            "gradient_boosting",
            GradientBoostingRegressor(random_state=random_state),
            {"n_estimators": [50], "learning_rate": [0.05, 0.1], "max_depth": [2]},
        ),
        RegressionCandidate(
            "random_forest",
            RandomForestRegressor(random_state=random_state, n_jobs=1),
            {"n_estimators": [50], "max_depth": [None, 4], "min_samples_leaf": [1]},
        ),
    ]
    if profile == "core":
        return core
    if profile != "extended":
        raise ValueError(f"Perfil de candidatos não suportado: {profile}")

    max_neighbors = max(1, min(5, record_count // 3))
    neighbor_values = sorted({1, 2, max_neighbors})
    extended = [
        RegressionCandidate(
            "elastic_net",
            ElasticNet(max_iter=20_000, random_state=random_state),
            {"alpha": [0.01, 0.1], "l1_ratio": [0.1, 0.5, 0.9]},
            True,
        ),
        RegressionCandidate(
            "knn",
            KNeighborsRegressor(),
            {"n_neighbors": neighbor_values, "weights": ["uniform", "distance"], "p": [1, 2]},
            True,
        ),
        RegressionCandidate(
            "decision_tree",
            DecisionTreeRegressor(random_state=random_state),
            {"max_depth": [None, 2, 4], "min_samples_leaf": [1, 2]},
        ),
        RegressionCandidate(
            "adaboost",
            AdaBoostRegressor(random_state=random_state),
            {"n_estimators": [50, 100], "learning_rate": [0.1, 1.0]},
        ),
    ]
    return core + extended
