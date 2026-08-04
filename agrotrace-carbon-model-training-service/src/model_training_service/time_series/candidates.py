from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from model_training_service.time_series.forecasters import (
    ARIMAForecaster,
    AutoRegForecaster,
    DriftForecaster,
    ETSForecaster,
    HoltForecaster,
    MovingAverageForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
    SimpleExponentialSmoothingForecaster,
)


@dataclass(frozen=True)
class TimeSeriesCandidate:
    name: str
    factory: Callable[[], object]


def build_time_series_candidates(
    record_count: int,
    seasonal_period: int,
    enable_seasonal_models_from: int,
) -> list[TimeSeriesCandidate]:
    candidates = [
        TimeSeriesCandidate("naive", NaiveForecaster),
        TimeSeriesCandidate("drift", DriftForecaster),
        TimeSeriesCandidate("moving_average_3", lambda: MovingAverageForecaster(window=3)),
        TimeSeriesCandidate("simple_exponential_smoothing", SimpleExponentialSmoothingForecaster),
        TimeSeriesCandidate("holt", lambda: HoltForecaster(damped=False)),
        TimeSeriesCandidate("holt_damped", lambda: HoltForecaster(damped=True)),
        TimeSeriesCandidate("autoreg_1", lambda: AutoRegForecaster(lags=1)),
        TimeSeriesCandidate("autoreg_3", lambda: AutoRegForecaster(lags=3)),
        TimeSeriesCandidate("arima_100", lambda: ARIMAForecaster(order=(1, 0, 0))),
        TimeSeriesCandidate("arima_010", lambda: ARIMAForecaster(order=(0, 1, 0))),
        TimeSeriesCandidate("arima_110", lambda: ARIMAForecaster(order=(1, 1, 0))),
        TimeSeriesCandidate("arima_011", lambda: ARIMAForecaster(order=(0, 1, 1))),
    ]
    if record_count >= enable_seasonal_models_from:
        candidates.extend(
            [
                TimeSeriesCandidate(
                    "seasonal_naive", lambda: SeasonalNaiveForecaster(seasonal_period)
                ),
                TimeSeriesCandidate("ets_additive", lambda: ETSForecaster(seasonal_period)),
            ]
        )
    return candidates
