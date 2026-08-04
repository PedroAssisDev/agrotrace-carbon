"""SQLite append-only triggers for blockchain ledger tables.

Only hash_record, verification_log and audit_log are append-only.
Operational tables (anchor_request, evidence_package, blockchain_transaction,
observer_state, anchoring_attempt, evidence_item, blockchain_network) remain mutable.
"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection

APPEND_ONLY_TABLES: tuple[str, ...] = (
    "hash_record",
    "verification_log",
    "audit_log",
)

MUTABLE_TABLES: tuple[str, ...] = (
    "anchor_request",
    "evidence_package",
    "evidence_item",
    "blockchain_transaction",
    "blockchain_network",
    "observer_state",
    "anchoring_attempt",
)


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
    """Install append-only triggers (idempotent)."""

    conn = connection.connect() if isinstance(connection, Engine) else connection
    own_connection = isinstance(connection, Engine)
    try:
        if conn.dialect.name != "sqlite":
            return
        for table in APPEND_ONLY_TABLES:
            conn.execute(text(_trigger_block_update(table)))
            conn.execute(text(_trigger_block_delete(table)))
        if own_connection:
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
        if own_connection:
            conn.commit()
    finally:
        if own_connection:
            conn.close()
