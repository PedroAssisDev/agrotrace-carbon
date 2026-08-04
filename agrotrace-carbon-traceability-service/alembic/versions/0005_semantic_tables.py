"""Create semantic tables.

Revision ID: 0005_semantic
Revises: 0004_pipeline_children
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_semantic"
down_revision = "0004_pipeline_children"
branch_labels = None
depends_on = None


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "semantic_integration_execution",
        sa.Column(
            "semantic_integration_execution_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ontology_name", sa.String(128), nullable=False),
        sa.Column("ontology_version", sa.String(64), nullable=False),
        sa.Column("mapping_rule_version", sa.String(64), nullable=False),
        sa.Column("execution_status", _enum("semantic_execution_status"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triples_generated", sa.Integer, nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint(
            "semantic_integration_execution_id", name="pk_semantic_integration_execution"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_semantic_integration_execution_idempotency_key"
        ),
        sa.UniqueConstraint(
            "prov_activity_id", name="uq_semantic_integration_execution_prov_activity_id"
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_semantic_integration_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_activity_id"],
            ["prov_core.prov_activity.activity_id"],
            name="fk_semantic_integration_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["normalized_batch_id"],
            ["pipeline.normalized_batch.normalized_batch_id"],
            name="fk_semantic_integration_execution_normalized_batch_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_semantic_integration_execution_finished_at_ge_started_at",
        ),
        schema="semantic",
    )
    op.create_index(
        "ix_semantic_integration_execution_pipeline_run_id",
        "semantic_integration_execution",
        ["pipeline_run_id"],
        schema="semantic",
    )

    op.create_table(
        "canonical_snapshot",
        sa.Column("canonical_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "semantic_integration_execution_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("graph_name", sa.String(256), nullable=False),
        sa.Column("snapshot_label", sa.String(256), nullable=False),
        sa.Column("snapshot_hash", sa.String(128), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=True),
        sa.Column("storage_uri", sa.String(1024), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("canonical_snapshot_id", name="pk_canonical_snapshot"),
        sa.UniqueConstraint("prov_entity_id", name="uq_canonical_snapshot_prov_entity_id"),
        sa.UniqueConstraint("snapshot_hash", name="uq_canonical_snapshot_snapshot_hash"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_canonical_snapshot_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_canonical_snapshot_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semantic_integration_execution_id"],
            [
                "semantic.semantic_integration_execution."
                "semantic_integration_execution_id"
            ],
            name="fk_canonical_snapshot_semantic_integration_execution_id",
            ondelete="RESTRICT",
        ),
        schema="semantic",
    )
    op.create_index(
        "ix_canonical_snapshot_pipeline_run_id",
        "canonical_snapshot",
        ["pipeline_run_id"],
        schema="semantic",
    )
    op.create_index(
        "ix_canonical_snapshot_graph_name",
        "canonical_snapshot",
        ["graph_name"],
        schema="semantic",
    )

    op.create_table(
        "canonical_snapshot_item",
        sa.Column("canonical_snapshot_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_key", sa.String(256), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("item_hash", sa.String(128), nullable=True),
        sa.PrimaryKeyConstraint("canonical_snapshot_item_id", name="pk_canonical_snapshot_item"),
        sa.ForeignKeyConstraint(
            ["canonical_snapshot_id"],
            ["semantic.canonical_snapshot.canonical_snapshot_id"],
            name="fk_canonical_snapshot_item_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        schema="semantic",
    )
    op.create_index(
        "ix_canonical_snapshot_item_canonical_snapshot_id",
        "canonical_snapshot_item",
        ["canonical_snapshot_id"],
        schema="semantic",
    )
    op.create_index(
        "ix_canonical_snapshot_item_item_key",
        "canonical_snapshot_item",
        ["item_key"],
        schema="semantic",
    )

    op.create_table(
        "ontology_resource_link",
        sa.Column("ontology_resource_link_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canonical_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ontology_uri", sa.String(1024), nullable=False),
        sa.Column("rdf_class", sa.String(256), nullable=True),
        sa.Column("graph_name", sa.String(256), nullable=False),
        sa.Column("ontology_version", sa.String(64), nullable=True),
        sa.Column("publication_stage", _enum("publication_stage"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("ontology_resource_link_id", name="pk_ontology_resource_link"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_ontology_resource_link_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_ontology_resource_link_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_snapshot_id"],
            ["semantic.canonical_snapshot.canonical_snapshot_id"],
            name="fk_ontology_resource_link_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        schema="semantic",
    )
    op.create_index(
        "ix_ontology_resource_link_pipeline_run_id",
        "ontology_resource_link",
        ["pipeline_run_id"],
        schema="semantic",
    )
    op.create_index(
        "ix_ontology_resource_link_ontology_uri",
        "ontology_resource_link",
        ["ontology_uri"],
        schema="semantic",
    )
    op.create_index(
        "ix_ontology_resource_link_canonical_snapshot_id",
        "ontology_resource_link",
        ["canonical_snapshot_id"],
        schema="semantic",
    )


def downgrade() -> None:
    for ix in [
        "ix_ontology_resource_link_canonical_snapshot_id",
        "ix_ontology_resource_link_ontology_uri",
        "ix_ontology_resource_link_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="ontology_resource_link", schema="semantic")
    op.drop_table("ontology_resource_link", schema="semantic")
    for ix in [
        "ix_canonical_snapshot_item_item_key",
        "ix_canonical_snapshot_item_canonical_snapshot_id",
    ]:
        op.drop_index(ix, table_name="canonical_snapshot_item", schema="semantic")
    op.drop_table("canonical_snapshot_item", schema="semantic")
    for ix in [
        "ix_canonical_snapshot_graph_name",
        "ix_canonical_snapshot_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="canonical_snapshot", schema="semantic")
    op.drop_table("canonical_snapshot", schema="semantic")
    op.drop_index(
        "ix_semantic_integration_execution_pipeline_run_id",
        table_name="semantic_integration_execution",
        schema="semantic",
    )
    op.drop_table("semantic_integration_execution", schema="semantic")
