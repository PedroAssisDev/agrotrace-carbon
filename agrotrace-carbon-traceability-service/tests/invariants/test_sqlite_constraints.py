from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from provenance_service.application.services.provenance_recorder import (
    RecordCanonicalSnapshotCommand,
    RecordNormalizedBatchCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordSourceArtifactRevisionCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    StartPipelineRunCommand,
)
from provenance_service.domain.semantic.entities import CanonicalSnapshotItem
from provenance_service.domain.shared.hashing import compute_hash_hex
from provenance_service.domain.shared.ids import new_uuid7


def _seed_basic_semantic_flow(uow_factory, recorder):
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code="sqlite-constraints-flow",
                farm_reference="farm-1",
                reporting_period_reference="2026-Q1",
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
            ),
        )
        wrapper = recorder.record_wrapper_definition(
            uow,
            RecordWrapperDefinitionCommand(
                wrapper_name="erp-xml",
                wrapper_version="1.0.0",
                source_layout_name="erp",
            ),
        )
        execution = recorder.record_wrapper_execution(
            uow,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=wrapper.wrapper_definition_id,
                input_artifact_id=artifact.source_artifact_id,
                started_at=datetime.now(timezone.utc),
            ),
        )
        batch = recorder.record_normalized_batch(
            uow,
            RecordNormalizedBatchCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_execution_id=execution.wrapper_execution_id,
                batch_code="batch-1",
                schema_version="1.0",
                record_count=1,
            ),
        )
        integration = recorder.record_semantic_integration(
            uow,
            RecordSemanticIntegrationCommand(
                pipeline_run_id=run.pipeline_run_id,
                normalized_batch_id=batch.normalized_batch_id,
                ontology_name="agrotrace",
                ontology_version="2026.04",
                mapping_rule_version="1",
                started_at=datetime.now(timezone.utc),
            ),
        )
        uow.commit()
        return run, artifact, integration


def test_unique_item_key_per_snapshot_is_enforced_in_sqlite(uow_factory, recorder) -> None:
    run, _, integration = _seed_basic_semantic_flow(uow_factory, recorder)

    with uow_factory() as uow:
        snapshot = recorder.record_canonical_snapshot(
            uow,
            RecordCanonicalSnapshotCommand(
                pipeline_run_id=run.pipeline_run_id,
                semantic_integration_execution_id=integration.semantic_integration_execution_id,
                graph_name="agrotrace:graph",
                snapshot_label="snapshot-1",
                items=[
                    {"item_key": "item-1", "value": 10},
                ],
            ),
        )
        uow.commit()

    with uow_factory() as uow:
        uow.canonical_snapshots.add_item(
            CanonicalSnapshotItem(
                canonical_snapshot_item_id=new_uuid7(),
                canonical_snapshot_id=snapshot.canonical_snapshot_id,
                item_key="item-1",
                payload={"value": 20},
                item_hash=compute_hash_hex({"value": 20}),
            )
        )
        with pytest.raises(IntegrityError):
            uow.commit()


def test_single_current_revision_per_artifact_is_enforced_in_sqlite(
    uow_factory, recorder
) -> None:
    _, artifact, _ = _seed_basic_semantic_flow(uow_factory, recorder)

    with uow_factory() as uow:
        recorder.record_source_artifact_revision(
            uow,
            RecordSourceArtifactRevisionCommand(
                source_artifact_id=artifact.source_artifact_id,
                revision_number=1,
                storage_uri="s3://data-r1.xml",
                content_hash="b" * 64,
                is_current=True,
                received_at=datetime.now(timezone.utc),
            ),
        )
        uow.commit()

    with uow_factory() as uow:
        with pytest.raises(IntegrityError):
            recorder.record_source_artifact_revision(
                uow,
                RecordSourceArtifactRevisionCommand(
                    source_artifact_id=artifact.source_artifact_id,
                    revision_number=2,
                    storage_uri="s3://data-r2.xml",
                    content_hash="c" * 64,
                    is_current=True,
                    received_at=datetime.now(timezone.utc),
                ),
            )
