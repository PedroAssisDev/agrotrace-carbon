"""Create calculation tables.

Revision ID: 0006_calculation
Revises: 0005_semantic
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_calculation"
down_revision = "0005_semantic"
branch_labels = None
depends_on = None


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "calculation_method",
        sa.Column("calculation_method_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method_code", sa.String(64), nullable=False),
        sa.Column("method_name", sa.String(256), nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("calculation_method_id", name="pk_calculation_method"),
        sa.UniqueConstraint("method_code", name="uq_calculation_method_method_code"),
        schema="calculation",
    )

    op.create_table(
        "calculation_method_version",
        sa.Column("calculation_method_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_method_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_label", sa.String(64), nullable=False),
        sa.Column("formula_reference", sa.String(256), nullable=True),
        sa.Column("implementation_version", sa.String(64), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _enum("calculation_method_status"), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint(
            "calculation_method_version_id", name="pk_calculation_method_version"
        ),
        sa.UniqueConstraint(
            "calculation_method_id",
            "version_label",
            name="uq_calculation_method_version_calculation_method_id_version_label",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_method_id"],
            ["calculation.calculation_method.calculation_method_id"],
            name="fk_calculation_method_version_calculation_method_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_method_version_calculation_method_id",
        "calculation_method_version",
        ["calculation_method_id"],
        schema="calculation",
    )

    op.create_table(
        "calculation_parameter_set",
        sa.Column("calculation_parameter_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_method_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_set_status", _enum("parameter_set_status"), nullable=False),
        sa.Column("created_by_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint(
            "calculation_parameter_set_id", name="pk_calculation_parameter_set"
        ),
        sa.UniqueConstraint("prov_entity_id", name="uq_calculation_parameter_set_prov_entity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_calculation_parameter_set_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_calculation_parameter_set_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_method_version_id"],
            ["calculation.calculation_method_version.calculation_method_version_id"],
            name="fk_calculation_parameter_set_calculation_method_version_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_agent_id"],
            ["prov_core.prov_agent.agent_id"],
            name="fk_calculation_parameter_set_created_by_agent_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_parameter_set_pipeline_run_id",
        "calculation_parameter_set",
        ["pipeline_run_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_parameter_set_method_version_id",
        "calculation_parameter_set",
        ["calculation_method_version_id"],
        schema="calculation",
    )

    op.create_table(
        "calculation_parameter_value",
        sa.Column("calculation_parameter_value_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_parameter_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parameter_name", sa.String(128), nullable=False),
        sa.Column("parameter_value_text", sa.String, nullable=True),
        sa.Column("parameter_value_numeric", sa.Numeric(38, 12), nullable=True),
        sa.Column("parameter_unit", sa.String(64), nullable=True),
        sa.Column("parameter_source", sa.String(128), nullable=True),
        sa.Column(
            "is_user_editable", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint(
            "calculation_parameter_value_id", name="pk_calculation_parameter_value"
        ),
        sa.ForeignKeyConstraint(
            ["calculation_parameter_set_id"],
            ["calculation.calculation_parameter_set.calculation_parameter_set_id"],
            name="fk_calculation_parameter_value_calculation_parameter_set_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_parameter_value_calculation_parameter_set_id",
        "calculation_parameter_value",
        ["calculation_parameter_set_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_parameter_value_parameter_name",
        "calculation_parameter_value",
        ["parameter_name"],
        schema="calculation",
    )

    op.create_table(
        "calculation_execution",
        sa.Column("calculation_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_method_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_parameter_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_status", _enum("calculation_execution_status"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_log_uri", sa.String(1024), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("calculation_execution_id", name="pk_calculation_execution"),
        sa.UniqueConstraint("idempotency_key", name="uq_calculation_execution_idempotency_key"),
        sa.UniqueConstraint("prov_activity_id", name="uq_calculation_execution_prov_activity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_calculation_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_calculation_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_snapshot_id"],
            ["semantic.canonical_snapshot.canonical_snapshot_id"],
            name="fk_calculation_execution_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_method_version_id"],
            ["calculation.calculation_method_version.calculation_method_version_id"],
            name="fk_calculation_execution_calculation_method_version_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_parameter_set_id"],
            ["calculation.calculation_parameter_set.calculation_parameter_set_id"],
            name="fk_calculation_execution_calculation_parameter_set_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_calculation_execution_finished_at_ge_started_at",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_execution_pipeline_run_id",
        "calculation_execution",
        ["pipeline_run_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_execution_canonical_snapshot_id",
        "calculation_execution",
        ["canonical_snapshot_id"],
        schema="calculation",
    )

    op.create_table(
        "calculation_result_set",
        sa.Column("calculation_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_set_status", _enum("calculation_result_set_status"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_hash", sa.String(128), nullable=True),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("calculation_result_set_id", name="pk_calculation_result_set"),
        sa.UniqueConstraint("prov_entity_id", name="uq_calculation_result_set_prov_entity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_calculation_result_set_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_calculation_result_set_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_execution_id"],
            ["calculation.calculation_execution.calculation_execution_id"],
            name="fk_calculation_result_set_calculation_execution_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_calculation_result_set_superseded_by_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_set_pipeline_run_id",
        "calculation_result_set",
        ["pipeline_run_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_set_calculation_execution_id",
        "calculation_result_set",
        ["calculation_execution_id"],
        schema="calculation",
    )

    op.create_table(
        "calculation_result_item",
        sa.Column("calculation_result_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_type", _enum("calculation_result_type"), nullable=False),
        sa.Column("result_name", sa.String(256), nullable=False),
        sa.Column("result_value", sa.Numeric(38, 12), nullable=False),
        sa.Column("result_unit", sa.String(64), nullable=False),
        sa.Column("dimension_reference", sa.String(256), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("calculation_result_item_id", name="pk_calculation_result_item"),
        sa.ForeignKeyConstraint(
            ["calculation_result_set_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_calculation_result_item_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_item_calculation_result_set_id",
        "calculation_result_item",
        ["calculation_result_set_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_result_item_result_type",
        "calculation_result_item",
        ["result_type"],
        schema="calculation",
    )

    op.create_table(
        "calculation_review",
        sa.Column("calculation_review_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", _enum("calculation_review_decision"), nullable=False),
        sa.Column("review_comment", sa.String, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_uri", sa.String(1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("calculation_review_id", name="pk_calculation_review"),
        sa.UniqueConstraint("prov_activity_id", name="uq_calculation_review_prov_activity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_calculation_review_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_calculation_review_prov_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_result_set_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_calculation_review_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_agent_id"],
            ["prov_core.prov_agent.agent_id"],
            name="fk_calculation_review_reviewer_agent_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_review_pipeline_run_id",
        "calculation_review",
        ["pipeline_run_id"],
        schema="calculation",
    )
    op.create_index(
        "ix_calculation_review_calculation_result_set_id",
        "calculation_review",
        ["calculation_result_set_id"],
        schema="calculation",
    )

    op.create_table(
        "result_publication_execution",
        sa.Column(
            "result_publication_execution_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_result_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calculation_review_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_graph_name", sa.String(256), nullable=False),
        sa.Column("ontology_name", sa.String(128), nullable=False),
        sa.Column("ontology_version", sa.String(64), nullable=False),
        sa.Column("publication_status", _enum("result_publication_status"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint(
            "result_publication_execution_id", name="pk_result_publication_execution"
        ),
        sa.UniqueConstraint(
            "prov_activity_id", name="uq_result_publication_execution_prov_activity_id"
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_result_publication_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_result_publication_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_result_set_id"],
            ["calculation.calculation_result_set.calculation_result_set_id"],
            name="fk_result_publication_execution_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_review_id"],
            ["calculation.calculation_review.calculation_review_id"],
            name="fk_result_publication_execution_calculation_review_id",
            ondelete="RESTRICT",
        ),
        schema="calculation",
    )
    op.create_index(
        "ix_result_publication_execution_pipeline_run_id",
        "result_publication_execution",
        ["pipeline_run_id"],
        schema="calculation",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_result_publication_execution_pipeline_run_id",
        table_name="result_publication_execution",
        schema="calculation",
    )
    op.drop_table("result_publication_execution", schema="calculation")
    for ix in [
        "ix_calculation_review_calculation_result_set_id",
        "ix_calculation_review_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="calculation_review", schema="calculation")
    op.drop_table("calculation_review", schema="calculation")
    for ix in [
        "ix_calculation_result_item_result_type",
        "ix_calculation_result_item_calculation_result_set_id",
    ]:
        op.drop_index(ix, table_name="calculation_result_item", schema="calculation")
    op.drop_table("calculation_result_item", schema="calculation")
    for ix in [
        "ix_calculation_result_set_calculation_execution_id",
        "ix_calculation_result_set_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="calculation_result_set", schema="calculation")
    op.drop_table("calculation_result_set", schema="calculation")
    for ix in [
        "ix_calculation_execution_canonical_snapshot_id",
        "ix_calculation_execution_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="calculation_execution", schema="calculation")
    op.drop_table("calculation_execution", schema="calculation")
    for ix in [
        "ix_calculation_parameter_value_parameter_name",
        "ix_calculation_parameter_value_calculation_parameter_set_id",
    ]:
        op.drop_index(ix, table_name="calculation_parameter_value", schema="calculation")
    op.drop_table("calculation_parameter_value", schema="calculation")
    for ix in [
        "ix_calculation_parameter_set_method_version_id",
        "ix_calculation_parameter_set_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="calculation_parameter_set", schema="calculation")
    op.drop_table("calculation_parameter_set", schema="calculation")
    op.drop_index(
        "ix_calculation_method_version_calculation_method_id",
        table_name="calculation_method_version",
        schema="calculation",
    )
    op.drop_table("calculation_method_version", schema="calculation")
    op.drop_table("calculation_method", schema="calculation")
