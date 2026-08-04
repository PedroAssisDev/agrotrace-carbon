"""Tipos de predição — distintos de CalculationResult / resultados observados."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PREDICTION_KIND = "prediction"
PREDICTION_MARKER = "__agrotrace_kind__"


@dataclass
class Prediction:
    """Resultado preditivo — nunca publicável como inventário oficial do ciclo."""

    property_id: str
    predicted_milk_production_liters: float | None = None
    predicted_total_ghg_emissions_tco2e: float | None = None
    granularity: str | None = None
    forecast_period: str | None = None
    milk_model_id: str | None = None
    emissions_model_id: str | None = None
    milk_model_version: str | None = None
    emissions_model_version: str | None = None
    source: str = "forecast_inference"
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extras = data.pop("extras", {}) or {}
        data.update(extras)
        data[PREDICTION_MARKER] = PREDICTION_KIND
        return data


def prediction_from_inference_dict(payload: dict[str, Any]) -> Prediction:
    """Wrap a forecast_inference result dict as Prediction."""
    known = {
        "property_id",
        "predicted_milk_production_liters",
        "predicted_total_ghg_emissions_tco2e",
        "granularity",
        "forecast_period",
        "milk_model_id",
        "emissions_model_id",
        "milk_model_version",
        "emissions_model_version",
    }
    extras = {k: v for k, v in payload.items() if k not in known and k != PREDICTION_MARKER}
    return Prediction(
        property_id=str(payload.get("property_id") or ""),
        predicted_milk_production_liters=_num(payload.get("predicted_milk_production_liters")),
        predicted_total_ghg_emissions_tco2e=_num(payload.get("predicted_total_ghg_emissions_tco2e")),
        granularity=payload.get("granularity"),
        forecast_period=payload.get("forecast_period"),
        milk_model_id=payload.get("milk_model_id"),
        emissions_model_id=payload.get("emissions_model_id"),
        milk_model_version=payload.get("milk_model_version"),
        emissions_model_version=payload.get("emissions_model_version"),
        extras=extras,
    )


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_prediction_payload(obj: Any) -> bool:
    """True when obj is a Prediction instance or a dict marked / shaped as prediction."""
    if isinstance(obj, Prediction):
        return True
    if not isinstance(obj, dict):
        return False
    if obj.get(PREDICTION_MARKER) == PREDICTION_KIND:
        return True
    if obj.get("kind") == PREDICTION_KIND or obj.get("result_kind") == PREDICTION_KIND:
        return True
    # Heuristic: prediction-only numeric fields without calculation structure
    pred_keys = (
        "predicted_milk_production_liters",
        "predicted_total_ghg_emissions_tco2e",
        "milk_predictions",
        "emission_predictions",
    )
    if any(k in obj for k in pred_keys) and "co2e_total_kg" not in (obj.get("calculation") or obj):
        if obj.get("source") == "forecast_inference" or "predicted_" in str(list(obj.keys())):
            return True
    return False


class PredictionNotPublishableError(ValueError):
    """Predições não podem ser publicadas como resultados observados (RF011 / RN-03)."""
