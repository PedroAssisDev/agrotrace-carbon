from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np
import pandas as pd  # noqa: F401 — used throughout
from sklearn.base import clone
from sklearn.model_selection import (
    BaseCrossValidator,
    GridSearchCV,
    GroupKFold,
    LeaveOneGroupOut,
    cross_val_predict,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from model_training_service.domain.errors import CandidateTrainingError, InsufficientDataError
from model_training_service.evaluation.metrics import regression_metrics
from model_training_service.evaluation.selection import (
    REGRESSION_BASELINE,
    select_against_baseline,
    sklearn_scoring_name,
)
from model_training_service.regression.candidates import build_regression_candidates


@dataclass
class RegressionTrainingResult:
    model: Any
    selected_candidate: str
    selected_params: dict[str, Any]
    metrics: dict[str, float | None]
    candidate_results: list[dict[str, Any]]
    training_data: pd.DataFrame
    selection_comparison: dict[str, Any]
    validation_strategy: str
    feature_columns: list[str]


class ChronologicalHoldout(BaseCrossValidator):
    """Single chronological fold: train on prefix, validate on suffix. No shuffle."""

    def __init__(self, n_train: int) -> None:
        self.n_train = int(n_train)

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return 1

    def split(self, X, y=None, groups=None) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        n_samples = _n_samples(X)
        if self.n_train <= 0 or self.n_train >= n_samples:
            raise ValueError("Holdout cronológico inválido.")
        train_idx = np.arange(0, self.n_train)
        test_idx = np.arange(self.n_train, n_samples)
        yield train_idx, test_idx


def _n_samples(X) -> int:
    if hasattr(X, "shape"):
        return int(X.shape[0])
    return len(X)


class RegressionTrainer:
    def __init__(self, config: dict[str, Any], selection_config: dict[str, Any] | None = None) -> None:
        self.config = config
        self.selection_config = selection_config or {
            "metric": "mae",
            "minimum_improvement_over_baseline": 0.0,
        }

    def train(self, data: pd.DataFrame, granularity: str, target: str) -> RegressionTrainingResult:
        feature = self.config["feature"]
        if feature != "lactating_cows":
            raise ValueError("A regressão deve usar exclusivamente lactating_cows.")

        subset = data[data["granularity"].eq(granularity)][
            ["property_id", "period", feature, target]
        ].dropna().sort_values(["property_id", "period"]).reset_index(drop=True)

        minimum = int(self.config["min_records"])
        if len(subset) < minimum:
            raise InsufficientDataError(
                f"Regressão {granularity}/{target}: {len(subset)} registros; mínimo {minimum}."
            )

        feature_columns = [feature]
        X = subset[feature_columns].to_numpy(dtype=float)
        y = subset[target].to_numpy(dtype=float)
        groups = subset["property_id"].to_numpy()
        cv, use_groups, validation_strategy = self._build_cv(subset)
        random_state = int(self.config.get("random_state", 42))
        metric_name = str(self.selection_config.get("metric", "mae"))
        scoring = sklearn_scoring_name(metric_name)
        metric_key = f"cv_{metric_name}"

        candidate_results: list[dict[str, Any]] = []
        fitted_by_name: dict[str, Any] = {}
        params_by_name: dict[str, dict[str, Any]] = {}
        scores: dict[str, float] = {}

        for candidate in build_regression_candidates(
            random_state, len(subset), profile=self.config.get("candidate_profile", "core")
        ):
            steps = []
            if candidate.requires_scaling:
                steps.append(("scaler", StandardScaler()))
            steps.append(("model", candidate.estimator))
            pipeline = Pipeline(steps)
            param_grid = {f"model__{key}": value for key, value in candidate.param_grid.items()}
            search = GridSearchCV(
                pipeline,
                param_grid=param_grid or [{}],
                scoring=scoring,
                cv=cv,
                n_jobs=1,
                error_score=np.nan,
                refit=True,
            )
            try:
                if use_groups:
                    search.fit(X, y, groups=groups)
                else:
                    search.fit(X, y)
                score = float(-search.best_score_)
                if not np.isfinite(score):
                    raise ValueError(f"{metric_name} não finito")
                result = {
                    "candidate": candidate.name,
                    "status": "success",
                    metric_key: score,
                    "best_params": _strip_model_prefix(search.best_params_),
                }
                candidate_results.append(result)
                scores[candidate.name] = score
                fitted_by_name[candidate.name] = clone(search.best_estimator_)
                params_by_name[candidate.name] = result["best_params"]
            except Exception as exc:  # one failed candidate must not abort the experiment
                candidate_results.append(
                    {"candidate": candidate.name, "status": "failed", "reason": str(exc)}
                )

        if REGRESSION_BASELINE not in scores:
            raise CandidateTrainingError(
                f"Baseline '{REGRESSION_BASELINE}' falhou; regressão {granularity}/{target} ignorada."
            )

        decision = select_against_baseline(
            candidate_scores=scores,
            baseline_name=REGRESSION_BASELINE,
            metric_name=metric_name,
            minimum_improvement=float(
                self.selection_config.get("minimum_improvement_over_baseline", 0.0)
            ),
            family="regression",
        )
        best_name = decision.selected_candidate
        best_model = fitted_by_name[best_name]
        best_params = params_by_name[best_name]

        if use_groups:
            predictions = cross_val_predict(best_model, X, y, cv=cv, groups=groups, n_jobs=1)
        else:
            predictions = cross_val_predict(best_model, X, y, cv=cv, n_jobs=1)
        metrics = regression_metrics(y, predictions)
        best_model.fit(X, y)
        return RegressionTrainingResult(
            model=best_model,
            selected_candidate=best_name,
            selected_params=best_params,
            metrics=metrics,
            candidate_results=candidate_results,
            training_data=subset.reset_index(drop=True),
            selection_comparison=decision.as_dict(),
            validation_strategy=validation_strategy,
            feature_columns=feature_columns,
        )

    def _build_cv(self, data: pd.DataFrame):
        max_splits = int(self.config.get("max_cv_splits", 5))
        property_count = int(data["property_id"].nunique())
        min_records = int(self.config.get("min_records", 8))

        if property_count >= 3:
            splits = min(max_splits, property_count)
            return GroupKFold(n_splits=splits), True, f"group_kfold_{splits}"

        if property_count == 2:
            return LeaveOneGroupOut(), True, "leave_one_group_out"

        # Uma propriedade: holdout cronológico sem embaralhamento.
        ordered = data.sort_values("period").reset_index(drop=True)
        n = len(ordered)
        min_train = max(min_records // 2, 3)
        n_test = max(1, min(n // 5, n - min_train))
        n_train = n - n_test
        if n_train < min_train or n_test < 1:
            raise InsufficientDataError(
                "Não há registros suficientes para validação cronológica da regressão "
                f"(n={n}, min_train={min_train})."
            )
        # Reordenar data já está ordenada por property_id,period; para 1 prop basta period.
        # O subset passado a train() já foi ordenado; ChronologicalHoldout usa índices 0..n.
        return ChronologicalHoldout(n_train), False, "chronological_holdout"


def _strip_model_prefix(params: dict[str, Any]) -> dict[str, Any]:
    return {key.removeprefix("model__"): value for key, value in params.items()}
