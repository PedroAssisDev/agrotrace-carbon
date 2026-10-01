"""Inferência de regressão global (cenário por rebanho)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from services.forecast_inference.errors import (
    InvalidInputError,
    ModelNotFoundError,
    OutOfDomainPredictionError,
)
from services.forecast_inference.loader import ModelArtifactLoader
from services.forecast_inference.period import next_period_label
from services.forecast_inference.property_history import (
    get_regression_scenario_defaults,
    history_rows_for_property,
    load_property_history_frame,
)
from services.forecast_inference.registry import ModelRegistryReader

TARGETS = ("milk_production_liters", "total_ghg_emissions_tco2e")


class RegressionInferenceService:
    def __init__(self, registry: ModelRegistryReader, loader: ModelArtifactLoader) -> None:
        self.registry = registry
        self.loader = loader

    def predict(
        self,
        *,
        property_id: str,
        granularity: str,
        expected_lactating_cows: int | float,
    ) -> dict[str, Any]:
        cows = _validate_cows(expected_lactating_cows)
        if granularity not in {"monthly", "annual"}:
            raise InvalidInputError("Granularidade deve ser monthly ou annual.")

        predictions: dict[str, float | None] = {}
        model_meta: dict[str, Any] = {}
        warnings: list[str] = []
        history_by_period: dict[str, dict[str, Any]] = {}

        # Preferência: histórico da propriedade na fonte de treino (ciclos publicados).
        property_defaults = get_regression_scenario_defaults(property_id, granularity)
        property_frame = load_property_history_frame(property_id, granularity)
        for row in history_rows_for_property(property_id, granularity):
            history_by_period[str(row["period"])] = dict(row)

        forecast_period = property_defaults.get("forecast_period") or "Próximo período"
        period_resolved = bool(property_defaults.get("last_period"))

        for target in TARGETS:
            try:
                entry = self.registry.find_latest(
                    model_family="regression",
                    model_scope="global",
                    granularity=granularity,
                    target=target,
                    property_id=None,
                )
                artifact = self.loader.load(entry, expect_family="regression")
                value = _predict_single(artifact.model, cows)
                predictions[target] = value
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
                }
                # Fallback: histórico embutido no artefato se a fonte de ciclos estiver vazia.
                if not history_by_period and artifact.history is not None:
                    for row in _history_for_property(artifact.history, property_id, target):
                        key = str(row["period"])
                        bucket = history_by_period.setdefault(
                            key,
                            {
                                "period": key,
                                "lactating_cows": row.get("lactating_cows"),
                            },
                        )
                        if row.get("lactating_cows") is not None:
                            bucket["lactating_cows"] = row.get("lactating_cows")
                        bucket[target] = row.get(target)
                if not period_resolved:
                    forecast_period = next_period_label(
                        granularity=granularity,
                        history=property_frame if not property_frame.empty else artifact.history,
                        property_id=property_id,
                        manifest=artifact.manifest,
                    )
                    period_resolved = True
            except (ModelNotFoundError, OutOfDomainPredictionError) as exc:
                predictions[target] = None
                warnings.append(f"{target}: {exc}")
            except Exception as exc:  # noqa: BLE001
                predictions[target] = None
                warnings.append(f"{target}: {exc}")

        history_rows = sorted(history_by_period.values(), key=lambda item: item["period"])

        if all(v is None for v in predictions.values()):
            raise ModelNotFoundError(
                "Nenhum modelo de regressão compatível produziu previsão válida."
            )

        milk = predictions.get("milk_production_liters")
        emissions = predictions.get("total_ghg_emissions_tco2e")
        intensity = None
        if milk is not None and emissions is not None and milk > 0:
            intensity = float(emissions) / float(milk)

        return {
            "property_id": property_id,
            "granularity": granularity,
            "forecast_period": forecast_period,
            "last_period_label": property_defaults.get("last_period_label"),
            "last_lactating_cows": property_defaults.get("last_lactating_cows"),
            "expected_lactating_cows": cows,
            "predicted_milk_production_liters": milk,
            "predicted_total_ghg_emissions_tco2e": emissions,
            "derived_intensity_tco2e_per_liter": intensity,
            "milk_model_id": (model_meta.get("milk_production_liters") or {}).get("model_id"),
            "emissions_model_id": (model_meta.get("total_ghg_emissions_tco2e") or {}).get("model_id"),
            "milk_model_version": (model_meta.get("milk_production_liters") or {}).get("version"),
            "emissions_model_version": (model_meta.get("total_ghg_emissions_tco2e") or {}).get(
                "version"
            ),
            "models": model_meta,
            "history": history_rows,
            "warnings": warnings,
        }


def _validate_cows(value: Any) -> int:
    if value is None or value == "":
        raise InvalidInputError("Informe a quantidade esperada de vacas em lactação.")
    try:
        # rejeita bool (bool is subclass of int)
        if isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("A quantidade de vacas deve ser um número inteiro.") from exc
    if not number.is_integer():
        raise InvalidInputError("A quantidade de vacas deve ser um número inteiro.")
    cows = int(number)
    if cows < 0:
        raise InvalidInputError("A quantidade de vacas não pode ser negativa.")
    return cows


def _predict_single(model: Any, cows: int) -> float:
    # Feature única: lactating_cows. property_id nunca entra no estimador.
    raw = model.predict(np.array([[float(cows)]]))
    value = float(np.asarray(raw).ravel()[0])
    if not np.isfinite(value):
        raise OutOfDomainPredictionError("Previsão não numérica ou infinita.")
    if value < 0:
        raise OutOfDomainPredictionError("Previsão negativa fora do domínio.")
    return value


def _history_for_property(
    history: pd.DataFrame, property_id: str, target: str
) -> list[dict[str, Any]]:
    if "property_id" not in history.columns or "period" not in history.columns:
        return []
    subset = history[history["property_id"].astype(str) == str(property_id)].copy()
    if subset.empty or target not in subset.columns:
        return []
    subset["period"] = pd.to_datetime(subset["period"], errors="coerce")
    subset = subset.dropna(subset=["period"]).sort_values("period")
    rows: list[dict[str, Any]] = []
    for _, row in subset.iterrows():
        rows.append(
            {
                "period": pd.Timestamp(row["period"]).isoformat(),
                "lactating_cows": float(row["lactating_cows"])
                if "lactating_cows" in subset.columns and pd.notna(row.get("lactating_cows"))
                else None,
                target: float(row[target]) if pd.notna(row.get(target)) else None,
            }
        )
    return rows
