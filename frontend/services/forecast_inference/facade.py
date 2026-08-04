"""Fachada única de inferência para callbacks do frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from services.forecast_inference.errors import ForecastInferenceError
from services.forecast_inference.loader import ArtifactCache, ModelArtifactLoader
from services.forecast_inference.logging_hooks import log_forecast_event, timed_forecast
from services.forecast_inference.registry import ModelRegistryReader
from services.forecast_inference.regression import RegressionInferenceService
from services.forecast_inference.time_series import TimeSeriesInferenceService


class PredictionFacade:
    def __init__(
        self,
        artifacts_dir: str | Path | None = None,
        registry_path: str | Path | None = None,
    ) -> None:
        root = Path(artifacts_dir or config.MODEL_TRAINING_ARTIFACTS_DIR)
        registry = Path(registry_path or config.MODEL_REGISTRY_PATH)
        self.registry = ModelRegistryReader(registry, artifacts_root=root)
        self.loader = ModelArtifactLoader(cache=ArtifactCache())
        self.regression = RegressionInferenceService(self.registry, self.loader)
        self.time_series = TimeSeriesInferenceService(self.registry, self.loader)

    def get_model_availability(self, property_id: str | None) -> dict[str, Any]:
        return self.registry.list_available_summary(property_id)

    def predict_regression_scenario(
        self,
        property_id: str,
        granularity: str,
        expected_lactating_cows: Any,
    ) -> dict[str, Any]:
        with timed_forecast() as timer:
            try:
                result = self.regression.predict(
                    property_id=property_id,
                    granularity=granularity,
                    expected_lactating_cows=expected_lactating_cows,
                )
                log_forecast_event(
                    forecast_type="regression",
                    property_id=property_id,
                    granularity=granularity,
                    expected_lactating_cows=result.get("expected_lactating_cows"),
                    model_ids={
                        "milk": result.get("milk_model_id"),
                        "emissions": result.get("emissions_model_id"),
                    },
                    success=True,
                    duration_seconds=timer.elapsed,
                )
                return result
            except ForecastInferenceError as exc:
                log_forecast_event(
                    forecast_type="regression",
                    property_id=property_id,
                    granularity=granularity,
                    expected_lactating_cows=None,
                    success=False,
                    duration_seconds=timer.elapsed,
                    error=str(exc),
                )
                raise

    def forecast_time_series(self, property_id: str) -> dict[str, Any]:
        with timed_forecast() as timer:
            try:
                result = self.time_series.forecast(property_id=property_id)
                log_forecast_event(
                    forecast_type="time_series",
                    property_id=property_id,
                    model_ids={
                        "milk": result.get("milk_model_id"),
                        "emissions": result.get("emissions_model_id"),
                    },
                    success=True,
                    duration_seconds=timer.elapsed,
                )
                return result
            except ForecastInferenceError as exc:
                log_forecast_event(
                    forecast_type="time_series",
                    property_id=property_id,
                    success=False,
                    duration_seconds=timer.elapsed,
                    error=str(exc),
                )
                raise


_default_facade: PredictionFacade | None = None


def get_prediction_facade() -> PredictionFacade:
    global _default_facade
    if _default_facade is None:
        _default_facade = PredictionFacade()
    return _default_facade
