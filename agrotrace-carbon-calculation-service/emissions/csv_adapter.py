"""Adaptadores entre linhas CSV/planilha e contratos tipados."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from emissions.defaults import (
    ANIMAL_CATEGORIES,
    ENERGY_VECTORS,
    MILK_KG_FPCM_COLUMN,
    MILK_LITERS_COLUMN,
    NITROGEN_APPLIED_KG_COLUMN,
    extract_body_weights_kg,
    extract_energy_consumption,
    extract_headcounts,
    extract_milk_kg_fpcm,
    extract_milk_liters,
    extract_nitrogen_applied_kg,
)
from emissions.exceptions import CalculationError
from emissions.farm_period import FarmPeriodInput
from emissions.temporal_defaults import resolve_days_in_period
from emissions.temporal_scope import TemporalScope


def farm_period_from_row(
    row: Mapping[str, Any],
    *,
    temporal_scope: TemporalScope,
    days_in_period: int | None = None,
) -> FarmPeriodInput:
    """Constrói :class:`FarmPeriodInput` a partir de uma linha estilo CSV legado."""
    return FarmPeriodInput(
        temporal_scope=temporal_scope,
        days_in_period=resolve_days_in_period(temporal_scope, days_in_period),
        headcounts_by_category=extract_headcounts(row, ANIMAL_CATEGORIES),
        body_weight_kg_by_category=extract_body_weights_kg(row, ANIMAL_CATEGORIES),
        nitrogen_applied_kg=extract_nitrogen_applied_kg(row),
        energy_consumption_by_vector=extract_energy_consumption(row, ENERGY_VECTORS),
        milk_liters=extract_milk_liters(row),
        milk_kg_fpcm=extract_milk_kg_fpcm(row),
    )


def require_csv_columns(row: Mapping[str, Any], columns: tuple[str, ...]) -> None:
    """Valida presença de colunas obrigatórias antes do cálculo em lote."""
    missing = [c for c in columns if c not in row]
    if missing:
        raise CalculationError(
            f"Colunas obrigatórias em falta na linha de dados: {missing}."
        )


def required_csv_columns() -> tuple[str, ...]:
    """Colunas mínimas exigidas para o pipeline CSV."""
    weight_cols = tuple(f"{c}_Weight" for c in ANIMAL_CATEGORIES)
    return (
        *ANIMAL_CATEGORIES,
        *weight_cols,
        NITROGEN_APPLIED_KG_COLUMN,
        *ENERGY_VECTORS,
    )
