"""Cross-context FKs must reject orphans (broken pipelines)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from provenance_service.application.services.provenance_recorder import (
    RecordNormalizedBatchCommand,
    RecordSemanticIntegrationCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    StartPipelineRunCommand,
)
from provenance_service.domain.shared.errors import InvariantViolationError


def _start_run(uow_factory, recorder, run_code: str = "ri-1"):
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


def test_wrapper_execution_without_source_artifact_fails(uow_factory, recorder) -> None:
    run = _start_run(uow_factory, recorder, "ri-w-1")
    with uow_factory() as uow:
        definition = recorder.record_wrapper_definition(
            uow,
            RecordWrapperDefinitionCommand(
                wrapper_name="erp",
                wrapper_version="1",
                source_layout_name="erp",
            ),
        )
        uow.commit()
    with uow_factory() as uow2, pytest.raises(InvariantViolationError):
        recorder.record_wrapper_execution(
            uow2,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=definition.wrapper_definition_id,
                input_artifact_id=uuid4(),
                started_at=datetime.now(timezone.utc),
            ),
        )


def test_normalized_batch_without_wrapper_execution_fails(
    uow_factory, recorder
) -> None:
    run = _start_run(uow_factory, recorder, "ri-w-2")
    with uow_factory() as uow, pytest.raises(InvariantViolationError):
        recorder.record_normalized_batch(
            uow,
            RecordNormalizedBatchCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_execution_id=uuid4(),
                batch_code="orphan",
                schema_version="1",
                record_count=0,
            ),
        )


def test_semantic_integration_without_normalized_batch_fails(
    uow_factory, recorder
) -> None:
    run = _start_run(uow_factory, recorder, "ri-w-3")
    with uow_factory() as uow, pytest.raises(InvariantViolationError):
        recorder.record_semantic_integration(
            uow,
            RecordSemanticIntegrationCommand(
                pipeline_run_id=run.pipeline_run_id,
                normalized_batch_id=uuid4(),
                ontology_name="agrotrace",
                ontology_version="2026.04",
                mapping_rule_version="1",
                started_at=datetime.now(timezone.utc),
            ),
        )
