"""Create audit tables and append-only triggers.

Revision ID: 0007_audit_appendonly
Revises: 0006_calculation
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_audit_appendonly"
down_revision = "0006_calculation"
branch_labels = None
depends_on = None

APPEND_ONLY_TABLES: tuple[tuple[str, str], ...] = (
    ("prov_core", "prov_bundle"),
    ("prov_core", "prov_entity"),
    ("prov_core", "prov_activity"),
    ("prov_core", "prov_agent"),
    ("prov_core", "prov_used"),
    ("prov_core", "prov_generated"),
    ("prov_core", "prov_derived_from"),
    ("prov_core", "prov_associated_with"),
    ("prov_core", "prov_revision"),
    ("prov_core", "prov_attribute"),
    ("pipeline", "source_artifact"),
    ("pipeline", "wrapper_execution"),
    ("pipeline", "normalized_batch"),
    ("semantic", "semantic_integration_execution"),
    ("semantic", "canonical_snapshot"),
    ("semantic", "canonical_snapshot_item"),
    ("semantic", "ontology_resource_link"),
    ("calculation", "calculation_execution"),
    ("calculation", "calculation_result_item"),
    ("calculation", "calculation_review"),
    ("audit", "hash_record"),
    ("audit", "audit_event"),
)

# Mutable tables: pipeline_run (status updates), wrapper_definition (is_active),
# calculation_method/version, calculation_parameter_set (status), calculation_result_set
# (status + superseded_by), result_publication_execution (status), blockchain_anchor
# (anchor lifecycle), outbox_event (status + published_at).


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False)


def upgrade() -> None:
    op.create_table(
        "hash_record",
        sa.Column("hash_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prov_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_kind", _enum("hash_subject_kind"), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hash_algorithm", _enum("hash_algorithm"), nullable=False),
        sa.Column("hash_value", sa.String(128), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("computed_by_version", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("hash_record_id", name="pk_hash_record"),
        sa.UniqueConstraint(
            "subject_kind",
            "subject_id",
            "hash_algorithm",
            name="uq_hash_record_subject_kind_subject_id_hash_algorithm",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_hash_record_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prov_entity_id"],
            ["prov_core.prov_entity.entity_id"],
            name="fk_hash_record_prov_entity_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bundle_id"],
            ["prov_core.prov_bundle.bundle_id"],
            name="fk_hash_record_bundle_id",
            ondelete="RESTRICT",
        ),
        schema="audit",
    )
    op.create_index(
        "ix_hash_record_pipeline_run_id", "hash_record", ["pipeline_run_id"], schema="audit"
    )
    op.create_index("ix_hash_record_subject_id", "hash_record", ["subject_id"], schema="audit")
    op.create_index("ix_hash_record_hash_value", "hash_record", ["hash_value"], schema="audit")

    op.create_table(
        "blockchain_anchor",
        sa.Column("blockchain_anchor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hash_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blockchain_network", sa.String(64), nullable=False),
        sa.Column("chain_id", sa.String(64), nullable=True),
        sa.Column("transaction_hash", sa.String(128), nullable=True),
        sa.Column("block_number", sa.String(64), nullable=True),
        sa.Column("anchor_status", _enum("blockchain_anchor_status"), nullable=False),
        sa.Column("merkle_root", sa.String(128), nullable=True),
        sa.Column("confirmations", sa.Integer, nullable=True),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_uri", sa.String(1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("blockchain_anchor_id", name="pk_blockchain_anchor"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline.pipeline_run.pipeline_run_id"],
            name="fk_blockchain_anchor_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["hash_record_id"],
            ["audit.hash_record.hash_record_id"],
            name="fk_blockchain_anchor_hash_record_id",
            ondelete="RESTRICT",
        ),
        schema="audit",
    )
    op.create_index(
        "ix_blockchain_anchor_pipeline_run_id",
        "blockchain_anchor",
        ["pipeline_run_id"],
        schema="audit",
    )
    op.create_index(
        "ix_blockchain_anchor_hash_record_id",
        "blockchain_anchor",
        ["hash_record_id"],
        schema="audit",
    )
    op.create_index(
        "ix_blockchain_anchor_status",
        "blockchain_anchor",
        ["anchor_status"],
        schema="audit",
    )

    op.create_table(
        "outbox_event",
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_kind", sa.String(64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _enum("outbox_status"), nullable=False),
        sa.PrimaryKeyConstraint("outbox_event_id", name="pk_outbox_event"),
        schema="audit",
    )
    op.create_index(
        "ix_outbox_event_status_created_at",
        "outbox_event",
        ["status", "created_at"],
        schema="audit",
    )
    op.create_index(
        "ix_outbox_event_aggregate",
        "outbox_event",
        ["aggregate_kind", "aggregate_id"],
        schema="audit",
    )

    op.create_table(
        "audit_event",
        sa.Column("audit_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("actor_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_kind", sa.String(64), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("audit_event_id", name="pk_audit_event"),
        sa.ForeignKeyConstraint(
            ["actor_agent_id"],
            ["prov_core.prov_agent.agent_id"],
            name="fk_audit_event_actor_agent_id",
            ondelete="RESTRICT",
        ),
        schema="audit",
    )
    op.create_index(
        "ix_audit_event_subject",
        "audit_event",
        ["subject_kind", "subject_id"],
        schema="audit",
    )
    op.create_index(
        "ix_audit_event_recorded_at",
        "audit_event",
        ["recorded_at"],
        schema="audit",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.append_only_guard()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'UPDATE') THEN
                RAISE EXCEPTION
                    'Append-only violation: UPDATE is not permitted on %.%',
                    TG_TABLE_SCHEMA, TG_TABLE_NAME
                    USING ERRCODE = '23514';
            ELSIF (TG_OP = 'DELETE') THEN
                RAISE EXCEPTION
                    'Append-only violation: DELETE is not permitted on %.%',
                    TG_TABLE_SCHEMA, TG_TABLE_NAME
                    USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for schema, table in APPEND_ONLY_TABLES:
        trigger_name = f"trg_append_only_{table}"
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE OR DELETE ON {schema}.{table}
            FOR EACH ROW EXECUTE FUNCTION audit.append_only_guard();
            """
        )


def downgrade() -> None:
    for schema, table in APPEND_ONLY_TABLES:
        trigger_name = f"trg_append_only_{table}"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {schema}.{table}")
    op.execute("DROP FUNCTION IF EXISTS audit.append_only_guard()")

    for ix in ["ix_audit_event_recorded_at", "ix_audit_event_subject"]:
        op.drop_index(ix, table_name="audit_event", schema="audit")
    op.drop_table("audit_event", schema="audit")
    for ix in ["ix_outbox_event_aggregate", "ix_outbox_event_status_created_at"]:
        op.drop_index(ix, table_name="outbox_event", schema="audit")
    op.drop_table("outbox_event", schema="audit")
    for ix in [
        "ix_blockchain_anchor_status",
        "ix_blockchain_anchor_hash_record_id",
        "ix_blockchain_anchor_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="blockchain_anchor", schema="audit")
    op.drop_table("blockchain_anchor", schema="audit")
    for ix in [
        "ix_hash_record_hash_value",
        "ix_hash_record_subject_id",
        "ix_hash_record_pipeline_run_id",
    ]:
        op.drop_index(ix, table_name="hash_record", schema="audit")
    op.drop_table("hash_record", schema="audit")
