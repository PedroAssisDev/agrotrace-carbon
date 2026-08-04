"""Idempotency-key based dedup must return the same record."""

from __future__ import annotations

from datetime import datetime, timezone

from provenance_service.application.services.provenance_recorder import (
    RecordSourceArtifactCommand,
    RecordWrapperDefinitionCommand,
    StartPipelineRunCommand,
)


def _start_run(uow_factory, recorder, run_code: str = "idem-1"):
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code=run_code,
                farm_reference="farm",
                reporting_period_reference="2026-Q1",
            ),
        )
        uow.commit()
        return run


def test_pipeline_run_idempotency_key(uow_factory, recorder) -> None:
    cmd = StartPipelineRunCommand(
        run_code="idem-pl-1",
        farm_reference="farm",
        reporting_period_reference="2026-Q1",
        idempotency_key="kpl-1",
    )
    with uow_factory() as uow:
        a = recorder.start_pipeline_run(uow, cmd)
        uow.commit()
    with uow_factory() as uow2:
        b = recorder.start_pipeline_run(uow2, cmd)
        uow2.commit()
    assert a.pipeline_run_id == b.pipeline_run_id


def test_source_artifact_idempotency_key(uow_factory, recorder) -> None:
    run = _start_run(uow_factory, recorder, "idem-2")
    cmd = RecordSourceArtifactCommand(
        pipeline_run_id=run.pipeline_run_id,
        source_system="ERP",
        original_filename="data.xml",
        storage_uri="s3://data.xml",
        content_hash="a" * 64,
        idempotency_key="ksa-1",
        received_at=datetime.now(timezone.utc),
    )
    with uow_factory() as uow:
        a = recorder.record_source_artifact(uow, cmd)
        uow.commit()
    with uow_factory() as uow2:
        b = recorder.record_source_artifact(uow2, cmd)
        uow2.commit()
    assert a.source_artifact_id == b.source_artifact_id


def test_wrapper_definition_dedup_by_name_version(uow_factory, recorder) -> None:
    cmd = RecordWrapperDefinitionCommand(
        wrapper_name="erp-xml",
        wrapper_version="1.2.3",
        source_layout_name="erp",
    )
    with uow_factory() as uow:
        a = recorder.record_wrapper_definition(uow, cmd)
        uow.commit()
    with uow_factory() as uow2:
        b = recorder.record_wrapper_definition(uow2, cmd)
        uow2.commit()
    assert a.wrapper_definition_id == b.wrapper_definition_id
