"""Blockchain observability preparation: reporting period, outbox evolution, aggregation links.

Revision ID: 0010_blockchain_observability
Revises: 0009_source_revision
Create Date: 2026-06-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_blockchain_observability"
down_revision = "0009_source_revision"
branch_labels = None
depends_on = None

NEW_ENUMS: dict[str, tuple[str, ...]] = {
    "period_granularity": ("daily", "monthly", "annual", "custom"),
    "reporting_period_status": (
        "open",
        "closed",
        "consolidated",
        "approved",
        "published",
        "superseded",
    ),
    "result_scope": ("daily", "monthly", "annual", "custom"),
    "consolidation_type": (
        "direct",
        "daily_to_monthly",
        "monthly_to_annual",
        "manual_adjustment",
        "reprocessing",
    ),
    "aggregation_type": (
        "daily_to_monthly",
        "monthly_to_annual",
        "manual_grouping",
    ),
    "hash_scope": (
        "record",
        "batch",
        "snapshot",
        "calculation_result",
        "calculation_parameter_set",
        "calculation_review",
        "ontology_publication",
        "aggregation",
    ),
    "run_type": (
        "raw_data_ingestion",
        "daily_ingestion",
        "monthly_calculation",
        "annual_calculation",
        "daily_to_monthly_aggregation",
        "monthly_to_annual_aggregation",
        "manual_reprocessing",
    ),
    "anchor_mode": (
        "local_simulation",
        "testnet",
        "mainnet",
        "permissioned_network",
    ),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS reporting")

    for enum_name, values in NEW_ENUMS.items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({vals})")

    op.execute("ALTER TYPE outbox_status ADD VALUE IF NOT EXISTS 'processing'")
    op.execute("ALTER TYPE outbox_status ADD VALUE IF NOT EXISTS 'processed'")

    op.create_table(
        "period",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_granularity", _enum("period_granularity"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=True),
        sa.Column("period_label", sa.String(64), nullable=False),
        sa.Column("status", _enum("reporting_period_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("reporting_period_id", name="pk_reporting_period"),
        sa.UniqueConstraint("period_label", name="uq_reporting_period_period_label"),
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_period_year_month",
        "period",
        ["year", "month"],
        schema="reporting",
    )
    op.create_index(
        "ix_reporting_period_granularity",
        "period",
        ["period_granularity"],
        schema="reporting",
    )

    # pipeline_run
    op.add_column(
        "pipeline_run",
        sa.Column("run_type", _enum("run_type"), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "pipeline_run",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "pipeline_run",
        sa.Column("farm_id_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "pipeline_run",
        sa.Column("project_id_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.create_foreign_key(
        "fk_pipeline_run_reporting_period_id",
        "pipeline_run",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="pipeline",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )

    # wrapper_definition / wrapper_execution
    op.add_column(
        "wrapper_definition",
        sa.Column("wrapper_code_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "wrapper_definition",
        sa.Column("input_schema_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "wrapper_definition",
        sa.Column("output_schema_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "wrapper_execution",
        sa.Column("execution_payload_hash", sa.String(128), nullable=True),
        schema="pipeline",
    )
    op.add_column(
        "wrapper_execution",
        sa.Column("runtime_version", sa.String(64), nullable=True),
        schema="pipeline",
    )

    # canonical_snapshot
    op.add_column(
        "canonical_snapshot",
        sa.Column("canonical_schema_version", sa.String(64), nullable=True),
        schema="semantic",
    )
    op.add_column(
        "canonical_snapshot",
        sa.Column("item_count", sa.Integer(), nullable=True),
        schema="semantic",
    )
    op.add_column(
        "canonical_snapshot",
        sa.Column("snapshot_payload_ref", sa.String(1024), nullable=True),
        schema="semantic",
    )
    op.add_column(
        "canonical_snapshot",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="semantic",
    )
    op.create_foreign_key(
        "fk_canonical_snapshot_reporting_period_id",
        "canonical_snapshot",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="semantic",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )

    # calculation_method_version
    op.add_column(
        "calculation_method_version",
        sa.Column("formula_hash", sa.String(128), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_method_version",
        sa.Column("method_document_uri", sa.String(1024), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_method_version",
        sa.Column("method_document_hash", sa.String(128), nullable=True),
        schema="calculation",
    )

    # calculation_execution
    op.add_column(
        "calculation_execution",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="calculation",
    )
    op.create_foreign_key(
        "fk_calculation_execution_reporting_period_id",
        "calculation_execution",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="calculation",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )

    # calculation_result_set
    op.add_column(
        "calculation_result_set",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("result_scope", _enum("result_scope"), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("consolidation_type", _enum("consolidation_type"), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "calculation_result_set",
        sa.Column("correction_reason", sa.String(), nullable=True),
        schema="calculation",
    )
    op.create_foreign_key(
        "fk_calculation_result_set_reporting_period_id",
        "calculation_result_set",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="calculation",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_calculation_result_set_supersedes_id",
        "calculation_result_set",
        "calculation_result_set",
        ["supersedes_id"],
        ["calculation_result_set_id"],
        source_schema="calculation",
        referent_schema="calculation",
        ondelete="RESTRICT",
    )

    # calculation_review
    op.add_column(
        "calculation_review",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="calculation",
    )
    op.create_foreign_key(
        "fk_calculation_review_reporting_period_id",
        "calculation_review",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="calculation",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )

    # result_publication_execution
    op.add_column(
        "result_publication_execution",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "result_publication_execution",
        sa.Column("publication_payload_hash", sa.String(128), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "result_publication_execution",
        sa.Column("ontology_resource_uri", sa.String(1024), nullable=True),
        schema="calculation",
    )
    op.add_column(
        "result_publication_execution",
        sa.Column("publication_version", sa.String(64), nullable=True),
        schema="calculation",
    )
    op.create_foreign_key(
        "fk_result_publication_execution_reporting_period_id",
        "result_publication_execution",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="calculation",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )

    # result_aggregation_link
    op.create_table(
        "result_aggregation_link",
        sa.Column(
            "calculation_result_aggregation_link_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("parent_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("child_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregation_type", _enum("aggregation_type"), nullable=False),
        sa.Column("parent_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("child_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint(
            "calculation_result_aggregation_link_id",
            name="pk_calculation_result_aggregation_link",
        ),
        sa.ForeignKeyConstraint(
            ["parent_result_set_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_result_aggregation_link_parent_result_set_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["child_result_set_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_result_aggregation_link_child_result_set_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_period_id"],
            ["reporting.period.reporting_period_id"],
            name="fk_result_aggregation_link_parent_period_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["child_period_id"],
            ["reporting.period.reporting_period_id"],
            name="fk_result_aggregation_link_child_period_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_aggregation_link_parent",
        "result_aggregation_link",
        ["parent_result_set_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_aggregation_link_child",
        "result_aggregation_link",
        ["child_result_set_id"],
        schema="calculation",
    )

    # hash_record
    op.add_column(
        "hash_record",
        sa.Column("hash_scope", _enum("hash_scope"), nullable=True),
        schema="audit",
    )
    op.add_column(
        "hash_record",
        sa.Column(
            "canonicalization_method",
            sa.String(64),
            nullable=True,
            server_default=sa.text("'json_canonical_v1'"),
        ),
        schema="audit",
    )
    op.add_column(
        "hash_record",
        sa.Column("canonical_payload_hash", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "hash_record",
        sa.Column("canonical_payload_ref", sa.String(1024), nullable=True),
        schema="audit",
    )
    op.add_column(
        "hash_record",
        sa.Column("created_by_service", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "hash_record",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        schema="audit",
    )

    # blockchain_anchor
    op.add_column(
        "blockchain_anchor",
        sa.Column("anchor_provider", sa.String(64), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("anchor_mode", _enum("anchor_mode"), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("evidence_package_external_id", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("package_hash", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("metadata_hash", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "blockchain_anchor",
        sa.Column("failed_reason", sa.String(), nullable=True),
        schema="audit",
    )

    # outbox_event evolution
    op.add_column(
        "outbox_event",
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("calculation_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("calculation_result_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("reporting_period_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("source_table", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("source_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("error_message", sa.String(), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("locked_by", sa.String(128), nullable=True),
        schema="audit",
    )
    op.add_column(
        "outbox_event",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        schema="audit",
    )
    op.create_foreign_key(
        "fk_outbox_event_pipeline_run_id",
        "outbox_event",
        "pipeline_run",
        ["pipeline_run_id"],
        ["pipeline_run_id"],
        source_schema="audit",
        referent_schema="pipeline",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_outbox_event_reporting_period_id",
        "outbox_event",
        "period",
        ["reporting_period_id"],
        ["reporting_period_id"],
        source_schema="audit",
        referent_schema="reporting",
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_outbox_event_pipeline_run_id",
        "outbox_event",
        ["pipeline_run_id"],
        schema="audit",
    )
    op.create_index(
        "ix_outbox_event_event_type",
        "outbox_event",
        ["event_type"],
        schema="audit",
    )

    for table in ("calculation_parameter_value", "result_aggregation_link"):
        op.execute(
            f"""
            CREATE TRIGGER trg_append_only_{table}
            BEFORE UPDATE OR DELETE ON calculation.{table}
            FOR EACH ROW EXECUTE FUNCTION audit.append_only_guard();
            """
        )


def downgrade() -> None:
    for table in ("result_aggregation_link", "calculation_parameter_value"):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_append_only_{table} ON calculation.{table}"
        )

    for ix in ("ix_outbox_event_event_type", "ix_outbox_event_pipeline_run_id"):
        op.drop_index(ix, table_name="outbox_event", schema="audit")

    for fk in (
        "fk_outbox_event_reporting_period_id",
        "fk_outbox_event_pipeline_run_id",
    ):
        op.drop_constraint(fk, "outbox_event", schema="audit", type_="foreignkey")

    for col in (
        "processed_at",
        "locked_by",
        "locked_at",
        "retry_count",
        "error_message",
        "source_record_id",
        "source_table",
        "reporting_period_id",
        "calculation_result_set_id",
        "calculation_execution_id",
        "pipeline_run_id",
    ):
        op.drop_column("outbox_event", col, schema="audit")

    for col in (
        "failed_reason",
        "confirmed_at",
        "submitted_at",
        "metadata_hash",
        "package_hash",
        "evidence_package_external_id",
        "anchor_mode",
        "anchor_provider",
    ):
        op.drop_column("blockchain_anchor", col, schema="audit")

    for col in (
        "created_at",
        "created_by_service",
        "canonical_payload_ref",
        "canonical_payload_hash",
        "canonicalization_method",
        "hash_scope",
    ):
        op.drop_column("hash_record", col, schema="audit")

    op.drop_index(
        "ix_calculation_result_aggregation_link_child",
        table_name="result_aggregation_link",
        schema="calculation",
    )
    op.drop_index(
        "ix_calculation_result_aggregation_link_parent",
        table_name="result_aggregation_link",
        schema="calculation",
    )
    op.drop_table("result_aggregation_link", schema="calculation")

    op.drop_constraint(
        "fk_result_publication_execution_reporting_period_id",
        "result_publication_execution",
        schema="calculation",
        type_="foreignkey",
    )
    for col in (
        "publication_version",
        "ontology_resource_uri",
        "publication_payload_hash",
        "reporting_period_id",
    ):
        op.drop_column("result_publication_execution", col, schema="calculation")

    op.drop_constraint(
        "fk_calculation_review_reporting_period_id",
        "calculation_review",
        schema="calculation",
        type_="foreignkey",
    )
    op.drop_column("calculation_review", "reporting_period_id", schema="calculation")

    op.drop_constraint(
        "fk_calculation_result_set_supersedes_id",
        "calculation_result_set",
        schema="calculation",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_calculation_result_set_reporting_period_id",
        "calculation_result_set",
        schema="calculation",
        type_="foreignkey",
    )
    for col in (
        "correction_reason",
        "supersedes_id",
        "published_at",
        "approved_at",
        "consolidation_type",
        "result_scope",
        "reporting_period_id",
    ):
        op.drop_column("calculation_result_set", col, schema="calculation")

    op.drop_constraint(
        "fk_calculation_execution_reporting_period_id",
        "calculation_execution",
        schema="calculation",
        type_="foreignkey",
    )
    op.drop_column("calculation_execution", "reporting_period_id", schema="calculation")

    for col in ("method_document_hash", "method_document_uri", "formula_hash"):
        op.drop_column("calculation_method_version", col, schema="calculation")

    op.drop_constraint(
        "fk_canonical_snapshot_reporting_period_id",
        "canonical_snapshot",
        schema="semantic",
        type_="foreignkey",
    )
    for col in (
        "reporting_period_id",
        "snapshot_payload_ref",
        "item_count",
        "canonical_schema_version",
    ):
        op.drop_column("canonical_snapshot", col, schema="semantic")

    for col in ("runtime_version", "execution_payload_hash"):
        op.drop_column("wrapper_execution", col, schema="pipeline")
    for col in ("output_schema_hash", "input_schema_hash", "wrapper_code_hash"):
        op.drop_column("wrapper_definition", col, schema="pipeline")

    op.drop_constraint(
        "fk_pipeline_run_reporting_period_id",
        "pipeline_run",
        schema="pipeline",
        type_="foreignkey",
    )
    for col in ("project_id_hash", "farm_id_hash", "reporting_period_id", "run_type"):
        op.drop_column("pipeline_run", col, schema="pipeline")

    op.drop_index("ix_reporting_period_granularity", table_name="period", schema="reporting")
    op.drop_index("ix_reporting_period_year_month", table_name="period", schema="reporting")
    op.drop_table("period", schema="reporting")

    for enum_name in reversed(list(NEW_ENUMS.keys())):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
