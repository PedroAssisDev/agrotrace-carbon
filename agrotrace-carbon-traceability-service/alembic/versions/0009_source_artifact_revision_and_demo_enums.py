"""Source artifact revision table, wrapper_execution FK, enum extensions, append-only.

Revision ID: 0009_source_revision
Revises: 0008_demo_enum_extensions
Create Date: 2026-04-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_source_revision"
down_revision = "0008_demo_enum_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE prov_entity_type ADD VALUE IF NOT EXISTS 'source_artifact_revision'"
    )
    op.execute(
        "ALTER TYPE publication_stage ADD VALUE IF NOT EXISTS 'publication_final'"
    )
    op.execute(
        "ALTER TYPE calculation_result_type ADD VALUE IF NOT EXISTS 'ghg_emission'"
    )
    op.execute(
        "ALTER TYPE calculation_result_type ADD VALUE IF NOT EXISTS 'carbon_footprint'"
    )
    op.execute(
        "ALTER TYPE hash_subject_kind ADD VALUE IF NOT EXISTS 'source_artifact_revision'"
    )

    op.create_table(
        "source_artifact_revision",
        sa.Column("source_artifact_revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_artifact_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.String(1024), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint(
            "source_artifact_revision_id", name="pk_source_artifact_revision"
        ),
        sa.UniqueConstraint(
            "source_artifact_id",
            "revision_number",
            name="uq_source_artifact_revision_artifact_revision_number",
        ),
        sa.ForeignKeyConstraint(
            ["source_artifact_id"],
            ["pipeline.source_artifact.source_artifact_id"],
            name="fk_source_artifact_revision_source_artifact_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_source_artifact_revision_prov_entity_id",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        schema="pipeline",
    )
    op.create_index(
        "ix_source_artifact_revision_source_artifact_id",
        "source_artifact_revision",
        ["source_artifact_id"],
        schema="pipeline",
    )

    op.add_column(
        "wrapper_execution",
        sa.Column(
            "input_source_artifact_revision_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="pipeline",
    )
    op.create_foreign_key(
        "fk_wrapper_execution_input_source_artifact_revision_id",
        "wrapper_execution",
        "source_artifact_revision",
        ["input_source_artifact_revision_id"],
        ["source_artifact_revision_id"],
        source_schema="pipeline",
        referent_schema="pipeline",
        ondelete="RESTRICT",
    )

    op.execute(
        """
        CREATE TRIGGER trg_append_only_source_artifact_revision
        BEFORE UPDATE OR DELETE ON pipeline.source_artifact_revision
        FOR EACH ROW EXECUTE FUNCTION audit.append_only_guard();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_append_only_source_artifact_revision "
        "ON pipeline.source_artifact_revision"
    )
    op.drop_constraint(
        "fk_wrapper_execution_input_source_artifact_revision_id",
        "wrapper_execution",
        schema="pipeline",
        type_="foreignkey",
    )
    op.drop_column(
        "wrapper_execution",
        "input_source_artifact_revision_id",
        schema="pipeline",
    )
    op.drop_index(
        "ix_source_artifact_revision_source_artifact_id",
        table_name="source_artifact_revision",
        schema="pipeline",
    )
    op.drop_table("source_artifact_revision", schema="pipeline")
