"""VerifyIntegrity v2 recomputation and mirror modes."""

from __future__ import annotations

from datetime import datetime, timezone

from provenance_service.application.services.provenance_recorder import (
    RecordCanonicalSnapshotCommand,
    RecordNormalizedBatchCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    StartPipelineRunCommand,
)
from provenance_service.application.use_cases.verify_integrity import VerifyIntegrity
from provenance_service.domain.shared.enums import HashAlgorithm, HashSubjectKind


def _seed_snapshot_bundle(uow_factory, recorder):
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code="verify-run-1",
                farm_reference="farm",
                reporting_period_reference="2026-Q1",
                idempotency_key="verify-run-key",
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
                idempotency_key="verify-art-key",
            ),
        )
        wrapper_def = recorder.record_wrapper_definition(
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
                wrapper_definition_id=wrapper_def.wrapper_definition_id,
                input_artifact_id=artifact.source_artifact_id,
                started_at=datetime.now(timezone.utc),
                idempotency_key="verify-wexec-key",
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
                content_hash="b" * 64,
                idempotency_key="verify-batch-key",
            ),
        )
        integration = recorder.record_semantic_integration(
            uow,
            RecordSemanticIntegrationCommand(
                pipeline_run_id=run.pipeline_run_id,
                normalized_batch_id=batch.normalized_batch_id,
                ontology_name="agrotrace",
                ontology_version="1.0",
                mapping_rule_version="1.0",
                started_at=datetime.now(timezone.utc),
                idempotency_key="verify-sem-key",
            ),
        )
        snapshot = recorder.record_canonical_snapshot(
            uow,
            RecordCanonicalSnapshotCommand(
                pipeline_run_id=run.pipeline_run_id,
                semantic_integration_execution_id=integration.semantic_integration_execution_id,
                graph_name="g1",
                snapshot_label="snap-1",
                items=[{"item_key": "row-1", "payload": {"co2e": 1.0}}],
            ),
        )
        hash_row = uow.hash_records.find_by_subject(
            HashSubjectKind.CANONICAL_SNAPSHOT.value,
            snapshot.canonical_snapshot_id,
            HashAlgorithm.SHA256.value,
        )
        assert hash_row is not None and hash_row.bundle_id is not None
        uow.commit()
        return hash_row.bundle_id, snapshot.canonical_snapshot_id


def test_verify_integrity_recomputes_canonical_snapshot(uow_factory, recorder) -> None:
    bundle_id, _ = _seed_snapshot_bundle(uow_factory, recorder)
    report = VerifyIntegrity(uow_factory).execute(bundle_id)
    assert report.is_valid
    snapshot_checks = [
        c for c in report.checks if c.subject_kind == "canonical_snapshot"
    ]
    assert snapshot_checks
    assert all(c.verification_mode == "recomputed" for c in snapshot_checks)
    assert all(c.matches for c in snapshot_checks)
