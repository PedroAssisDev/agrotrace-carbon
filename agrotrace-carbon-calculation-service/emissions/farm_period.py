"""Contrato tipado de entrada para um período de inventário."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from emissions.temporal_scope import TemporalScope


@dataclass(frozen=True)
class FarmPeriodInput:
    """
    Entrada canónica para cálculo de emissões de um período (mensal ou anual).

    Todas as magnitudes de massa/consumo devem referir-se ao **mesmo** período
    indicado por ``temporal_scope`` e ``days_in_period``.
    """

    temporal_scope: TemporalScope
    days_in_period: int
    headcounts_by_category: dict[str, float]
    body_weight_kg_by_category: dict[str, float]
    nitrogen_applied_kg: float
    energy_consumption_by_vector: dict[str, float]
    period_start: date | None = None
    period_end: date | None = None
    milk_liters: float | None = None
    milk_kg_fpcm: float | None = None
    farm_area_ha: float | None = None
