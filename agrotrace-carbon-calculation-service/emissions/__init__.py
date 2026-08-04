"""Camada de cálculos de emissões: funções puras, entradas explícitas e escopo temporal."""

__version__ = "1.0.0"

from emissions.calculation_bundle import CalculationBundle, ProvenanceMetadata
from emissions.csv_adapter import farm_period_from_row, required_csv_columns
from emissions.defaults import (
    ANIMAL_CATEGORIES,
    ENERGY_VECTORS,
    MILK_KG_FPCM_COLUMN,
    MILK_LITERS_COLUMN,
    NITROGEN_APPLIED_KG_COLUMN,
    default_energy_co2_kg_per_unit_yearly_basis,
    default_enteric_ch4_kg_per_animal_yearly,
    default_fertilizer_factors,
    default_manure_ch4_kg_per_kg_manure,
    default_manure_kg_per_kg_bw_per_day,
    extract_body_weights_kg,
    extract_energy_consumption,
    extract_headcounts,
    extract_milk_kg_fpcm,
    extract_milk_liters,
    extract_nitrogen_applied_kg,
    gwp_ipcc_ar4,
)
from emissions.emission_intensity import (
    build_milk_intensity_indicators,
    calculate_emission_intensity_per_milk_fpcm,
    calculate_emission_intensity_per_milk_liter,
)
from emissions.energy import calculate_energy_co2
from emissions.enteric_fermentation import calculate_enteric_fermentation_ch4
from emissions.factor_alignment import (
    align_energy_factors_to_scope,
    align_enteric_factors_to_scope,
)
from emissions.explanation import (
    SCHEMA_VERSION as EXPLANATION_SCHEMA_VERSION,
    CalculationExplanation,
    ValueOrigin,
    build_calculation_explanation,
    compute_explanation_hash,
    explanation_from_dict,
)
from emissions.farm_period import FarmPeriodInput
from emissions.fertilizer import calculate_fertilizer_n2o
from emissions.ghg_total import calculate_total_ghg_co2e
from emissions.manure_management import calculate_manure_management_ch4
from emissions.models import CalculationResult, TotalGhgResult
from emissions.temporal_consolidator import (
    ConsolidationType,
    consolidate_monthly_calculation_results,
    consolidate_monthly_ghg_totals,
)
from emissions.temporal_defaults import default_days_in_period, resolve_days_in_period
from emissions.temporal_scope import TemporalScope, normalize_temporal_label, require_matching_scope

__all__ = [
    "ANIMAL_CATEGORIES",
    "ENERGY_VECTORS",
    "EXPLANATION_SCHEMA_VERSION",
    "MILK_KG_FPCM_COLUMN",
    "MILK_LITERS_COLUMN",
    "NITROGEN_APPLIED_KG_COLUMN",
    "CalculationBundle",
    "CalculationExplanation",
    "CalculationResult",
    "ConsolidationType",
    "FarmPeriodInput",
    "ProvenanceMetadata",
    "TemporalScope",
    "TotalGhgResult",
    "ValueOrigin",
    "align_energy_factors_to_scope",
    "align_enteric_factors_to_scope",
    "build_calculation_explanation",
    "build_milk_intensity_indicators",
    "calculate_emission_intensity_per_milk_fpcm",
    "calculate_emission_intensity_per_milk_liter",
    "calculate_energy_co2",
    "calculate_enteric_fermentation_ch4",
    "calculate_fertilizer_n2o",
    "calculate_manure_management_ch4",
    "calculate_total_ghg_co2e",
    "compute_explanation_hash",
    "consolidate_monthly_calculation_results",
    "consolidate_monthly_ghg_totals",
    "default_days_in_period",
    "default_energy_co2_kg_per_unit_yearly_basis",
    "default_enteric_ch4_kg_per_animal_yearly",
    "default_fertilizer_factors",
    "default_manure_ch4_kg_per_kg_manure",
    "default_manure_kg_per_kg_bw_per_day",
    "explanation_from_dict",
    "extract_body_weights_kg",
    "extract_energy_consumption",
    "extract_headcounts",
    "extract_milk_kg_fpcm",
    "extract_milk_liters",
    "extract_nitrogen_applied_kg",
    "farm_period_from_row",
    "gwp_ipcc_ar4",
    "normalize_temporal_label",
    "required_csv_columns",
    "require_matching_scope",
    "resolve_days_in_period",
]
