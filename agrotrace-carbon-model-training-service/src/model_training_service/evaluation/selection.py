"""Seleção de modelos com política explícita contra baseline.

Tolerância de ponto fluttuante: 0.0 (comparações estritas; sem epsilon oculto).
Métricas suportadas: mae, rmse (menor é melhor).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Documentado: melhoria exige comparação estrita sem tolerância oculta.
FLOAT_COMPARISON_TOLERANCE = 0.0

REGRESSION_COMPLEXITY: dict[str, int] = {
    "mean_per_cow_baseline": 0,
    "linear_regression": 1,
    "ridge": 2,
    "svr": 3,
    "gradient_boosting": 4,
    "random_forest": 5,
    "elastic_net": 6,
    "knn": 7,
    "decision_tree": 8,
    "adaboost": 9,
}

TIME_SERIES_COMPLEXITY: dict[str, int] = {
    "naive": 0,
    "drift": 1,
    "moving_average_3": 2,
    "simple_exponential_smoothing": 3,
    "holt": 4,
    "holt_damped": 5,
    "autoreg_1": 6,
    "autoreg_3": 7,
    "arima_100": 8,
    "arima_010": 9,
    "arima_110": 10,
    "arima_011": 11,
    "seasonal_naive": 12,
    "ets_additive": 13,
}

REGRESSION_BASELINE = "mean_per_cow_baseline"
TIME_SERIES_BASELINE = "naive"


@dataclass(frozen=True)
class SelectionDecision:
    selected_candidate: str
    baseline_name: str
    baseline_metric: float
    winner_metric: float
    absolute_improvement: float
    percent_improvement: float | None
    selection_reason: str
    metric_name: str
    minimum_improvement_over_baseline: float
    float_comparison_tolerance: float = FLOAT_COMPARISON_TOLERANCE

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_candidate": self.selected_candidate,
            "baseline_name": self.baseline_name,
            "baseline_metric": self.baseline_metric,
            "winner_metric": self.winner_metric,
            "absolute_improvement": self.absolute_improvement,
            "percent_improvement": self.percent_improvement,
            "selection_reason": self.selection_reason,
            "metric_name": self.metric_name,
            "minimum_improvement_over_baseline": self.minimum_improvement_over_baseline,
            "float_comparison_tolerance": self.float_comparison_tolerance,
        }


def complexity_rank(name: str, family: str) -> int:
    table = REGRESSION_COMPLEXITY if family == "regression" else TIME_SERIES_COMPLEXITY
    return table.get(name, 100)


def select_against_baseline(
    *,
    candidate_scores: dict[str, float],
    baseline_name: str,
    metric_name: str,
    minimum_improvement: float,
    family: str,
) -> SelectionDecision:
    """Select the winner using an explicit baseline gate.

    A non-baseline candidate wins only when its metric is strictly better than
    ``baseline_metric - minimum_improvement`` (with tolerance 0.0).
    Ties prefer the simpler model.
    """
    if baseline_name not in candidate_scores:
        raise ValueError(
            f"Baseline '{baseline_name}' não treinou com sucesso; seleção abortada."
        )

    baseline_metric = float(candidate_scores[baseline_name])
    threshold = baseline_metric - float(minimum_improvement)

    eligible: list[tuple[str, float]] = [(baseline_name, baseline_metric)]
    for name, score in candidate_scores.items():
        if name == baseline_name:
            continue
        # Strict improvement: score < threshold (FLOAT_COMPARISON_TOLERANCE = 0.0).
        if score < threshold:
            eligible.append((name, float(score)))

    eligible.sort(key=lambda item: (item[1], complexity_rank(item[0], family)))
    winner_name, winner_metric = eligible[0]
    absolute_improvement = baseline_metric - winner_metric
    percent_improvement = None
    if abs(baseline_metric) > FLOAT_COMPARISON_TOLERANCE:
        percent_improvement = (absolute_improvement / abs(baseline_metric)) * 100.0

    if winner_name == baseline_name:
        reason = (
            f"Baseline '{baseline_name}' selecionado: nenhum candidato complexo "
            f"melhorou {metric_name} além de {minimum_improvement} "
            f"(tolerância={FLOAT_COMPARISON_TOLERANCE})."
        )
    else:
        reason = (
            f"Candidato '{winner_name}' selecionado: {metric_name}={winner_metric} "
            f"melhorou o baseline '{baseline_name}'={baseline_metric} "
            f"(delta_abs={absolute_improvement}, melhoria mínima={minimum_improvement})."
        )

    return SelectionDecision(
        selected_candidate=winner_name,
        baseline_name=baseline_name,
        baseline_metric=baseline_metric,
        winner_metric=winner_metric,
        absolute_improvement=absolute_improvement,
        percent_improvement=percent_improvement,
        selection_reason=reason,
        metric_name=metric_name,
        minimum_improvement_over_baseline=float(minimum_improvement),
    )


def sklearn_scoring_name(metric: str) -> str:
    if metric == "mae":
        return "neg_mean_absolute_error"
    if metric == "rmse":
        return "neg_root_mean_squared_error"
    raise ValueError(f"Métrica não suportada para scoring sklearn: {metric}")
