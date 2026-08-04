from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings

import numpy as np
import pandas as pd

from model_training_service.data.validation import assert_monthly_series_is_contiguous
from model_training_service.domain.errors import (
    CandidateTrainingError,
    DataValidationError,
    InsufficientDataError,
    ModelTrainingError,
)
from model_training_service.evaluation.metrics import regression_metrics
from model_training_service.evaluation.selection import (
    TIME_SERIES_BASELINE,
    select_against_baseline,
)
from model_training_service.evaluation.temporal import build_temporal_folds
from model_training_service.time_series.candidates import build_time_series_candidates


@dataclass
class TimeSeriesTrainingResult:
    model: Any
    selected_candidate: str
    metrics: dict[str, float | None]
    candidate_results: list[dict[str, Any]]
    training_series: pd.DataFrame
    validation_predictions: pd.DataFrame
    selection_comparison: dict[str, Any]
    validation_strategy: str


class PropertySkippedError(ModelTrainingError):
    """Raised when monthly_gap_policy=skip_property encounters gaps."""


class TimeSeriesTrainer:
    def __init__(
        self,
        config: dict[str, Any],
        selection_config: dict[str, Any] | None = None,
        monthly_gap_policy: str = "reject",
    ) -> None:
        self.config = config
        self.selection_config = selection_config or {
            "metric": "mae",
            "minimum_improvement_over_baseline": 0.0,
        }
        self.monthly_gap_policy = monthly_gap_policy

    def train(
        self, property_data: pd.DataFrame, property_id: str, target: str
    ) -> TimeSeriesTrainingResult:
        subset = (
            property_data[property_data["granularity"].eq(self.config["granularity"])][
                ["property_id", "period", target]
            ]
            .dropna()
            .sort_values("period")
            .reset_index(drop=True)
        )

        minimum = int(self.config["min_records"])
        if len(subset) < minimum:
            raise InsufficientDataError(
                f"Série temporal {property_id}/{target}: {len(subset)} registros; mínimo {minimum}."
            )

        try:
            assert_monthly_series_is_contiguous(subset)
        except DataValidationError as exc:
            if self.monthly_gap_policy == "skip_property":
                raise PropertySkippedError(
                    f"Lacunas mensais em {property_id}; propriedade ignorada ({exc})."
                ) from exc
            raise

        values = subset[target].to_numpy(dtype=float)
        horizon = int(self.config["forecast_horizon"])
        folds = build_temporal_folds(
            observation_count=len(values),
            horizon=horizon,
            minimum_train_size=int(self.config["minimum_train_size"]),
            max_folds=int(self.config["max_validation_folds"]),
        )
        if not folds:
            raise InsufficientDataError(
                f"Não há dados suficientes para validar horizonte {horizon} em {property_id}/{target}."
            )

        candidates = build_time_series_candidates(
            record_count=len(values),
            seasonal_period=int(self.config["seasonal_period"]),
            enable_seasonal_models_from=int(self.config["enable_seasonal_models_from"]),
        )
        metric_name = str(self.selection_config.get("metric", "mae"))
        candidate_results: list[dict[str, Any]] = []
        scores: dict[str, float] = {}
        factories: dict[str, Any] = {}
        predictions_by_name: dict[str, pd.DataFrame] = {}

        for candidate in candidates:
            actual_values: list[float] = []
            predicted_values: list[float] = []
            fold_rows: list[dict[str, Any]] = []
            try:
                for fold_index, fold in enumerate(folds, start=1):
                    train_values = values[: fold.train_end]
                    test_values = values[fold.train_end : fold.test_end]
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = candidate.factory().fit(train_values)
                        predictions = np.asarray(model.forecast(len(test_values)), dtype=float)
                    if len(predictions) != len(test_values) or not np.isfinite(predictions).all():
                        raise ValueError("O candidato gerou previsões inválidas.")
                    actual_values.extend(test_values.tolist())
                    predicted_values.extend(predictions.tolist())
                    periods = subset.iloc[fold.train_end : fold.test_end]["period"].tolist()
                    for period, actual, predicted in zip(
                        periods, test_values, predictions, strict=True
                    ):
                        fold_rows.append(
                            {
                                "fold": fold_index,
                                "period": period,
                                "actual": float(actual),
                                "predicted": float(predicted),
                            }
                        )
                metrics = regression_metrics(actual_values, predicted_values)
                score_raw = metrics.get(metric_name)
                if score_raw is None or not np.isfinite(float(score_raw)):
                    raise ValueError(f"Métrica {metric_name} inválida.")
                score = float(score_raw)
                candidate_results.append(
                    {"candidate": candidate.name, "status": "success", **metrics}
                )
                scores[candidate.name] = score
                factories[candidate.name] = candidate.factory
                predictions_by_name[candidate.name] = pd.DataFrame(fold_rows)
            except Exception as exc:
                candidate_results.append(
                    {"candidate": candidate.name, "status": "failed", "reason": str(exc)}
                )

        if TIME_SERIES_BASELINE not in scores:
            raise CandidateTrainingError(
                f"Baseline '{TIME_SERIES_BASELINE}' falhou; série {property_id}/{target} ignorada."
            )

        decision = select_against_baseline(
            candidate_scores=scores,
            baseline_name=TIME_SERIES_BASELINE,
            metric_name=metric_name,
            minimum_improvement=float(
                self.selection_config.get("minimum_improvement_over_baseline", 0.0)
            ),
            family="time_series",
        )
        best_name = decision.selected_candidate
        best_factory = factories[best_name]
        best_predictions = predictions_by_name[best_name]
        selected_result = next(
            result
            for result in candidate_results
            if result.get("candidate") == best_name and result.get("status") == "success"
        )
        selected_metrics = {
            key: selected_result.get(key) for key in ["mae", "rmse", "r2", "mape"]
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            final_model = best_factory().fit(values)
        return TimeSeriesTrainingResult(
            model=final_model,
            selected_candidate=best_name,
            metrics=selected_metrics,
            candidate_results=candidate_results,
            training_series=subset.reset_index(drop=True),
            validation_predictions=best_predictions,
            selection_comparison=decision.as_dict(),
            validation_strategy="temporal_expanding_origin",
        )
