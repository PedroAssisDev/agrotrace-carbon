"""Orquestração unificada de cálculos de emissões."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from emissions.calculation_bundle import CalculationBundle, ProvenanceMetadata
from emissions.emission_intensity import build_milk_intensity_indicators
from emissions.energy import calculate_energy_co2
from emissions.enteric_fermentation import calculate_enteric_fermentation_ch4
from emissions.factor_alignment import (
    DEFAULT_ENERGY_FACTOR_TEMPORAL_BASIS,
    DEFAULT_ENTERIC_FACTOR_TEMPORAL_BASIS,
    align_energy_factors_to_scope,
    align_enteric_factors_to_scope,
)
from emissions.farm_period import FarmPeriodInput
from emissions.fertilizer import calculate_fertilizer_n2o
from emissions.ghg_total import calculate_total_ghg_co2e
from emissions.manure_management import calculate_manure_management_ch4
from emissions.temporal_defaults import resolve_days_in_period
from emissions.temporal_scope import TemporalScope

METHOD_CODE = "ECOFARM-T1-DAIRY"
METHOD_VERSION = "1.0.0"
IMPLEMENTATION_VERSION = "0.3.1"


def _resolve_default_factors(
    *,
    temporal_scope: TemporalScope,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None,
    manure_kg_per_kg_bw_per_day: Mapping[str, float] | None,
    manure_ch4_kg_per_kg_manure: Mapping[str, float] | None,
    energy_co2_kg_per_unit: Mapping[str, float] | None,
    fertilizer_factors: Mapping[str, float] | None,
    gwp: Mapping[str, float] | None,
    auto_prorate_factors: bool,
) -> tuple[
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
]:
    from emissions.defaults import (
        default_energy_co2_kg_per_unit_yearly_basis,
        default_enteric_ch4_kg_per_animal_yearly,
        default_fertilizer_factors,
        default_manure_ch4_kg_per_kg_manure,
        default_manure_kg_per_kg_bw_per_day,
        gwp_ipcc_ar4,
    )

    raw_enteric = enteric_ch4_kg_per_animal or default_enteric_ch4_kg_per_animal_yearly()
    if enteric_ch4_kg_per_animal is not None:
        enteric = {k: float(v) for k, v in raw_enteric.items()}
    else:
        enteric = align_enteric_factors_to_scope(
            raw_enteric,
            temporal_scope=temporal_scope,
            factor_temporal_basis=DEFAULT_ENTERIC_FACTOR_TEMPORAL_BASIS,
            auto_prorate=auto_prorate_factors,
        )

    raw_energy = energy_co2_kg_per_unit or default_energy_co2_kg_per_unit_yearly_basis()
    if energy_co2_kg_per_unit is not None:
        energy = {k: float(v) for k, v in raw_energy.items()}
    else:
        energy = align_energy_factors_to_scope(
            raw_energy,
            temporal_scope=temporal_scope,
            factor_temporal_basis=DEFAULT_ENERGY_FACTOR_TEMPORAL_BASIS,
            auto_prorate=auto_prorate_factors,
        )

    return (
        enteric,
        dict(manure_kg_per_kg_bw_per_day or default_manure_kg_per_kg_bw_per_day()),
        dict(manure_ch4_kg_per_kg_manure or default_manure_ch4_kg_per_kg_manure()),
        energy,
        dict(fertilizer_factors or default_fertilizer_factors()),
        dict(gwp or gwp_ipcc_ar4()),
    )


def compute_farm_period_emissions(
    farm_input: FarmPeriodInput,
    *,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None = None,
    manure_kg_per_kg_bw_per_day: Mapping[str, float] | None = None,
    manure_ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    energy_co2_kg_per_unit: Mapping[str, float] | None = None,
    fertilizer_factors: Mapping[str, float] | None = None,
    gwp: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
    include_provenance: bool = True,
) -> CalculationBundle:
    """
    Calcula emissões completas para um :class:`FarmPeriodInput`.

    Aplica alinhamento temporal de fatores default e calcula indicadores de
    intensidade láctea quando ``milk_liters`` ou ``milk_kg_fpcm`` estão presentes.
    """
    (
        enteric_factors,
        manure_md,
        manure_ef,
        energy_factors,
        fert_factors,
        gwp_values,
    ) = _resolve_default_factors(
        temporal_scope=farm_input.temporal_scope,
        enteric_ch4_kg_per_animal=enteric_ch4_kg_per_animal,
        manure_kg_per_kg_bw_per_day=manure_kg_per_kg_bw_per_day,
        manure_ch4_kg_per_kg_manure=manure_ch4_kg_per_kg_manure,
        energy_co2_kg_per_unit=energy_co2_kg_per_unit,
        fertilizer_factors=fertilizer_factors,
        gwp=gwp,
        auto_prorate_factors=auto_prorate_factors,
    )

    enteric = calculate_enteric_fermentation_ch4(
        temporal_scope=farm_input.temporal_scope,
        headcounts_by_category=farm_input.headcounts_by_category,
        ch4_kg_per_animal_in_period=enteric_factors,
    )
    manure = calculate_manure_management_ch4(
        temporal_scope=farm_input.temporal_scope,
        headcounts_by_category=farm_input.headcounts_by_category,
        body_weight_kg_by_category=farm_input.body_weight_kg_by_category,
        manure_kg_per_kg_body_weight_per_day=manure_md,
        ch4_kg_per_kg_manure=manure_ef,
        days_in_period=farm_input.days_in_period,
    )
    fertilizer = calculate_fertilizer_n2o(
        temporal_scope=farm_input.temporal_scope,
        nitrogen_applied_kg=farm_input.nitrogen_applied_kg,
        direct_n2o_emission_factor=float(fert_factors["direct_n2o_emission_factor"]),
        indirect_n2o_emission_factor=float(fert_factors["indirect_n2o_emission_factor"]),
        fraction_n_volatilized=float(fert_factors["fraction_n_volatilized"]),
    )
    energy = calculate_energy_co2(
        temporal_scope=farm_input.temporal_scope,
        consumption_by_vector=farm_input.energy_consumption_by_vector,
        co2_kg_per_unit_consumption=energy_factors,
    )
    total = calculate_total_ghg_co2e(
        enteric_ch4=enteric,
        manure_ch4=manure,
        fertilizer_n2o=fertilizer,
        energy_co2=energy,
        gwp_ch4=float(gwp_values["CH4"]),
        gwp_n2o=float(gwp_values["N2O"]),
    )

    indicators = build_milk_intensity_indicators(
        temporal_scope=farm_input.temporal_scope,
        co2e_kg=total.co2e_kg,
        milk_liters=farm_input.milk_liters,
        milk_kg_fpcm=farm_input.milk_kg_fpcm,
    )

    provenance = None
    if include_provenance:
        provenance = ProvenanceMetadata(
            method_code=METHOD_CODE,
            method_version=METHOD_VERSION,
            implementation_version=IMPLEMENTATION_VERSION,
        )

    return CalculationBundle(
        enteric=enteric,
        manure=manure,
        fertilizer=fertilizer,
        energy=energy,
        total=total,
        indicators=indicators,
        provenance=provenance,
    )


def compute_row_emissions(
    row: Mapping[str, Any],
    *,
    temporal_scope: TemporalScope,
    days_in_period: int | None = None,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None = None,
    manure_kg_per_kg_bw_per_day: Mapping[str, float] | None = None,
    manure_ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    energy_co2_kg_per_unit: Mapping[str, float] | None = None,
    fertilizer_factors: Mapping[str, float] | None = None,
    gwp: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> CalculationBundle:
    """Atalho: linha CSV → :class:`CalculationBundle`."""
    from emissions.csv_adapter import farm_period_from_row

    farm_input = farm_period_from_row(
        row,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
    )
    return compute_farm_period_emissions(
        farm_input,
        enteric_ch4_kg_per_animal=enteric_ch4_kg_per_animal,
        manure_kg_per_kg_bw_per_day=manure_kg_per_kg_bw_per_day,
        manure_ch4_kg_per_kg_manure=manure_ch4_kg_per_kg_manure,
        energy_co2_kg_per_unit=energy_co2_kg_per_unit,
        fertilizer_factors=fertilizer_factors,
        gwp=gwp,
        auto_prorate_factors=auto_prorate_factors,
    )
