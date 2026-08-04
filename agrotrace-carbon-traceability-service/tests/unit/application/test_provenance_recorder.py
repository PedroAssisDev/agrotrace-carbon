"""End-to-end coverage of ``ProvenanceRecorder`` against in-memory fakes."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from provenance_service.application.services.provenance_recorder import (
    ParameterValueInput,
    ProvenanceRecorder,
    RecordBlockchainAnchorCommand,
    RecordCalculationExecutionCommand,
    RecordCalculationMethodCommand,
    RecordCalculationMethodVersionCommand,
    RecordCalculationParameterSetCommand,
    RecordCalculationResultSetCommand,
    RecordCalculationReviewCommand,
    RecordCanonicalSnapshotCommand,
    RecordHashCommand,
    RecordNormalizedBatchCommand,
    RecordResultPublicationCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    ResultItemInput,
    StartPipelineRunCommand,
)
from provenance_service.domain.prov_core.entities import ProvAgent
from provenance_service.domain.shared.enums import (
    BlockchainAnchorStatus,
    CalculationResultType,
    CalculationReviewDecision,
    HashAlgorithm,
    HashSubjectKind,
    OutboxStatus,
    ProvAgentType,
    ResultPublicationStatus,
)
from provenance_service.domain.shared.errors import (
    AlreadyExistsError,
    IdempotencyConflictError,
    InvariantViolationError,
    NotFoundError,
)
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.domain.shared.time import utcnow
from tests.unit.application.fakes import FakeUnitOfWork


@pytest.fixture
def recorder() -> ProvenanceRecorder:
    return ProvenanceRecorder()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _start_run(
    recorder: ProvenanceRecorder, uow: FakeUnitOfWork, run_code: str = "run-001"
):
    return recorder.start_pipeline_run(
        uow,
        StartPipelineRunCommand(
            run_code=run_code,
            farm_reference="farm-1",
            reporting_period_reference="2026-Q1",
        ),
    )


def test_start_pipeline_run_creates_record(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    assert uow.pipeline_runs.get(run.pipeline_run_id) is run
    assert any(
        e.event_type == "pipeline_run.started"
        for e in uow.outbox.items.values()
    )


def test_start_pipeline_run_is_idempotent(recorder, uow) -> None:
    cmd = StartPipelineRunCommand(
        run_code="run-001",
        farm_reference="farm-1",
        reporting_period_reference="2026-Q1",
        idempotency_key="key-001",
    )
    a = recorder.start_pipeline_run(uow, cmd)
    b = recorder.start_pipeline_run(uow, cmd)
    assert a.pipeline_run_id == b.pipeline_run_id


def test_start_pipeline_run_rejects_duplicate_run_code(recorder, uow) -> None:
    _start_run(recorder, uow, "run-001")
    with pytest.raises(AlreadyExistsError):
        _start_run(recorder, uow, "run-001")


def test_record_source_artifact_creates_entity_and_hash(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    artifact = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="ERP",
            original_filename="payload.xml",
            storage_uri="s3://raw/payload.xml",
            content_hash="abc123" * 4,
        ),
    )
    assert uow.prov_entities.get(artifact.prov_entity_id) is not None
    assert any(
        h.subject_id == artifact.source_artifact_id
        for h in uow.hash_records.items.values()
    )


def test_record_source_artifact_is_idempotent(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    cmd = RecordSourceArtifactCommand(
        pipeline_run_id=run.pipeline_run_id,
        source_system="ERP",
        original_filename="payload.xml",
        storage_uri="s3://raw/payload.xml",
        content_hash="abc123" * 4,
        idempotency_key="src-1",
    )
    a = recorder.record_source_artifact(uow, cmd)
    b = recorder.record_source_artifact(uow, cmd)
    assert a.source_artifact_id == b.source_artifact_id


def test_start_pipeline_run_idempotency_detects_payload_conflict(recorder, uow) -> None:
    recorder.start_pipeline_run(
        uow,
        StartPipelineRunCommand(
            run_code="run-001",
            farm_reference="farm-1",
            reporting_period_reference="2026-Q1",
            idempotency_key="run-key-1",
        ),
    )
    with pytest.raises(IdempotencyConflictError):
        recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code="run-001",
                farm_reference="farm-2",
                reporting_period_reference="2026-Q1",
                idempotency_key="run-key-1",
            ),
        )


def test_record_source_artifact_idempotency_detects_payload_conflict(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="ERP",
            original_filename="payload.xml",
            storage_uri="s3://raw/payload.xml",
            content_hash="abc123" * 4,
            idempotency_key="src-key-1",
        ),
    )
    with pytest.raises(IdempotencyConflictError):
        recorder.record_source_artifact(
            uow,
            RecordSourceArtifactCommand(
                pipeline_run_id=run.pipeline_run_id,
                source_system="ERP",
                original_filename="payload.xml",
                storage_uri="s3://raw/changed.xml",
                content_hash="abc123" * 4,
                idempotency_key="src-key-1",
            ),
        )


def test_wrapper_execution_requires_existing_source_artifact(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    definition = recorder.record_wrapper_definition(
        uow,
        RecordWrapperDefinitionCommand(
            wrapper_name="erp-xml",
            wrapper_version="1.0.0",
            source_layout_name="erp",
        ),
    )
    with pytest.raises(InvariantViolationError):
        recorder.record_wrapper_execution(
            uow,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=definition.wrapper_definition_id,
                input_artifact_id=uuid4(),
                started_at=datetime.now(timezone.utc),
            ),
        )


def test_full_happy_path(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    artifact = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="ERP",
            original_filename="payload.xml",
            storage_uri="s3://raw/payload.xml",
            content_hash="a" * 64,
        ),
    )
    definition = recorder.record_wrapper_definition(
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
            wrapper_definition_id=definition.wrapper_definition_id,
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
            record_count=10,
            content_hash="b" * 64,
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
    snapshot = recorder.record_canonical_snapshot(
        uow,
        RecordCanonicalSnapshotCommand(
            pipeline_run_id=run.pipeline_run_id,
            semantic_integration_execution_id=(
                integration.semantic_integration_execution_id
            ),
            graph_name="agrotrace:graph",
            snapshot_label="snap-001",
            payload={"farms": ["farm-1"]},
        ),
    )

    method = recorder.record_calculation_method(
        uow,
        RecordCalculationMethodCommand(
            method_code="ipcc-2019",
            method_name="IPCC 2019 Refinement",
        ),
    )
    version = recorder.record_calculation_method_version(
        uow,
        RecordCalculationMethodVersionCommand(
            calculation_method_id=method.calculation_method_id,
            version_label="1.0",
        ),
    )
    params = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_method_version_id=version.calculation_method_version_id,
            values=[
                ParameterValueInput(
                    parameter_name="ef_methane",
                    parameter_value_numeric=Decimal("28.0"),
                    parameter_unit="kg",
                )
            ],
        ),
    )
    calc_execution = recorder.record_calculation_execution(
        uow,
        RecordCalculationExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            calculation_method_version_id=version.calculation_method_version_id,
            calculation_parameter_set_id=params.calculation_parameter_set_id,
            started_at=datetime.now(timezone.utc),
        ),
    )
    result_set = recorder.record_calculation_result_set(
        uow,
        RecordCalculationResultSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_execution_id=calc_execution.calculation_execution_id,
            items=[
                ResultItemInput(
                    result_type=CalculationResultType.EMISSION_TOTAL,
                    result_name="co2e_total",
                    result_value=Decimal("987.65"),
                    result_unit="kgCO2e",
                )
            ],
        ),
    )

    reviewer_agent_id = new_uuid7()
    uow.prov_agents.add(
        ProvAgent(
            agent_id=reviewer_agent_id,
            agent_type=ProvAgentType.HUMAN,
            name="reviewer-1",
            external_reference="user:reviewer-1",
            created_at=utcnow(),
        )
    )
    review = recorder.record_calculation_review(
        uow,
        RecordCalculationReviewCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            reviewer_agent_id=reviewer_agent_id,
            decision=CalculationReviewDecision.APPROVED,
        ),
    )
    publication = recorder.record_result_publication(
        uow,
        RecordResultPublicationCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            target_graph_name="agrotrace:final",
            ontology_name="agrotrace",
            ontology_version="2026.04",
            calculation_review_id=review.calculation_review_id,
        ),
    )
    hash_record = recorder.record_hash(
        uow,
        RecordHashCommand(
            pipeline_run_id=run.pipeline_run_id,
            subject_kind=HashSubjectKind.BUNDLE,
            subject_id=publication.result_publication_execution_id,
            hash_value="c" * 64,
            hash_algorithm=HashAlgorithm.SHA256,
        ),
    )
    anchor = recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hash_record.hash_record_id,
            blockchain_network="stub",
            anchor_status=BlockchainAnchorStatus.SUBMITTED,
            transaction_hash="0xabc",
        ),
    )
    assert publication.publication_status is ResultPublicationStatus.PUBLISHED
    assert anchor.transaction_hash == "0xabc"

    pending = [
        e for e in uow.outbox.items.values() if e.status is OutboxStatus.PENDING
    ]
    assert len(pending) >= 8


def test_record_result_publication_requires_approved_review(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    artifact = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="ERP",
            original_filename="payload.xml",
            storage_uri="s3://raw/payload.xml",
            content_hash="a" * 64,
        ),
    )
    definition = recorder.record_wrapper_definition(
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
            wrapper_definition_id=definition.wrapper_definition_id,
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
    snapshot = recorder.record_canonical_snapshot(
        uow,
        RecordCanonicalSnapshotCommand(
            pipeline_run_id=run.pipeline_run_id,
            semantic_integration_execution_id=(
                integration.semantic_integration_execution_id
            ),
            graph_name="agrotrace:graph",
            snapshot_label="snap-001",
        ),
    )
    method = recorder.record_calculation_method(
        uow,
        RecordCalculationMethodCommand(
            method_code="ipcc-2019", method_name="IPCC 2019 Refinement"
        ),
    )
    version = recorder.record_calculation_method_version(
        uow,
        RecordCalculationMethodVersionCommand(
            calculation_method_id=method.calculation_method_id, version_label="1.0"
        ),
    )
    params = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_method_version_id=version.calculation_method_version_id,
            values=[
                ParameterValueInput(
                    parameter_name="ef_methane",
                    parameter_value_numeric=Decimal("28.0"),
                    parameter_unit="kg",
                )
            ],
        ),
    )
    calc_exec = recorder.record_calculation_execution(
        uow,
        RecordCalculationExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            calculation_method_version_id=version.calculation_method_version_id,
            calculation_parameter_set_id=params.calculation_parameter_set_id,
            started_at=datetime.now(timezone.utc),
        ),
    )
    result_set = recorder.record_calculation_result_set(
        uow,
        RecordCalculationResultSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_execution_id=calc_exec.calculation_execution_id,
            items=[
                ResultItemInput(
                    result_type=CalculationResultType.EMISSION_TOTAL,
                    result_name="co2e_total",
                    result_value=Decimal("12.0"),
                    result_unit="kgCO2e",
                )
            ],
        ),
    )

    reviewer_agent_id = new_uuid7()
    uow.prov_agents.add(
        ProvAgent(
            agent_id=reviewer_agent_id,
            agent_type=ProvAgentType.HUMAN,
            name="reviewer-1",
            external_reference="user:reviewer-1",
            created_at=utcnow(),
        )
    )
    review = recorder.record_calculation_review(
        uow,
        RecordCalculationReviewCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            reviewer_agent_id=reviewer_agent_id,
            decision=CalculationReviewDecision.REJECTED,
        ),
    )
    with pytest.raises(InvariantViolationError):
        recorder.record_result_publication(
            uow,
            RecordResultPublicationCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                target_graph_name="g",
                ontology_name="agrotrace",
                ontology_version="2026.04",
                calculation_review_id=review.calculation_review_id,
            ),
        )


def test_record_hash_returns_existing_when_same_value(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    cmd = RecordHashCommand(
        pipeline_run_id=run.pipeline_run_id,
        subject_kind=HashSubjectKind.OTHER,
        subject_id=uuid4(),
        hash_value="d" * 64,
    )
    a = recorder.record_hash(uow, cmd)
    b = recorder.record_hash(uow, cmd)
    assert a.hash_record_id == b.hash_record_id


def test_record_blockchain_anchor_requires_existing_hash(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    with pytest.raises(InvariantViolationError):
        recorder.record_blockchain_anchor(
            uow,
            RecordBlockchainAnchorCommand(
                pipeline_run_id=run.pipeline_run_id,
                hash_record_id=uuid4(),
                blockchain_network="stub",
            ),
        )


def test_record_canonical_snapshot_requires_integration(recorder, uow) -> None:
    run = _start_run(recorder, uow)
    with pytest.raises(InvariantViolationError):
        recorder.record_canonical_snapshot(
            uow,
            RecordCanonicalSnapshotCommand(
                pipeline_run_id=run.pipeline_run_id,
                semantic_integration_execution_id=uuid4(),
                graph_name="g",
                snapshot_label="s",
            ),
        )


def test_record_calculation_method_version_rejects_unknown_method(
    recorder, uow
) -> None:
    with pytest.raises(NotFoundError):
        recorder.record_calculation_method_version(
            uow,
            RecordCalculationMethodVersionCommand(
                calculation_method_id=uuid4(),
                version_label="1.0",
            ),
        )


def test_calculation_execution_rejects_cross_run_snapshot_or_param_set(recorder, uow) -> None:
    run_a = _start_run(recorder, uow, "run-a")
    run_b = _start_run(recorder, uow, "run-b")

    artifact_a = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run_a.pipeline_run_id,
            source_system="ERP",
            original_filename="a.xml",
            storage_uri="s3://a.xml",
            content_hash="a" * 64,
        ),
    )
    artifact_b = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run_b.pipeline_run_id,
            source_system="ERP",
            original_filename="b.xml",
            storage_uri="s3://b.xml",
            content_hash="b" * 64,
        ),
    )
    definition = recorder.record_wrapper_definition(
        uow,
        RecordWrapperDefinitionCommand(
            wrapper_name="erp-xml",
            wrapper_version="1.0.0",
            source_layout_name="erp",
        ),
    )

    exec_a = recorder.record_wrapper_execution(
        uow,
        RecordWrapperExecutionCommand(
            pipeline_run_id=run_a.pipeline_run_id,
            wrapper_definition_id=definition.wrapper_definition_id,
            input_artifact_id=artifact_a.source_artifact_id,
            started_at=datetime.now(timezone.utc),
        ),
    )
    exec_b = recorder.record_wrapper_execution(
        uow,
        RecordWrapperExecutionCommand(
            pipeline_run_id=run_b.pipeline_run_id,
            wrapper_definition_id=definition.wrapper_definition_id,
            input_artifact_id=artifact_b.source_artifact_id,
            started_at=datetime.now(timezone.utc),
        ),
    )
    batch_a = recorder.record_normalized_batch(
        uow,
        RecordNormalizedBatchCommand(
            pipeline_run_id=run_a.pipeline_run_id,
            wrapper_execution_id=exec_a.wrapper_execution_id,
            batch_code="batch-a",
            schema_version="1.0",
            record_count=1,
        ),
    )
    batch_b = recorder.record_normalized_batch(
        uow,
        RecordNormalizedBatchCommand(
            pipeline_run_id=run_b.pipeline_run_id,
            wrapper_execution_id=exec_b.wrapper_execution_id,
            batch_code="batch-b",
            schema_version="1.0",
            record_count=1,
        ),
    )

    integration_a = recorder.record_semantic_integration(
        uow,
        RecordSemanticIntegrationCommand(
            pipeline_run_id=run_a.pipeline_run_id,
            normalized_batch_id=batch_a.normalized_batch_id,
            ontology_name="agrotrace",
            ontology_version="2026.04",
            mapping_rule_version="1",
            started_at=datetime.now(timezone.utc),
        ),
    )
    snapshot_a = recorder.record_canonical_snapshot(
        uow,
        RecordCanonicalSnapshotCommand(
            pipeline_run_id=run_a.pipeline_run_id,
            semantic_integration_execution_id=integration_a.semantic_integration_execution_id,
            graph_name="graph-a",
            snapshot_label="snapshot-a",
        ),
    )

    method = recorder.record_calculation_method(
        uow,
        RecordCalculationMethodCommand(
            method_code="ipcc-2019",
            method_name="IPCC 2019 Refinement",
        ),
    )
    version = recorder.record_calculation_method_version(
        uow,
        RecordCalculationMethodVersionCommand(
            calculation_method_id=method.calculation_method_id,
            version_label="1.0",
        ),
    )
    param_set_b = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run_b.pipeline_run_id,
            calculation_method_version_id=version.calculation_method_version_id,
            values=[
                ParameterValueInput(
                    parameter_name="factor",
                    parameter_value_numeric=Decimal("1.0"),
                    parameter_unit="kg",
                )
            ],
        ),
    )

    with pytest.raises(InvariantViolationError):
        recorder.record_calculation_execution(
            uow,
            RecordCalculationExecutionCommand(
                pipeline_run_id=run_a.pipeline_run_id,
                canonical_snapshot_id=snapshot_a.canonical_snapshot_id,
                calculation_method_version_id=version.calculation_method_version_id,
                calculation_parameter_set_id=param_set_b.calculation_parameter_set_id,
                started_at=datetime.now(timezone.utc),
            ),
        )
