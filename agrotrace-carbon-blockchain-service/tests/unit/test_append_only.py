"""Append-only SQLite triggers for blockchain ledger tables (temp DB only)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import sessionmaker

from app.application.container import init_database
from app.domain.entities import HashRecord
from app.infrastructure.db.connection import create_engine_from_settings
from app.infrastructure.db.sqlite_append_only import (
    APPEND_ONLY_TABLES,
    install_sqlite_append_only,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.config import Settings


@pytest.fixture
def bc_settings(tmp_path) -> Settings:
    blockchain_db = tmp_path / "blockchain_append.db"
    provenance_db = tmp_path / "provenance_empty.db"
    provenance_db.write_text("", encoding="utf-8")
    return Settings(
        database_url=f"sqlite:///{blockchain_db}",
        provenance_database_url=str(provenance_db),
        environment="local",
    )


@pytest.fixture
def bc_engine(bc_settings: Settings):
    init_database(bc_settings)
    engine = create_engine_from_settings(bc_settings)
    yield engine
    engine.dispose()


def test_install_idempotent_on_temp_db(bc_engine) -> None:
    with bc_engine.begin() as conn:
        install_sqlite_append_only(conn)
        install_sqlite_append_only(conn)
    with bc_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'trg_append_only_%'"
            )
        ).fetchall()
    assert len(rows) >= len(APPEND_ONLY_TABLES) * 2  # update + delete each


def test_hash_record_insert_allowed_update_delete_blocked(bc_settings, bc_engine) -> None:
    session_factory = sessionmaker(bind=bc_engine, expire_on_commit=False)
    hid = uuid4()
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        uow.hash_records.add(
            HashRecord(
                hash_record_id=hid,
                subject_kind="evidence_package",
                subject_id=uuid4(),
                hash_algorithm="sha256",
                canonicalization_method="json_canonical_v1",
                hash_value="a" * 64,
                payload_ref=None,
                created_at=datetime.now(UTC),
            )
        )
        uow.commit()

    with bc_engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text("UPDATE hash_record SET hash_value = 'tampered' WHERE hash_record_id = :id"),
            {"id": str(hid)},
        )
        conn.commit()

    with bc_engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text("DELETE FROM hash_record WHERE hash_record_id = :id"),
            {"id": str(hid)},
        )
        conn.commit()


def test_verification_log_and_audit_log_update_blocked(bc_engine) -> None:
    now = datetime.now(UTC)
    now_s = now.isoformat()
    req_id = str(uuid4())
    pkg_id = str(uuid4())
    with bc_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO anchor_request (
                    anchor_request_id, source_event_id, source_event_type,
                    request_scope, status, created_at, updated_at
                ) VALUES (:id, :ev, 'final.published', 'package', 'PENDING', :now, :now)
                """
            ),
            {"id": req_id, "ev": f"ev-{uuid4()}", "now": now_s},
        )
        conn.execute(
            text(
                """
                INSERT INTO evidence_package (
                    evidence_package_id, anchor_request_id, package_type, package_version,
                    period_start, period_end, period_granularity,
                    public_summary_enabled, status, created_at, updated_at
                ) VALUES (
                    :id, :req, 'final_result', '1.0.0',
                    '2026-01-01', '2026-03-31', 'quarter',
                    0, 'DRAFT', :now, :now
                )
                """
            ),
            {"id": pkg_id, "req": req_id, "now": now_s},
        )
        vid = str(uuid4())
        conn.execute(
            text(
                """
                INSERT INTO verification_log (
                    verification_log_id, evidence_package_id, verification_type,
                    is_valid, verified_at
                ) VALUES (:id, :pkg, 'full', 1, :now)
                """
            ),
            {"id": vid, "pkg": pkg_id, "now": now_s},
        )
        aid = str(uuid4())
        conn.execute(
            text(
                """
                INSERT INTO audit_log (
                    audit_log_id, event_name, entity_type, entity_id,
                    severity, message, created_at
                ) VALUES (:id, 'test', 'pkg', :pkg, 'info', 'ok', :now)
                """
            ),
            {"id": aid, "pkg": pkg_id, "now": now_s},
        )

    with bc_engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text("UPDATE verification_log SET is_valid = 0 WHERE verification_log_id = :id"),
            {"id": vid},
        )
        conn.commit()

    with bc_engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text("UPDATE audit_log SET message = 'tampered' WHERE audit_log_id = :id"),
            {"id": aid},
        )
        conn.commit()


def test_mutable_observer_state_still_updateable(bc_engine) -> None:
    """observer_state remains operational (not append-only)."""
    now = datetime.now(UTC).isoformat()
    with bc_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT OR REPLACE INTO observer_state (state_key, state_value, updated_at) "
                "VALUES ('cursor', '0', :now)"
            ),
            {"now": now},
        )
        conn.execute(
            text(
                "UPDATE observer_state SET state_value = '1', updated_at = :now "
                "WHERE state_key = 'cursor'"
            ),
            {"now": now},
        )
    with bc_engine.connect() as conn:
        val = conn.execute(
            text("SELECT state_value FROM observer_state WHERE state_key = 'cursor'")
        ).scalar()
    assert val == "1"
