"""Create schemas and PostgreSQL enum types.

Revision ID: 0001_schemas_enums
Revises:
Create Date: 2026-04-29
"""

from __future__ import annotations

from alembic import op

revision = "0001_schemas_enums"
down_revision = None
branch_labels = None
depends_on = None

SCHEMAS = ("pipeline", "prov_core", "semantic", "calculation", "audit")

ENUMS: dict[str, tuple[str, ...]] = {
    "pipeline_run_status": (
        "pending",
        "running",
        "succeeded",
        "failed",
        "cancelled",
        "superseded",
    ),
    "wrapper_execution_status": ("pending", "running", "succeeded", "failed"),
    "prov_bundle_type": (
        "pipeline_run",
        "wrapper_execution",
        "semantic_integration",
        "calculation",
        "publication",
        "audit",
    ),
    "prov_bundle_status": ("open", "closed", "invalidated"),
    "prov_entity_type": (
        "source_artifact",
        "normalized_batch",
        "canonical_snapshot",
        "calculation_parameter_set",
        "calculation_result_set",
        "ontology_resource",
        "other",
    ),
    "prov_activity_type": (
        "wrapper_execution",
        "semantic_integration",
        "calculation_execution",
        "calculation_review",
        "result_publication",
        "blockchain_anchoring",
        "other",
    ),
    "prov_agent_type": ("human", "software", "organization"),
    "semantic_execution_status": ("pending", "running", "succeeded", "failed"),
    "publication_stage": ("draft", "preliminary", "final", "retracted"),
    "calculation_method_status": ("draft", "active", "deprecated", "retired"),
    "parameter_set_status": ("draft", "locked", "superseded"),
    "calculation_execution_status": ("pending", "running", "succeeded", "failed"),
    "calculation_result_set_status": (
        "preliminary",
        "under_review",
        "approved",
        "rejected",
        "superseded",
    ),
    "calculation_result_type": (
        "emission_total",
        "emission_by_category",
        "intensity",
        "productivity",
        "other",
    ),
    "calculation_review_decision": (
        "pending",
        "approved",
        "rejected",
        "changes_requested",
    ),
    "result_publication_status": (
        "pending",
        "publishing",
        "published",
        "failed",
        "rolled_back",
    ),
    "hash_algorithm": ("sha256", "sha3_256"),
    "hash_subject_kind": (
        "source_artifact",
        "normalized_batch",
        "canonical_snapshot",
        "calculation_result_set",
        "calculation_parameter_set",
        "bundle",
        "other",
    ),
    "blockchain_anchor_status": (
        "pending",
        "submitted",
        "confirmed",
        "failed",
        "rolled_back",
    ),
    "outbox_status": ("pending", "published", "failed", "dead_lettered"),
}


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    for enum_name, values in ENUMS.items():
        formatted = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({formatted})")


def downgrade() -> None:
    for enum_name in reversed(list(ENUMS.keys())):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
