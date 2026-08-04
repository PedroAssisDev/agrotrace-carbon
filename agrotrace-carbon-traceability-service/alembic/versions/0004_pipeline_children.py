"""Create pipeline child tables (source_artifact, wrapper_*, normalized_batch).

Revision ID: 0004_pipeline_children
Revises: 0003_prov_core
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_pipeline_children"
down_revision = "0003_prov_core"
branch_labels = None
depends_on = None


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "source_artifact",
        sa.Column("source_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_system", sa.String(128), nullable=False),
        sa.Column("source_layout_name", sa.String(128), nullable=True),
        sa.Column("source_layout_version", sa.String(64), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_uri", sa.String(1024), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("source_artifact_id", name="pk_source_artifact"),
        sa.UniqueConstraint("idempotency_key", name="uq_source_artifact_idempotency_key"),
        sa.UniqueConstraint("prov_entity_id", name="uq_source_artifact_prov_entity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_source_artifact_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_source_artifact_prov_entity_id",
            ondelete="RESTRICT",
        ),
        schema="pipeline",
    )
    op.create_index(
        "ix_source_artifact_pipeline_run_id",
        "source_artifact",
        ["pipeline_run_id"],
        schema="pipeline",
    )
    op.create_index(
        "ix_source_artifact_content_hash",
        "source_artifact",
        ["content_hash"],
        schema="pipeline",
    )

    op.create_table(
        "wrapper_definition",
        sa.Column("wrapper_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wrapper_name", sa.String(128), nullable=False),
        sa.Column("wrapper_version", sa.String(64), nullable=False),
        sa.Column("source_layout_name", sa.String(128), nullable=False),
        sa.Column("source_layout_version", sa.String(64), nullable=True),
        sa.Column("schema_version", sa.String(64), nullable=True),
        sa.Column("code_hash", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("wrapper_definition_id", name="pk_wrapper_definition"),
        sa.UniqueConstraint(
            "wrapper_name",
            "wrapper_version",
            name="uq_wrapper_definition_wrapper_name_wrapper_version",
        ),
        schema="pipeline",
    )
    op.create_index(
        "ix_wrapper_definition_layout",
        "wrapper_definition",
        ["source_layout_name", "source_layout_version"],
        schema="pipeline",
    )

    op.create_table(
        "wrapper_execution",
        sa.Column("wrapper_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wrapper_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_status", _enum("wrapper_execution_status"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warning_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("execution_log_uri", sa.String(1024), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("wrapper_execution_id", name="pk_wrapper_execution"),
        sa.UniqueConstraint("idempotency_key", name="uq_wrapper_execution_idempotency_key"),
        sa.UniqueConstraint("prov_activity_id", name="uq_wrapper_execution_prov_activity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_wrapper_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_wrapper_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wrapper_definition_id"],
            ["pipeline.wrapper_definition.wrapper_definition_id"],
            name="fk_wrapper_execution_wrapper_definition_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["input_artifact_id"],
            ["pipeline.source_artifact.source_artifact_id"],
            name="fk_wrapper_execution_input_artifact_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_wrapper_execution_finished_at_ge_started_at",
        ),
        sa.CheckConstraint("warning_count >= 0", name="ck_wrapper_execution_warning_count_ge_0"),
        sa.CheckConstraint("error_count >= 0", name="ck_wrapper_execution_error_count_ge_0"),
        schema="pipeline",
    )
    op.create_index(
        "ix_wrapper_execution_pipeline_run_id",
        "wrapper_execution",
        ["pipeline_run_id"],
        schema="pipeline",
    )

    op.create_table(
        "normalized_batch",
        sa.Column("normalized_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wrapper_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_code", sa.String(128), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("record_count", sa.Integer, nullable=False),
        sa.Column("storage_uri", sa.String(1024), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("normalized_batch_id", name="pk_normalized_batch"),
        sa.UniqueConstraint("idempotency_key", name="uq_normalized_batch_idempotency_key"),
        sa.UniqueConstraint("prov_entity_id", name="uq_normalized_batch_prov_entity_id"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_normalized_batch_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_normalized_batch_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["wrapper_execution_id"],
            ["pipeline.wrapper_execution.wrapper_execution_id"],
            name="fk_normalized_batch_wrapper_execution_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("record_count >= 0", name="ck_normalized_batch_record_count_ge_0"),
        schema="pipeline",
    )
    op.create_index(
        "ix_normalized_batch_pipeline_run_id",
        "normalized_batch",
        ["pipeline_run_id"],
        schema="pipeline",
    )
    op.create_index(
        "ix_normalized_batch_wrapper_execution_id",
        "normalized_batch",
        ["wrapper_execution_id"],
        schema="pipeline",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_normalized_batch_wrapper_execution_id",
        table_name="normalized_batch",
        schema="pipeline",
    )
    op.drop_index(
        "ix_normalized_batch_pipeline_run_id",
        table_name="normalized_batch",
        schema="pipeline",
    )
    op.drop_table("normalized_batch", schema="pipeline")
    op.drop_index(
        "ix_wrapper_execution_pipeline_run_id",
        table_name="wrapper_execution",
        schema="pipeline",
    )
    op.drop_table("wrapper_execution", schema="pipeline")
    op.drop_index(
        "ix_wrapper_definition_layout",
        table_name="wrapper_definition",
        schema="pipeline",
    )
    op.drop_table("wrapper_definition", schema="pipeline")
    op.drop_index(
        "ix_source_artifact_content_hash",
        table_name="source_artifact",
        schema="pipeline",
    )
    op.drop_index(
        "ix_source_artifact_pipeline_run_id",
        table_name="source_artifact",
        schema="pipeline",
    )
    op.drop_table("source_artifact", schema="pipeline")
