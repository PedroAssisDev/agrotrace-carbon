"""Inferência de séries temporais mensais por propriedade."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from services.forecast_inference.errors import (
    ModelNotFoundError,
    OutOfDomainPredictionError,
)
from services.forecast_inference.loader import ModelArtifactLoader
from services.forecast_inference.period import next_periods_monthly
from services.forecast_inference.registry import ModelRegistryReader

TARGETS = ("milk_production_liters", "total_ghg_emissions_tco2e")
HORIZON = 3


class TimeSeriesInferenceService:
    def __init__(self, registry: ModelRegistryReader, loader: ModelArtifactLoader) -> None:
        self.registry = registry
        self.loader = loader

    def forecast(self, *, property_id: str) -> dict[str, Any]:
        if not property_id or not str(property_id).strip():
            raise ModelNotFoundError("Propriedade não informada para projeção temporal.")

        predictions: dict[str, list[float] | None] = {}
        histories: dict[str, list[dict[str, Any]]] = {}
        model_meta: dict[str, Any] = {}
        warnings: list[str] = []
        periods: list[str] = []

        for target in TARGETS:
            try:
                entry = self.registry.find_latest(
                    model_family="time_series",
                    model_scope="property",
                    granularity="monthly",
                    target=target,
                    property_id=str(property_id),
                    forecast_horizon=HORIZON,
                )
                artifact = self.loader.load(entry, expect_family="time_series")
                values = _forecast_values(artifact.model, HORIZON)
                predictions[target] = values
                model_meta[target] = {
                    "model_id": artifact.metadata.get("model_id"),
                    "version": artifact.metadata.get("version"),
                    "selected_candidate": artifact.metadata.get("selected_candidate"),
                    "metrics": (artifact.metrics or {}).get("selected") or {},
                    "manifest": {
                        "row_count": artifact.manifest.get("row_count"),
                        "period_start": artifact.manifest.get("period_start"),
                        "period_end": artifact.manifest.get("period_end"),
                    },
                    "created_at": artifact.metadata.get("created_at"),
                    "forecast_horizon": artifact.metadata.get("forecast_horizon"),
                }
                histories[target] = _series_history(artifact.history, target)
                if not periods:
                    periods = next_periods_monthly(artifact.history, HORIZON)
            except (ModelNotFoundError, OutOfDomainPredictionError) as exc:
                predictions[target] = None
                warnings.append(f"{target}: {exc}")
            except Exception as exc:  # noqa: BLE001
                predictions[target] = None
                warnings.append(f"{target}: {exc}")

        if all(v is None for v in predictions.values()):
            raise ModelNotFoundError(
                "Ainda não há histórico mensal suficiente para gerar a projeção desta propriedade."
            )
        if not periods:
            periods = [f"M+{i}" for i in range(1, HORIZON + 1)]

        return {
            "property_id": property_id,
            "forecast_horizon": HORIZON,
            "periods": periods,
            "milk_predictions": predictions.get("milk_production_liters"),
            "emission_predictions": predictions.get("total_ghg_emissions_tco2e"),
            "milk_model_id": (model_meta.get("milk_production_liters") or {}).get("model_id"),
            "emissions_model_id": (model_meta.get("total_ghg_emissions_tco2e") or {}).get("model_id"),
            "milk_model_version": (model_meta.get("milk_production_liters") or {}).get("version"),
            "emissions_model_version": (model_meta.get("total_ghg_emissions_tco2e") or {}).get(
                "version"
            ),
            "models": model_meta,
            "history": histories,
            "warnings": warnings,
        }


def _forecast_values(model: Any, horizon: int) -> list[float]:
    if not hasattr(model, "forecast"):
        raise OutOfDomainPredictionError("Modelo temporal sem método forecast.")
    raw = np.asarray(model.forecast(horizon), dtype=float).ravel()
    if len(raw) != horizon:
        raise OutOfDomainPredictionError(
            f"Horizonte esperado {horizon}; recebido {len(raw)}."
        )
    values: list[float] = []
    for item in raw:
        value = float(item)
        if not np.isfinite(value):
            raise OutOfDomainPredictionError("Previsão temporal não numérica ou infinita.")
        if value < 0:
            raise OutOfDomainPredictionError("Previsão temporal negativa fora do domínio.")
        values.append(value)
    return values


def _series_history(history: pd.DataFrame | None, target: str) -> list[dict[str, Any]]:
    if history is None or history.empty or "period" not in history.columns:
        return []
    if target not in history.columns:
        return []
    data = history.copy()
    data["period"] = pd.to_datetime(data["period"], errors="coerce")
    data = data.dropna(subset=["period"]).sort_values("period")
    rows: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        rows.append(
            {
                "period": pd.Timestamp(row["period"]).isoformat(),
                target: float(row[target]) if pd.notna(row.get(target)) else None,
            }
        )
    return rows
