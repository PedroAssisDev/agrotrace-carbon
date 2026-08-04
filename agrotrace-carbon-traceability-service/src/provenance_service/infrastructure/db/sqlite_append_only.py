"""SQLite append-only triggers for the provenance ledger.

Physical table names use bounded-context prefixes (``pipeline_*``, ``prov_core_*``, …)
in a single SQLite schema. Triggers block UPDATE/DELETE on critical ledger tables.

Controlled exceptions:
- ``prov_core_prov_entity``: UPDATE allowed only to set ``invalidated_at`` (soft invalidation).
- Mutable operational tables (``pipeline_pipeline_run``, ``calculation_calculation_result_set``, …)
  are intentionally excluded — see ``MUTABLE_TABLES``.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection

# Tables where UPDATE/DELETE are blocked entirely (ledger facts).
APPEND_ONLY_TABLES: tuple[str, ...] = (
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
    "pipeline_source_artifact",
    "pipeline_source_artifact_revision",
    "pipeline_wrapper_execution",
    "pipeline_normalized_batch",
    "semantic_semantic_integration_execution",
    "semantic_canonical_snapshot",
    "semantic_canonical_snapshot_item",
    "semantic_ontology_resource_link",
    "calculation_calculation_execution",
    "calculation_calculation_parameter_value",
    "calculation_calculation_result_item",
    "calculation_calculation_review",
    "calculation_result_aggregation_link",
    "audit_hash_record",
    "audit_audit_event",
)

# Tables that may receive controlled UPDATEs (status, supersede, outbox, etc.).
MUTABLE_TABLES: tuple[str, ...] = (
    "pipeline_pipeline_run",
    "pipeline_wrapper_definition",
    "calculation_calculation_method",
    "calculation_calculation_method_version",
    "calculation_calculation_parameter_set",
    "calculation_calculation_result_set",
    "calculation_result_publication_execution",
    "audit_blockchain_anchor",
    "audit_outbox_event",
    "reporting_period",
)

_ENTITY_INVALIDATION_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS trg_prov_entity_invalidate_only
BEFORE UPDATE ON prov_core_prov_entity
BEGIN
    SELECT CASE
        WHEN OLD.invalidated_at IS NOT NULL THEN
            RAISE(ABORT, 'Append-only violation: prov_entity already invalidated')
        WHEN NEW.invalidated_at IS NULL THEN
            RAISE(ABORT, 'Append-only violation: cannot clear invalidated_at on prov_entity')
        WHEN NEW.entity_id != OLD.entity_id
            OR NEW.bundle_id != OLD.bundle_id
            OR NEW.pipeline_run_id != OLD.pipeline_run_id
            OR NEW.entity_type != OLD.entity_type
            OR IFNULL(NEW.entity_kind, '') != IFNULL(OLD.entity_kind, '')
            OR IFNULL(NEW.entity_ref_id, '00000000-0000-0000-0000-000000000000')
                != IFNULL(OLD.entity_ref_id, '00000000-0000-0000-0000-000000000000')
            OR IFNULL(NEW.business_key, '') != IFNULL(OLD.business_key, '')
            OR IFNULL(NEW.name, '') != IFNULL(OLD.name, '')
            OR IFNULL(NEW.description, '') != IFNULL(OLD.description, '')
            OR IFNULL(NEW.version_label, '') != IFNULL(OLD.version_label, '')
            OR IFNULL(NEW.content_hash, '') != IFNULL(OLD.content_hash, '')
            OR NEW.created_at != OLD.created_at
            OR IFNULL(NEW.metadata, '{}') != IFNULL(OLD.metadata, '{}')
        THEN
            RAISE(ABORT, 'Append-only violation: only invalidated_at may change on prov_entity')
    END;
END;
"""


def _trigger_block_update(table: str) -> str:
    return f"""
CREATE TRIGGER IF NOT EXISTS trg_append_only_{table}_no_update
BEFORE UPDATE ON {table}
BEGIN
    SELECT RAISE(ABORT, 'Append-only violation: UPDATE not permitted on {table}');
END;
"""


def _trigger_block_delete(table: str) -> str:
    return f"""
CREATE TRIGGER IF NOT EXISTS trg_append_only_{table}_no_delete
BEFORE DELETE ON {table}
BEGIN
    SELECT RAISE(ABORT, 'Append-only violation: DELETE not permitted on {table}');
END;
"""


def install_sqlite_append_only(connection: Connection | Engine) -> None:
    """Install append-only triggers on an SQLite database (idempotent)."""

    conn = connection.connect() if isinstance(connection, Engine) else connection
    own_connection = isinstance(connection, Engine)
    try:
        if conn.dialect.name != "sqlite":
            return
        for table in APPEND_ONLY_TABLES:
            if table == "prov_core_prov_entity":
                continue
            conn.execute(text(_trigger_block_update(table)))
            conn.execute(text(_trigger_block_delete(table)))
        conn.execute(text(_ENTITY_INVALIDATION_TRIGGER))
        conn.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS trg_prov_entity_no_delete
                BEFORE DELETE ON prov_core_prov_entity
                BEGIN
                    SELECT RAISE(ABORT, 'Append-only violation: DELETE not permitted on prov_core_prov_entity');
                END;
                """
            )
        )
        conn.commit()
    finally:
        if own_connection:
            conn.close()


def drop_sqlite_append_only(connection: Connection | Engine) -> None:
    """Drop append-only triggers (tests / schema reset)."""

    conn = connection.connect() if isinstance(connection, Engine) else connection
    own_connection = isinstance(connection, Engine)
    try:
        if conn.dialect.name != "sqlite":
            return
        for table in APPEND_ONLY_TABLES:
            conn.execute(text(f"DROP TRIGGER IF EXISTS trg_append_only_{table}_no_update"))
            conn.execute(text(f"DROP TRIGGER IF EXISTS trg_append_only_{table}_no_delete"))
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prov_entity_invalidate_only"))
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prov_entity_no_delete"))
        conn.commit()
    finally:
        if own_connection:
            conn.close()
