"""Append-only enforcement via SQLite triggers (and application guards)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import DatabaseError

from provenance_service.application.services.provenance_recorder import (
    RecordSourceArtifactCommand,
    StartPipelineRunCommand,
)
from provenance_service.infrastructure.db.models.audit import HashRecordModel
from provenance_service.infrastructure.db.models.pipeline import (
    PipelineRunModel,
    SourceArtifactModel,
)
from provenance_service.infrastructure.db.models.prov_core import ProvEntityModel


def _seed_run_with_artifact(uow_factory, recorder):
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code="ap-1",
                farm_reference="farm",
                reporting_period_reference="2026-Q1",
                idempotency_key="ap-run-1",
            ),
        )
        artifact = recorder.record_source_artifact(
            uow,
            RecordSourceArtifactCommand(
                pipeline_run_id=run.pipeline_run_id,
                source_system="ERP",
                original_filename="data.xml",
                storage_uri="s3://data.xml",
                content_hash="a" * 64,
                received_at=datetime.now(timezone.utc),
                idempotency_key="ap-art-1",
            ),
        )
        uow.commit()
        return run, artifact


def test_update_on_source_artifact_is_blocked(engine, uow_factory, recorder) -> None:
    _, artifact = _seed_run_with_artifact(uow_factory, recorder)
    tbl = SourceArtifactModel.__tablename__
    with engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text(
                f"UPDATE {tbl} "
                "SET storage_uri = 's3://hijacked' "
                "WHERE source_artifact_id = :id"
            ),
            {"id": artifact.source_artifact_id},
        )
        conn.commit()


def test_delete_on_prov_entity_is_blocked(engine, uow_factory, recorder) -> None:
    _, artifact = _seed_run_with_artifact(uow_factory, recorder)
    tbl = ProvEntityModel.__tablename__
    with engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(text(f"DELETE FROM {tbl} WHERE entity_id = :id"), {"id": artifact.prov_entity_id})
        conn.commit()


def test_update_on_hash_record_is_blocked(engine, uow_factory, recorder) -> None:
    _, artifact = _seed_run_with_artifact(uow_factory, recorder)
    htbl = HashRecordModel.__tablename__
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT hash_record_id FROM {htbl} "
                "WHERE subject_id = :id LIMIT 1"
            ),
            {"id": artifact.source_artifact_id.hex},
        ).fetchone()
        assert row is not None
    with engine.connect() as conn, pytest.raises(DatabaseError):
        conn.execute(
            text(
                f"UPDATE {htbl} SET hash_value = 'tampered' "
                "WHERE hash_record_id = :id"
            ),
            {"id": row[0]},
        )
        conn.commit()


def test_pipeline_run_update_is_allowed(engine, uow_factory, recorder) -> None:
    """``pipeline_run`` is intentionally not append-only; status updates are
    expected to flow naturally as the run progresses."""

    run, _ = _seed_run_with_artifact(uow_factory, recorder)
    with engine.begin() as conn:
        conn.execute(
            update(PipelineRunModel)
            .where(PipelineRunModel.pipeline_run_id == run.pipeline_run_id)
            .values(notes="rollup notes")
        )
