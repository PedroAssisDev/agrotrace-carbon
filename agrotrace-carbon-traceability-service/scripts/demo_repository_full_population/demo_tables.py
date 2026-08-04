"""Expected SQLite table names (real ``__tablename__`` values from ORM models)."""

from __future__ import annotations

# Pipeline context (6)
PIPELINE_TABLES: tuple[str, ...] = (
    "pipeline_pipeline_run",
    "pipeline_source_artifact",
    "pipeline_source_artifact_revision",
    "pipeline_wrapper_definition",
    "pipeline_wrapper_execution",
    "pipeline_normalized_batch",
)

# Prov core context (10)
PROV_CORE_TABLES: tuple[str, ...] = (
    "prov_core_prov_bundle",
    "prov_core_prov_entity",
    "prov_core_prov_activity",
    "prov_core_prov_agent",
    "prov_core_prov_used",
    "prov_core_prov_generated",
    "prov_core_prov_derived_from",
    "prov_core_prov_associated_with",
    "prov_core_prov_revision",
    "prov_core_prov_attribute",
)

# Semantic context (4)
SEMANTIC_TABLES: tuple[str, ...] = (
    "semantic_semantic_integration_execution",
    "semantic_canonical_snapshot",
    "semantic_canonical_snapshot_item",
    "semantic_ontology_resource_link",
)

# Calculation context (9)
CALCULATION_TABLES: tuple[str, ...] = (
    "calculation_calculation_method",
    "calculation_calculation_method_version",
    "calculation_calculation_parameter_set",
    "calculation_calculation_parameter_value",
    "calculation_calculation_execution",
    "calculation_calculation_result_set",
    "calculation_calculation_result_item",
    "calculation_calculation_review",
    "calculation_result_publication_execution",
)

# Audit context (4)
AUDIT_TABLES: tuple[str, ...] = (
    "audit_hash_record",
    "audit_blockchain_anchor",
    "audit_outbox_event",
    "audit_audit_event",
)

EXPECTED_TABLES: tuple[str, ...] = (
    *PIPELINE_TABLES,
    *PROV_CORE_TABLES,
    *SEMANTIC_TABLES,
    *CALCULATION_TABLES,
    *AUDIT_TABLES,
)

TABLES_BY_CONTEXT: dict[str, tuple[str, ...]] = {
    "pipeline": PIPELINE_TABLES,
    "prov_core": PROV_CORE_TABLES,
    "semantic": SEMANTIC_TABLES,
    "calculation": CALCULATION_TABLES,
    "audit": AUDIT_TABLES,
}
