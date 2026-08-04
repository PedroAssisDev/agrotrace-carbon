"""Public API for AgroMRV-O Lite."""

from ontology.builder import build_base_ontology, build_full_ontology
from ontology.catalogs import populate_catalogs
from ontology.cycle_model import (
    list_cycle_observations,
    set_cycle_status,
    upsert_emission_cycle,
    upsert_observation,
    upsert_property,
)
from ontology.exporters import export_ontology
from ontology.parameter_lifecycle import (
    extract_factor_catalog_with_statuses,
    set_groups_status,
    set_parameter_status,
    upsert_emission_factor_value,
    upsert_gwp_value,
)
from ontology.population import populate_from_csv, populate_from_dataframe
from ontology.result_lifecycle import (
    list_active_results,
    set_results_status,
    upsert_emission_result,
)

__all__ = [
    "build_base_ontology",
    "build_full_ontology",
    "populate_catalogs",
    "populate_from_dataframe",
    "populate_from_csv",
    "export_ontology",
    "upsert_emission_factor_value",
    "upsert_gwp_value",
    "set_parameter_status",
    "set_groups_status",
    "extract_factor_catalog_with_statuses",
    "upsert_property",
    "upsert_emission_cycle",
    "upsert_observation",
    "list_cycle_observations",
    "set_cycle_status",
    "upsert_emission_result",
    "list_active_results",
    "set_results_status",
]
