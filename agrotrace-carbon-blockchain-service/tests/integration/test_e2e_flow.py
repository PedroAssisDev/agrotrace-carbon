from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.dto.commands import (
    BuildEvidencePackageCommand,
    ObserveEventsCommand,
    SimulateAnchoringCommand,
    VerifyEvidencePackageCommand,
)
from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
from app.application.use_cases.observe_provenance_events import ObserveProvenanceEventsUseCase
from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
from app.infrastructure.provenance.sqlite_provenance_event_reader import (
    SQLiteProvenanceDataReader,
    SQLiteProvenanceEventReader,
)
from app.shared.config import Settings


def _create_provenance_schema(db_path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE audit_outbox_event (
            outbox_event_id TEXT PRIMARY KEY,
            aggregate_kind TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            pipeline_run_id TEXT,
            calculation_execution_id TEXT,
            calculation_result_set_id TEXT,
            reporting_period_id TEXT,
            source_table TEXT,
            source_record_id TEXT
        );
        CREATE TABLE reporting_period (
            reporting_period_id TEXT PRIMARY KEY,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            period_granularity TEXT NOT NULL,
            period_label TEXT NOT NULL
        );
        CREATE TABLE pipeline_pipeline_run (
            pipeline_run_id TEXT PRIMARY KEY,
            farm_id_hash TEXT,
            project_id_hash TEXT,
            reporting_period_id TEXT
        );
        CREATE TABLE calculation_calculation_execution (
            calculation_execution_id TEXT PRIMARY KEY,
            calculation_method_version_id TEXT,
            calculation_parameter_set_id TEXT
        );
        CREATE TABLE calculation_calculation_method_version (
            calculation_method_version_id TEXT PRIMARY KEY
        );
        CREATE TABLE calculation_calculation_parameter_set (
            calculation_parameter_set_id TEXT PRIMARY KEY
        );
        CREATE TABLE calculation_calculation_result_set (
            calculation_result_set_id TEXT PRIMARY KEY,
            pipeline_run_id TEXT NOT NULL,
            calculation_execution_id TEXT NOT NULL,
            summary_hash TEXT,
            result_scope TEXT,
            consolidation_type TEXT,
            reporting_period_id TEXT,
            approved_at TEXT,
            published_at TEXT
        );
        CREATE TABLE audit_hash_record (
            hash_record_id TEXT PRIMARY KEY,
            subject_kind TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            hash_value TEXT NOT NULL,
            hash_scope TEXT,
            canonicalization_method TEXT,
            computed_at TEXT NOT NULL
        );
        """
    )
    conn.close()


def _seed_provenance(db_path) -> str:
    event_id = str(uuid4())
    pipeline_run_id = str(uuid4())
    reporting_period_id = str(uuid4())
    result_set_id = str(uuid4())
    execution_id = str(uuid4())
    method_version_id = str(uuid4())
    parameter_set_id = str(uuid4())

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO reporting_period VALUES (?, ?, ?, ?, ?)
        """,
        (
            reporting_period_id,
            "2026-01-01T00:00:00+00:00",
            "2026-12-31T23:59:59+00:00",
            "annual",
            "2026",
        ),
    )
    conn.execute(
        """
        INSERT INTO pipeline_pipeline_run VALUES (?, ?, ?, ?)
        """,
        (
            pipeline_run_id,
            "0xfarm",
            "0xproject",
            reporting_period_id,
        ),
    )
    conn.execute(
        "INSERT INTO calculation_calculation_method_version VALUES (?)",
        (method_version_id,),
    )
    conn.execute(
        "INSERT INTO calculation_calculation_parameter_set VALUES (?)",
        (parameter_set_id,),
    )
    conn.execute(
        """
        INSERT INTO calculation_calculation_execution VALUES (?, ?, ?)
        """,
        (execution_id, method_version_id, parameter_set_id),
    )
    conn.execute(
        """
        INSERT INTO calculation_calculation_result_set VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_set_id,
            pipeline_run_id,
            execution_id,
            "0xsummary",
            "annual",
            "direct",
            reporting_period_id,
            datetime.now(UTC).isoformat(),
            None,
        ),
    )
    conn.execute(
        """
        INSERT INTO audit_hash_record VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            "calculation_method_version",
            method_version_id,
            "0xmethodhash",
            "record",
            "json_canonical_v1",
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.execute(
        """
        INSERT INTO audit_hash_record VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            "calculation_parameter_set",
            parameter_set_id,
            "0xparamhash",
            "record",
            "json_canonical_v1",
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.execute(
        """
        INSERT INTO audit_outbox_event (
            outbox_event_id, aggregate_kind, aggregate_id, event_type, payload,
            created_at, status, pipeline_run_id, calculation_execution_id,
            calculation_result_set_id, reporting_period_id, source_table, source_record_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            "calculation_result_set",
            result_set_id,
            "CALCULATION_APPROVED",
            "{}",
            datetime.now(UTC).isoformat(),
            "pending",
            pipeline_run_id,
            execution_id,
            result_set_id,
            reporting_period_id,
            "calculation_calculation_result_set",
            result_set_id,
        ),
    )
    conn.commit()
    conn.close()
    return event_id


@pytest.fixture
def seeded_settings(tmp_path) -> Settings:
    provenance_db = tmp_path / "provenance.db"
    _create_provenance_schema(provenance_db)
    _seed_provenance(provenance_db)
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'blockchain.db'}",
        provenance_database_url=str(provenance_db),
    )


def test_observe_events_creates_anchor_request(seeded_settings, uow_factory) -> None:
    uow = uow_factory(seeded_settings)
    reader = SQLiteProvenanceEventReader(seeded_settings)
    result = ObserveProvenanceEventsUseCase(uow, reader).execute(ObserveEventsCommand(limit=10))
    uow.commit()
    assert len(result.created_request_ids) == 1
    uow.close()


def test_end_to_end_build_simulate_verify(seeded_settings, uow_factory) -> None:
    uow = uow_factory(seeded_settings)
    reader = SQLiteProvenanceEventReader(seeded_settings)
    data_reader = SQLiteProvenanceDataReader(seeded_settings)
    observe = ObserveProvenanceEventsUseCase(uow, reader).execute(ObserveEventsCommand(limit=10))
    request_id = observe.created_request_ids[0]
    build = BuildEvidencePackageUseCase(uow, data_reader, reader).execute(
        BuildEvidencePackageCommand(anchor_request_id=request_id)
    )
    from app.infrastructure.anchoring.providers_registry import ProvidersRegistry

    simulate = SimulateAnchoringUseCase(uow, ProvidersRegistry()).execute(
        SimulateAnchoringCommand(evidence_package_id=build.evidence_package_id)
    )
    verify = VerifyEvidencePackageUseCase(uow).execute(
        VerifyEvidencePackageCommand(evidence_package_id=build.evidence_package_id)
    )
    uow.commit()
    assert simulate.transaction_hash.startswith("0x")
    assert verify.is_valid is True
    uow.close()
