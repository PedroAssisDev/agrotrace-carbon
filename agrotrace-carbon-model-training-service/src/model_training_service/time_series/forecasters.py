from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing


class Forecaster(Protocol):
    def fit(self, values: np.ndarray) -> "Forecaster": ...
    def forecast(self, horizon: int) -> np.ndarray: ...


@dataclass
class NaiveForecaster:
    last_value: float | None = None

    def fit(self, values: np.ndarray):
        self.last_value = float(values[-1])
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.repeat(float(self.last_value), horizon)


@dataclass
class DriftForecaster:
    first_value: float | None = None
    last_value: float | None = None
    observation_count: int = 0

    def fit(self, values: np.ndarray):
        self.first_value = float(values[0])
        self.last_value = float(values[-1])
        self.observation_count = len(values)
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        slope = 0.0
        if self.observation_count > 1:
            slope = (float(self.last_value) - float(self.first_value)) / (self.observation_count - 1)
        steps = np.arange(1, horizon + 1, dtype=float)
        return float(self.last_value) + slope * steps


@dataclass
class MovingAverageForecaster:
    window: int = 3
    mean_value: float | None = None

    def fit(self, values: np.ndarray):
        used = values[-min(self.window, len(values)) :]
        self.mean_value = float(np.mean(used))
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.repeat(float(self.mean_value), horizon)


@dataclass
class SeasonalNaiveForecaster:
    seasonal_period: int = 12
    season: np.ndarray | None = None

    def fit(self, values: np.ndarray):
        if len(values) < self.seasonal_period:
            raise ValueError("Histórico insuficiente para naive sazonal.")
        self.season = np.asarray(values[-self.seasonal_period :], dtype=float)
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        assert self.season is not None
        return np.asarray([self.season[index % len(self.season)] for index in range(horizon)])


@dataclass
class SimpleExponentialSmoothingForecaster:
    result: object | None = None

    def fit(self, values: np.ndarray):
        self.result = SimpleExpSmoothing(values, initialization_method="estimated").fit(optimized=True)
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.asarray(self.result.forecast(horizon), dtype=float)


@dataclass
class HoltForecaster:
    damped: bool = False
    result: object | None = None

    def fit(self, values: np.ndarray):
        self.result = Holt(values, damped_trend=self.damped, initialization_method="estimated").fit(
            optimized=True
        )
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.asarray(self.result.forecast(horizon), dtype=float)


@dataclass
class ETSForecaster:
    seasonal_period: int = 12
    result: object | None = None

    def fit(self, values: np.ndarray):
        if len(values) < self.seasonal_period * 2:
            raise ValueError("ETS sazonal exige ao menos dois ciclos completos.")
        self.result = ExponentialSmoothing(
            values,
            trend="add",
            seasonal="add",
            seasonal_periods=self.seasonal_period,
            initialization_method="estimated",
        ).fit(optimized=True)
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.asarray(self.result.forecast(horizon), dtype=float)


@dataclass
class AutoRegForecaster:
    lags: int = 1
    result: object | None = None

    def fit(self, values: np.ndarray):
        if len(values) <= self.lags + 2:
            raise ValueError("Histórico insuficiente para AutoReg.")
        self.result = AutoReg(values, lags=self.lags, old_names=False, trend="ct").fit()
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        start = self.result.nobs
        end = start + horizon - 1
        return np.asarray(self.result.predict(start=start, end=end), dtype=float)


@dataclass
class ARIMAForecaster:
    order: tuple[int, int, int] = (1, 1, 0)
    result: object | None = None

    def fit(self, values: np.ndarray):
        self.result = ARIMA(values, order=self.order, trend=None).fit()
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        return np.asarray(self.result.forecast(horizon), dtype=float)
