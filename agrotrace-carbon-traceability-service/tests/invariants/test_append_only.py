"""Append-only enforcement via SQLite triggers (and application guards)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import DatabaseError

from provenance_service.application.services.provenance_recorder import (
    RecordRevisionCommand,
    RecordSourceArtifactCommand,
    StartPipelineRunCommand,
)
from provenance_service.domain.audit.entities import OutboxEvent
from provenance_service.domain.prov_core.entities import ProvEntity
from provenance_service.domain.shared.enums import OutboxStatus, ProvEntityType
from provenance_service.domain.shared.errors import AppendOnlyViolationError
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.infrastructure.db.models.audit import HashRecordModel
from provenance_service.infrastructure.db.models.pipeline import (
    PipelineRunModel,
    SourceArtifactModel,
)
from provenance_service.infrastructure.db.models.prov_core import ProvEntityModel
from provenance_service.infrastructure.db.sqlite_append_only import (
    APPEND_ONLY_TABLES,
    install_sqlite_append_only,
)


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


def test_insert_on_source_artifact_is_allowed(engine, uow_factory, recorder) -> None:
    run, artifact = _seed_run_with_artifact(uow_factory, recorder)
    assert artifact.source_artifact_id is not None
    tbl = SourceArtifactModel.__tablename__
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
    assert count >= 1


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


def test_new_revision_and_derived_entity_are_allowed(uow_factory, recorder) -> None:
    run, artifact = _seed_run_with_artifact(uow_factory, recorder)
    with uow_factory() as uow:
        bundles = uow.prov_bundles.list_by_pipeline_run(run.pipeline_run_id)
        assert bundles
        bundle = bundles[0]
        new_entity = ProvEntity(
            entity_id=uuid4(),
            bundle_id=bundle.bundle_id,
            pipeline_run_id=run.pipeline_run_id,
            entity_type=ProvEntityType.OTHER,
            name="revised-artifact",
            created_at=datetime.now(timezone.utc),
            content_hash="b" * 64,
        )
        uow.prov_entities.add(new_entity)
        uow.flush()
        revision = recorder.record_revision(
            uow,
            RecordRevisionCommand(
                previous_entity_id=artifact.prov_entity_id,
                new_entity_id=new_entity.entity_id,
                revision_reason="correction",
                invalidate_previous=True,
            ),
        )
        uow.commit()
        assert revision.revision_id is not None

    with uow_factory() as uow2:
        previous = uow2.prov_entities.get(artifact.prov_entity_id)
        assert previous is not None
        assert previous.invalidated_at is not None


def test_outbox_mark_published_still_works(uow_factory) -> None:
    event_id = new_uuid7()
    with uow_factory() as uow:
        uow.outbox.add(
            OutboxEvent(
                outbox_event_id=event_id,
                aggregate_kind="pipeline_run",
                aggregate_id=uuid4(),
                event_type="test.event",
                payload={"hello": "world"},
                created_at=datetime.now(timezone.utc),
                status=OutboxStatus.PENDING,
            )
        )
        uow.commit()

    with uow_factory() as uow2:
        uow2.outbox.mark_published(event_id)
        uow2.commit()

    with uow_factory() as uow3:
        pending = uow3.outbox.list_pending(10)
        assert all(e.outbox_event_id != event_id for e in pending)


def test_prov_bundle_close_raises_at_application_layer(uow_factory, recorder) -> None:
    run, _ = _seed_run_with_artifact(uow_factory, recorder)
    with uow_factory() as uow:
        bundles = uow.prov_bundles.list_by_pipeline_run(run.pipeline_run_id)
        assert bundles
        with pytest.raises(AppendOnlyViolationError):
            uow.prov_bundles.close(bundles[0].bundle_id)


def test_install_triggers_idempotent_on_temp_db(engine) -> None:
    """Re-installing triggers on an existing SQLite DB must be safe (no destructive migration)."""
    with engine.begin() as conn:
        install_sqlite_append_only(conn)
        install_sqlite_append_only(conn)
    # spot-check one trigger exists
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND name LIKE 'trg_append_only_%'"
            )
        ).fetchall()
    assert len(rows) >= len(APPEND_ONLY_TABLES)


def test_read_model_aggregation_still_works(uow_factory, recorder) -> None:
    """UI read models are Python aggregations over ledger rows — insert path stays intact."""
    run, artifact = _seed_run_with_artifact(uow_factory, recorder)
    with uow_factory() as uow:
        entities = uow.prov_entities.list_by_bundle(
            uow.prov_bundles.list_by_pipeline_run(run.pipeline_run_id)[0].bundle_id
        )
        assert any(e.entity_id == artifact.prov_entity_id for e in entities)
