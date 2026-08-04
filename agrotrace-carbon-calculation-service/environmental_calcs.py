"""
Compatibilidade com o módulo legado e ponto de entrada para CSV.

A lógica de negócio vive em ``orchestration.pipeline`` e ``emissions.*``.
Este ficheiro delega e mantém assinaturas próximas do legado.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from emissions import gwp_ipcc_ar4
from emissions.calculation_bundle import CalculationBundle
from emissions.temporal_defaults import resolve_days_in_period
from emissions.temporal_scope import TemporalScope
from orchestration.pipeline import compute_row_emissions

# Reexport para importadores antigos
GWP = gwp_ipcc_ar4()


def _default_days_in_period(temporal_scope: TemporalScope) -> int:
    """Compatibilidade: delega a ``emissions.temporal_defaults``."""
    return resolve_days_in_period(temporal_scope)


def calculate_total_emissions_bundle(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    days_in_period: int | None = None,
    gwp: Mapping[str, float] | None = None,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None = None,
    manure_kg_per_kg_body_weight_per_day: Mapping[str, float] | None = None,
    ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    fertilizer_factors: Mapping[str, float] | None = None,
    energy_co2_kg_per_unit: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> CalculationBundle:
    """API recomendada: retorna bundle completo com metadados e indicadores."""
    return compute_row_emissions(
        farm_data,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
        enteric_ch4_kg_per_animal=enteric_ch4_kg_per_animal,
        manure_kg_per_kg_bw_per_day=manure_kg_per_kg_body_weight_per_day,
        manure_ch4_kg_per_kg_manure=ch4_kg_per_kg_manure,
        energy_co2_kg_per_unit=energy_co2_kg_per_unit,
        fertilizer_factors=fertilizer_factors,
        gwp=gwp,
        auto_prorate_factors=auto_prorate_factors,
    )


def calculate_enteric_fermentation(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    ch4_kg_per_animal_in_period: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> float:
    bundle = compute_row_emissions(
        farm_data,
        temporal_scope=temporal_scope,
        enteric_ch4_kg_per_animal=ch4_kg_per_animal_in_period,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.enteric.value


def calculate_manure_management(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    days_in_period: int | None = None,
    manure_kg_per_kg_body_weight_per_day: Mapping[str, float] | None = None,
    ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> float:
    bundle = compute_row_emissions(
        farm_data,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
        manure_kg_per_kg_bw_per_day=manure_kg_per_kg_body_weight_per_day,
        manure_ch4_kg_per_kg_manure=ch4_kg_per_kg_manure,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.manure.value


def calculate_fertilizer_emissions(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    fertilizer_factors: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> float:
    bundle = compute_row_emissions(
        farm_data,
        temporal_scope=temporal_scope,
        fertilizer_factors=fertilizer_factors,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.fertilizer.value


def calculate_energy_emissions(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    co2_kg_per_unit_consumption: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> float:
    bundle = compute_row_emissions(
        farm_data,
        temporal_scope=temporal_scope,
        energy_co2_kg_per_unit=co2_kg_per_unit_consumption,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.energy.value


def calculate_total_emissions(
    farm_data: Mapping[str, float],
    *,
    temporal_scope: TemporalScope = TemporalScope.YEARLY,
    days_in_period: int | None = None,
    gwp: Mapping[str, float] | None = None,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None = None,
    manure_kg_per_kg_body_weight_per_day: Mapping[str, float] | None = None,
    ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    fertilizer_factors: Mapping[str, float] | None = None,
    energy_co2_kg_per_unit: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> float:
    bundle = calculate_total_emissions_bundle(
        farm_data,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
        gwp=gwp,
        enteric_ch4_kg_per_animal=enteric_ch4_kg_per_animal,
        manure_kg_per_kg_body_weight_per_day=manure_kg_per_kg_body_weight_per_day,
        ch4_kg_per_kg_manure=ch4_kg_per_kg_manure,
        fertilizer_factors=fertilizer_factors,
        energy_co2_kg_per_unit=energy_co2_kg_per_unit,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.total.co2e_kg


if __name__ == "__main__":
    from batch_runner import run_csv_pipeline

    base_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    input_file_path = os.path.join(base_directory, "data/processed/validated_data.csv")
    output_file_path = os.path.join(base_directory, "data/processed/calculate_data.csv")

    final_data = run_csv_pipeline(
        input_file_path,
        output_file_path,
        temporal_scope=TemporalScope.YEARLY,
    )
    print(final_data)
