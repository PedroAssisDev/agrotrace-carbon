"""Indicadores de intensidade de emissão para pecuária leiteira."""

from __future__ import annotations

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope
from emissions.validators import require_non_negative


def calculate_emission_intensity_per_milk_liter(
    *,
    temporal_scope: TemporalScope,
    co2e_kg: float,
    milk_liters: float,
) -> CalculationResult:
    """
    Intensidade de emissão por litro de leite.

    Unidade: kg CO2e / L
    """
    require_non_negative("co2e_kg", float(co2e_kg))
    require_non_negative("milk_liters", float(milk_liters))
    if float(milk_liters) == 0:
        raise CalculationError(
            "milk_liters deve ser > 0 para calcular intensidade por litro; recebido 0."
        )
    value = float(co2e_kg) / float(milk_liters)
    return CalculationResult(
        value=value,
        unit="kg CO2e/L",
        temporal_scope=temporal_scope,
        description="Emission intensity per milk liter",
    )


def calculate_emission_intensity_per_milk_fpcm(
    *,
    temporal_scope: TemporalScope,
    co2e_kg: float,
    milk_kg_fpcm: float,
) -> CalculationResult:
    """
    Intensidade de emissão por kg de leite corrigido (FPCM).

    Unidade: kg CO2e / kg FPCM
    """
    require_non_negative("co2e_kg", float(co2e_kg))
    require_non_negative("milk_kg_fpcm", float(milk_kg_fpcm))
    if float(milk_kg_fpcm) == 0:
        raise CalculationError(
            "milk_kg_fpcm deve ser > 0 para calcular intensidade FPCM; recebido 0."
        )
    value = float(co2e_kg) / float(milk_kg_fpcm)
    return CalculationResult(
        value=value,
        unit="kg CO2e/kg FPCM",
        temporal_scope=temporal_scope,
        description="Emission intensity per kg FPCM",
    )


def build_milk_intensity_indicators(
    *,
    temporal_scope: TemporalScope,
    co2e_kg: float,
    milk_liters: float | None = None,
    milk_kg_fpcm: float | None = None,
) -> dict[str, CalculationResult]:
    """Calcula indicadores de intensidade disponíveis a partir dos inputs."""
    indicators: dict[str, CalculationResult] = {}
    if milk_liters is not None and float(milk_liters) > 0:
        indicators["co2e_intensity_per_milk_liter"] = calculate_emission_intensity_per_milk_liter(
            temporal_scope=temporal_scope,
            co2e_kg=co2e_kg,
            milk_liters=float(milk_liters),
        )
    if milk_kg_fpcm is not None and float(milk_kg_fpcm) > 0:
        indicators["co2e_intensity_per_milk_fpcm"] = calculate_emission_intensity_per_milk_fpcm(
            temporal_scope=temporal_scope,
            co2e_kg=co2e_kg,
            milk_kg_fpcm=float(milk_kg_fpcm),
        )
    return indicators
