"""Create pipeline.pipeline_run (parent only — child tables defer to 0004).

Revision ID: 0002_pipeline_root
Revises: 0001_schemas_enums
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_pipeline_root"
down_revision = "0001_schemas_enums"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run",
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_code", sa.String(128), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("farm_reference", sa.String(128), nullable=False),
        sa.Column("reporting_period_reference", sa.String(64), nullable=False),
        sa.Column(
            "run_status",
            postgresql.ENUM(name="pipeline_run_status", create_type=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triggered_by_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("pipeline_run_id", name="pk_pipeline_run"),
        sa.UniqueConstraint("run_code", name="uq_pipeline_run_run_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_pipeline_run_idempotency_key"),
        sa.ForeignKeyConstraint(
            ["parent_pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_pipeline_run_parent_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_pipeline_run_finished_at_ge_started_at",
        ),
        schema="pipeline",
    )
    op.create_index(
        "ix_pipeline_run_farm_period",
        "pipeline_run",
        ["farm_reference", "reporting_period_reference"],
        schema="pipeline",
    )
    op.create_index(
        "ix_pipeline_run_status_started_at",
        "pipeline_run",
        ["run_status", "started_at"],
        schema="pipeline",
    )
    op.create_index(
        "ix_pipeline_run_metadata_gin",
        "pipeline_run",
        ["metadata"],
        postgresql_using="gin",
        schema="pipeline",
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_metadata_gin", table_name="pipeline_run", schema="pipeline")
    op.drop_index(
        "ix_pipeline_run_status_started_at", table_name="pipeline_run", schema="pipeline"
    )
    op.drop_index("ix_pipeline_run_farm_period", table_name="pipeline_run", schema="pipeline")
    op.drop_table("pipeline_run", schema="pipeline")
