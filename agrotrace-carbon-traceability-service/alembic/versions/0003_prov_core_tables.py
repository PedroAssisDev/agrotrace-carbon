"""Create prov_core tables.

Revision ID: 0003_prov_core
Revises: 0002_pipeline_root
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_prov_core"
down_revision = "0002_pipeline_root"
branch_labels = None
depends_on = None


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "prov_agent",
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", _enum("prov_agent_type"), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("external_reference", sa.String(256), nullable=True),
        sa.Column("organization_name", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("agent_id", name="pk_prov_agent"),
        sa.UniqueConstraint(
            "agent_type",
            "external_reference",
            name="uq_prov_agent_agent_type_external_reference",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_agent_external_reference",
        "prov_agent",
        ["external_reference"],
        schema="prov_core",
    )

    op.create_table(
        "prov_bundle",
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_type", _enum("prov_bundle_type"), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("status", _enum("prov_bundle_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("bundle_id", name="pk_prov_bundle"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_prov_bundle_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_bundle_pipeline_run_id", "prov_bundle", ["pipeline_run_id"], schema="prov_core"
    )
    op.create_index("ix_prov_bundle_status", "prov_bundle", ["status"], schema="prov_core")

    op.create_table(
        "prov_entity",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", _enum("prov_entity_type"), nullable=False),
        sa.Column("entity_kind", sa.String(64), nullable=True),
        sa.Column("entity_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_key", sa.String(256), nullable=True),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("version_label", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("entity_id", name="pk_prov_entity"),
        sa.ForeignKeyConstraint(
            ["bundle_id"],
            ["prov_core.prov_bundle.bundle_id"],
            name="fk_prov_entity_bundle_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_prov_entity_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_entity_bundle_id", "prov_entity", ["bundle_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_entity_pipeline_run_id", "prov_entity", ["pipeline_run_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_entity_entity_type", "prov_entity", ["entity_type"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_entity_business_key", "prov_entity", ["business_key"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_entity_entity_ref",
        "prov_entity",
        ["entity_kind", "entity_ref_id"],
        schema="prov_core",
    )

    op.create_table(
        "prov_activity",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", _enum("prov_activity_type"), nullable=False),
        sa.Column("business_key", sa.String(256), nullable=True),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("software_version", sa.String(128), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("activity_id", name="pk_prov_activity"),
        sa.ForeignKeyConstraint(
            ["bundle_id"],
            ["prov_core.prov_bundle.bundle_id"],
            name="fk_prov_activity_bundle_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_prov_activity_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_activity_bundle_id", "prov_activity", ["bundle_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_activity_pipeline_run_id",
        "prov_activity",
        ["pipeline_run_id"],
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_activity_activity_type",
        "prov_activity",
        ["activity_type"],
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_activity_business_key",
        "prov_activity",
        ["business_key"],
        schema="prov_core",
    )

    op.create_table(
        "prov_used",
        sa.Column("used_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(128), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("used_id", name="pk_prov_used"),
        sa.UniqueConstraint(
            "activity_id",
            "entity_id",
            "role",
            name="uq_prov_used_activity_id_entity_id_role",
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_prov_used_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_used_entity_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index("ix_prov_used_entity_id", "prov_used", ["entity_id"], schema="prov_core")

    op.create_table(
        "prov_generated",
        sa.Column("generated_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("generated_id", name="pk_prov_generated"),
        sa.UniqueConstraint(
            "entity_id", "activity_id", name="uq_prov_generated_entity_id_activity_id"
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_generated_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_prov_generated_activity_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_generated_activity_id",
        "prov_generated",
        ["activity_id"],
        schema="prov_core",
    )

    op.create_table(
        "prov_derived_from",
        sa.Column("derived_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derivation_type", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("derived_id", name="pk_prov_derived_from"),
        sa.UniqueConstraint(
            "generated_entity_id",
            "source_entity_id",
            "derivation_type",
            name=(
                "uq_prov_derived_from_generated_entity_id_source_entity_id_"
                "derivation_type"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["generated_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_derived_from_generated_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_derived_from_source_entity_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_derived_from_source_entity_id",
        "prov_derived_from",
        ["source_entity_id"],
        schema="prov_core",
    )

    op.create_table(
        "prov_associated_with",
        sa.Column("association_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("association_id", name="pk_prov_associated_with"),
        sa.UniqueConstraint(
            "activity_id",
            "agent_id",
            "role",
            name="uq_prov_associated_with_activity_id_agent_id_role",
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_prov_associated_with_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["prov_core.prov_agent.agent_id"],
            name="fk_prov_associated_with_agent_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_associated_with_agent_id",
        "prov_associated_with",
        ["agent_id"],
        schema="prov_core",
    )

    op.create_table(
        "prov_revision",
        sa.Column("revision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_reason", sa.String, nullable=True),
        sa.Column("revised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("revision_id", name="pk_prov_revision"),
        sa.UniqueConstraint(
            "previous_entity_id",
            "new_entity_id",
            name="uq_prov_revision_previous_entity_id_new_entity_id",
        ),
        sa.ForeignKeyConstraint(
            ["previous_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_revision_previous_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["new_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_revision_new_entity_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_revision_new_entity_id",
        "prov_revision",
        ["new_entity_id"],
        schema="prov_core",
    )

    op.create_table(
        "prov_attribute",
        sa.Column("prov_attribute_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attr_key", sa.String(128), nullable=False),
        sa.Column("attr_value", postgresql.JSONB, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("prov_attribute_id", name="pk_prov_attribute"),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_prov_attribute_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_prov_attribute_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["prov_core.prov_agent.agent_id"],
            name="fk_prov_attribute_agent_id",
            ondelete="RESTRICT",
        ),
        schema="prov_core",
    )
    op.create_index(
        "ix_prov_attribute_entity_id", "prov_attribute", ["entity_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_attribute_activity_id", "prov_attribute", ["activity_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_attribute_agent_id", "prov_attribute", ["agent_id"], schema="prov_core"
    )
    op.create_index(
        "ix_prov_attribute_attr_key", "prov_attribute", ["attr_key"], schema="prov_core"
    )

    # Now wire pipeline_run.triggered_by_agent_id -> prov_agent (deferred FK).
    op.create_foreign_key(
        "fk_pipeline_run_triggered_by_agent_id",
        source_schema="pipeline",
        source_table="pipeline_run",
        referent_schema="prov_core",
        referent_table="prov_agent",
        local_cols=["triggered_by_agent_id"],
        remote_cols=["agent_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_pipeline_run_triggered_by_agent_id",
        "pipeline_run",
        schema="pipeline",
        type_="foreignkey",
    )
    for ix, table in [
        ("ix_prov_attribute_attr_key", "prov_attribute"),
        ("ix_prov_attribute_agent_id", "prov_attribute"),
        ("ix_prov_attribute_activity_id", "prov_attribute"),
        ("ix_prov_attribute_entity_id", "prov_attribute"),
    ]:
        op.drop_index(ix, table_name=table, schema="prov_core")
    op.drop_table("prov_attribute", schema="prov_core")
    op.drop_index("ix_prov_revision_new_entity_id", table_name="prov_revision", schema="prov_core")
    op.drop_table("prov_revision", schema="prov_core")
    op.drop_index(
        "ix_prov_associated_with_agent_id",
        table_name="prov_associated_with",
        schema="prov_core",
    )
    op.drop_table("prov_associated_with", schema="prov_core")
    op.drop_index(
        "ix_prov_derived_from_source_entity_id",
        table_name="prov_derived_from",
        schema="prov_core",
    )
    op.drop_table("prov_derived_from", schema="prov_core")
    op.drop_index(
        "ix_prov_generated_activity_id", table_name="prov_generated", schema="prov_core"
    )
    op.drop_table("prov_generated", schema="prov_core")
    op.drop_index("ix_prov_used_entity_id", table_name="prov_used", schema="prov_core")
    op.drop_table("prov_used", schema="prov_core")
    for ix in [
        "ix_prov_activity_business_key",
        "ix_prov_activity_activity_type",
        "ix_prov_activity_pipeline_run_id",
        "ix_prov_activity_bundle_id",
    ]:
        op.drop_index(ix, table_name="prov_activity", schema="prov_core")
    op.drop_table("prov_activity", schema="prov_core")
    for ix in [
        "ix_prov_entity_entity_ref",
        "ix_prov_entity_business_key",
        "ix_prov_entity_entity_type",
        "ix_prov_entity_pipeline_run_id",
        "ix_prov_entity_bundle_id",
    ]:
        op.drop_index(ix, table_name="prov_entity", schema="prov_core")
    op.drop_table("prov_entity", schema="prov_core")
    op.drop_index("ix_prov_bundle_status", table_name="prov_bundle", schema="prov_core")
    op.drop_index(
        "ix_prov_bundle_pipeline_run_id", table_name="prov_bundle", schema="prov_core"
    )
    op.drop_table("prov_bundle", schema="prov_core")
    op.drop_index(
        "ix_prov_agent_external_reference", table_name="prov_agent", schema="prov_core"
    )
    op.drop_table("prov_agent", schema="prov_core")
