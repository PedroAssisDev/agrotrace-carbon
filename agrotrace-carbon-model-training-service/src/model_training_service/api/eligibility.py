"""Avaliação de elegibilidade por slot (regras no training-service)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from model_training_service.api.contracts import ModelSlot
from model_training_service.data.validation import assert_monthly_series_is_contiguous
from model_training_service.domain.enums import ModelFamily
from model_training_service.domain.errors import DataValidationError


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str | None = None
    record_count: int = 0
    period_start: str | None = None
    period_end: str | None = None


class EligibilityService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def evaluate(self, data: pd.DataFrame, slot: ModelSlot) -> EligibilityResult:
        if slot.family == ModelFamily.REGRESSION.value:
            return self._regression(data, slot)
        return self._time_series(data, slot)

    def _regression(self, data: pd.DataFrame, slot: ModelSlot) -> EligibilityResult:
        feature = self.config["regression"]["feature"]
        target = slot.target
        subset = data[data["granularity"].eq(slot.granularity)][
            ["property_id", "period", feature, target]
        ].dropna()
        count = int(len(subset))
        minimum = int(self.config["regression"]["min_records"])
        period_start = period_end = None
        if not subset.empty:
            periods = pd.to_datetime(subset["period"])
            period_start = periods.min().isoformat()
            period_end = periods.max().isoformat()
        if count < minimum:
            return EligibilityResult(
                False,
                f"Registros insuficientes ({count}; mínimo {minimum}).",
                count,
                period_start,
                period_end,
            )
        if subset["property_id"].nunique() < 1:
            return EligibilityResult(False, "Nenhuma propriedade no dataset.", count)
        if (subset[feature] < 0).any() or (subset[target] < 0).any():
            return EligibilityResult(False, "Valores negativos no dataset.", count)
        return EligibilityResult(True, None, count, period_start, period_end)

    def _time_series(self, data: pd.DataFrame, slot: ModelSlot) -> EligibilityResult:
        ts = self.config["time_series"]
        target = slot.target
        property_id = str(slot.property_id)
        subset = (
            data[
                data["granularity"].eq("monthly")
                & data["property_id"].astype(str).eq(property_id)
            ][["property_id", "period", target]]
            .dropna()
            .sort_values("period")
            .reset_index(drop=True)
        )
        count = int(len(subset))
        minimum = int(ts["min_records"])
        period_start = period_end = None
        if not subset.empty:
            periods = pd.to_datetime(subset["period"])
            period_start = periods.min().isoformat()
            period_end = periods.max().isoformat()
        if count < minimum:
            return EligibilityResult(
                False,
                f"Histórico mensal insuficiente ({count}; mínimo {minimum}).",
                count,
                period_start,
                period_end,
            )
        gap_policy = (self.config.get("validation") or {}).get("monthly_gap_policy", "reject")
        try:
            assert_monthly_series_is_contiguous(subset)
        except DataValidationError as exc:
            if gap_policy == "skip_property":
                return EligibilityResult(
                    False,
                    f"Lacunas mensais (política skip_property): {exc}",
                    count,
                    period_start,
                    period_end,
                )
            return EligibilityResult(
                False,
                f"Lacunas mensais: {exc}",
                count,
                period_start,
                period_end,
            )
        if int(ts.get("forecast_horizon", 3)) != 3:
            return EligibilityResult(False, "Horizonte configurado diferente de 3.")
        return EligibilityResult(True, None, count, period_start, period_end)
