"""ProvenanceRecorder — the single, centralized writer of the provenance ledger.

This is the heart of the service. Every fact about lineage, executions,
reviews, publications, hashes and blockchain anchors flows through this
component. APIs and adapters NEVER write to ``prov_*`` tables directly.

Each ``record_*`` method:

1. Opens (or receives) a ``UnitOfWork``.
2. Validates business invariants (e.g. ``wrapper_execution`` requires a
   pre-existing ``source_artifact``).
3. Resolves or creates the surrounding PROV elements (bundle, agent,
   activity, entity).
4. Writes the operational mirror table (``wrapper_execution``,
   ``calculation_execution``, ...).
5. Wires the PROV-DM relations (``used`` / ``generated`` /
   ``derivedFrom`` / ``associatedWith``).
6. Computes and persists a content hash via :func:`compute_hash_hex`.
7. Inserts an outbox event in the SAME transaction.
8. Commits.

Idempotency: when an ``idempotency_key`` is supplied and a previous record
with the same key exists, that record is returned untouched (no duplicate
inserts). Mismatched payloads raise :class:`IdempotencyConflictError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from provenance_service.application.unit_of_work import UnitOfWork
from provenance_service.domain.audit.entities import (
    AuditEvent,
    BlockchainAnchor,
    HashRecord,
    OutboxEvent,
)
from provenance_service.domain.calculation.entities import (
    CalculationExecution,
    CalculationMethod,
    CalculationMethodVersion,
    CalculationParameterSet,
    CalculationParameterValue,
    CalculationResultAggregationLink,
    CalculationResultItem,
    CalculationResultSet,
    CalculationReview,
    ResultPublicationExecution,
)
from provenance_service.domain.pipeline.entities import (
    NormalizedBatch,
    PipelineRun,
    SourceArtifact,
    SourceArtifactRevision,
    WrapperDefinition,
    WrapperExecution,
)
from provenance_service.domain.prov_core.entities import (
    ProvActivity,
    ProvAgent,
    ProvBundle,
    ProvEntity,
)
from provenance_service.domain.prov_core.relations import (
    ProvAssociatedWith,
    ProvDerivedFrom,
    ProvGenerated,
    ProvRevision,
    ProvUsed,
)
from provenance_service.domain.reporting.entities import ReportingPeriod
from provenance_service.domain.semantic.entities import (
    CanonicalSnapshot,
    OntologyResourceLink,
    SemanticIntegrationExecution,
)
from provenance_service.domain.audit.observability import (
    default_canonicalization_method,
    hash_scope_for_subject,
)
from provenance_service.domain.shared.enums import (
    AggregationType,
    BlockchainAnchorStatus,
    CalculationExecutionStatus,
    CalculationMethodStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    ConsolidationType,
    HashAlgorithm,
    HashSubjectKind,
    OutboxStatus,
    ParameterSetStatus,
    PeriodGranularity,
    PipelineRunStatus,
    ProvActivityType,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
    PublicationStage,
    ReportingPeriodStatus,
    ResultPublicationStatus,
    ResultScope,
    RunType,
    SemanticExecutionStatus,
    WrapperExecutionStatus,
)
from provenance_service.domain.shared.errors import (
    AlreadyExistsError,
    IdempotencyConflictError,
    InvariantViolationError,
    NotFoundError,
)
from provenance_service.domain.shared.hashing import compute_hash_hex
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.observability import (
    PROVENANCE_RECORDS,
    get_logger,
    record_recorder_duration,
)


# =====================================================================
# Commands
# =====================================================================


@dataclass(frozen=True, slots=True)
class StartPipelineRunCommand:
    run_code: str
    farm_reference: str
    reporting_period_reference: str
    started_at: datetime | None = None
    parent_pipeline_run_id: UUID | None = None
    triggered_by_agent_id: UUID | None = None
    notes: str | None = None
    tenant_id: UUID | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    pipeline_run_id: UUID | None = None
    run_type: RunType | None = None
    reporting_period_id: UUID | None = None
    farm_id_hash: str | None = None
    project_id_hash: str | None = None


@dataclass(frozen=True, slots=True)
class RecordReportingPeriodCommand:
    period_start: datetime
    period_end: datetime
    period_granularity: PeriodGranularity
    year: int
    period_label: str
    status: ReportingPeriodStatus = ReportingPeriodStatus.OPEN
    month: int | None = None
    day: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    reporting_period_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordSourceArtifactCommand:
    pipeline_run_id: UUID
    source_system: str
    original_filename: str
    storage_uri: str
    content_hash: str
    received_at: datetime | None = None
    source_layout_name: str | None = None
    source_layout_version: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    business_key: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source_artifact_id: UUID | None = None
    prov_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordSourceArtifactRevisionCommand:
    source_artifact_id: UUID
    revision_number: int
    storage_uri: str
    content_hash: str
    received_at: datetime | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    is_current: bool = True
    source_artifact_revision_id: UUID | None = None
    prov_entity_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordWrapperDefinitionCommand:
    wrapper_name: str
    wrapper_version: str
    source_layout_name: str
    source_layout_version: str | None = None
    schema_version: str | None = None
    code_hash: str | None = None
    wrapper_code_hash: str | None = None
    input_schema_hash: str | None = None
    output_schema_hash: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    wrapper_definition_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordWrapperExecutionCommand:
    pipeline_run_id: UUID
    wrapper_definition_id: UUID
    input_artifact_id: UUID
    started_at: datetime
    execution_status: WrapperExecutionStatus = WrapperExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    warning_count: int = 0
    error_count: int = 0
    execution_log_uri: str | None = None
    executor_agent_external_reference: str | None = None
    executor_agent_name: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    input_source_artifact_revision_id: UUID | None = None
    execution_payload_hash: str | None = None
    runtime_version: str | None = None
    wrapper_execution_id: UUID | None = None
    prov_activity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordNormalizedBatchCommand:
    pipeline_run_id: UUID
    wrapper_execution_id: UUID
    batch_code: str
    schema_version: str
    record_count: int
    generated_at: datetime | None = None
    storage_uri: str | None = None
    content_hash: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    normalized_batch_id: UUID | None = None
    prov_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordSemanticIntegrationCommand:
    pipeline_run_id: UUID
    normalized_batch_id: UUID
    ontology_name: str
    ontology_version: str
    mapping_rule_version: str
    started_at: datetime
    execution_status: SemanticExecutionStatus = SemanticExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    triples_generated: int | None = None
    integrator_agent_external_reference: str | None = None
    integrator_agent_name: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    semantic_integration_execution_id: UUID | None = None
    prov_activity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordCanonicalSnapshotCommand:
    pipeline_run_id: UUID
    semantic_integration_execution_id: UUID
    graph_name: str
    snapshot_label: str
    schema_version: str | None = None
    storage_uri: str | None = None
    payload: dict[str, Any] | None = None
    items: list[dict[str, Any]] = field(default_factory=list)
    published_at: datetime | None = None
    snapshot_hash_override: str | None = None
    canonical_schema_version: str | None = None
    snapshot_payload_ref: str | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    canonical_snapshot_id: UUID | None = None
    prov_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordOntologyResourceLinkCommand:
    pipeline_run_id: UUID
    ontology_uri: str
    graph_name: str
    publication_stage: PublicationStage = PublicationStage.FINAL
    prov_entity_id: UUID | None = None
    canonical_snapshot_id: UUID | None = None
    rdf_class: str | None = None
    ontology_version: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ontology_resource_link_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordCalculationMethodCommand:
    method_code: str
    method_name: str
    description: str | None = None
    created_at: datetime | None = None
    calculation_method_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordCalculationMethodVersionCommand:
    calculation_method_id: UUID
    version_label: str
    status: CalculationMethodStatus = CalculationMethodStatus.ACTIVE
    formula_reference: str | None = None
    formula_hash: str | None = None
    method_document_uri: str | None = None
    method_document_hash: str | None = None
    implementation_version: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_method_version_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ParameterValueInput:
    parameter_name: str
    parameter_value_text: str | None = None
    parameter_value_numeric: Decimal | None = None
    parameter_unit: str | None = None
    parameter_source: str | None = None
    is_user_editable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordCalculationParameterSetCommand:
    pipeline_run_id: UUID
    calculation_method_version_id: UUID
    values: list[ParameterValueInput]
    parameter_set_status: ParameterSetStatus = ParameterSetStatus.LOCKED
    created_by_agent_id: UUID | None = None
    notes: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_parameter_set_id: UUID | None = None
    prov_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordCalculationExecutionCommand:
    pipeline_run_id: UUID
    canonical_snapshot_id: UUID
    calculation_method_version_id: UUID
    calculation_parameter_set_id: UUID
    started_at: datetime
    execution_status: CalculationExecutionStatus = CalculationExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    execution_log_uri: str | None = None
    executor_agent_external_reference: str | None = None
    executor_agent_name: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_execution_id: UUID | None = None
    reporting_period_id: UUID | None = None
    prov_activity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResultItemInput:
    result_type: CalculationResultType
    result_name: str
    result_value: Decimal
    result_unit: str
    dimension_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordCalculationResultSetCommand:
    pipeline_run_id: UUID
    calculation_execution_id: UUID
    items: list[ResultItemInput]
    generated_at: datetime | None = None
    result_set_status: CalculationResultSetStatus = CalculationResultSetStatus.PRELIMINARY
    """When set, used as summary / PROV ``content_hash`` instead of a deterministic digest."""
    summary_hash_override: str | None = None
    reporting_period_id: UUID | None = None
    result_scope: ResultScope | None = None
    consolidation_type: ConsolidationType | None = None
    supersedes_id: UUID | None = None
    correction_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_result_set_id: UUID | None = None
    prov_entity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordCalculationReviewCommand:
    pipeline_run_id: UUID
    calculation_result_set_id: UUID
    reviewer_agent_id: UUID
    decision: CalculationReviewDecision
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    evidence_uri: str | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_review_id: UUID | None = None
    prov_activity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordResultPublicationCommand:
    pipeline_run_id: UUID
    calculation_result_set_id: UUID
    target_graph_name: str
    ontology_name: str
    ontology_version: str
    publication_status: ResultPublicationStatus = ResultPublicationStatus.PUBLISHED
    calculation_review_id: UUID | None = None
    published_at: datetime | None = None
    publisher_agent_external_reference: str | None = None
    publisher_agent_name: str | None = None
    create_ontology_resource_link: bool = True
    ontology_uri: str | None = None
    rdf_class: str | None = None
    publication_payload_hash: str | None = None
    ontology_resource_uri: str | None = None
    publication_version: str | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    result_publication_execution_id: UUID | None = None
    prov_activity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordHashCommand:
    pipeline_run_id: UUID
    subject_kind: HashSubjectKind
    subject_id: UUID
    hash_value: str
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    prov_entity_id: UUID | None = None
    bundle_id: UUID | None = None
    computed_at: datetime | None = None
    computed_by_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordBlockchainAnchorCommand:
    pipeline_run_id: UUID
    hash_record_id: UUID
    blockchain_network: str
    anchor_status: BlockchainAnchorStatus = BlockchainAnchorStatus.PENDING
    chain_id: str | None = None
    transaction_hash: str | None = None
    block_number: str | None = None
    merkle_root: str | None = None
    confirmations: int | None = None
    anchored_at: datetime | None = None
    verification_uri: str | None = None
    anchor_provider: str | None = None
    anchor_mode: str | None = None
    evidence_package_external_id: str | None = None
    package_hash: str | None = None
    metadata_hash: str | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    failed_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConfirmBlockchainAnchorCommand:
    """Atualiza um espelho PENDING/SUBMITTED para CONFIRMED (ou FAILED)."""

    blockchain_anchor_id: UUID | None = None
    evidence_package_external_id: str | None = None
    pipeline_run_id: UUID | None = None
    anchor_status: BlockchainAnchorStatus = BlockchainAnchorStatus.CONFIRMED
    chain_id: str | None = None
    transaction_hash: str | None = None
    block_number: str | None = None
    confirmations: int | None = None
    anchored_at: datetime | None = None
    confirmed_at: datetime | None = None
    verification_uri: str | None = None
    failed_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordIntegrityVerificationCommand:
    """Registra verificação de integridade como audit_event (append-only)."""

    pipeline_run_id: UUID
    blockchain_anchor_id: UUID
    verification_id: str
    result: str  # match | divergence
    local_values: dict[str, Any] = field(default_factory=dict)
    recovered_values: dict[str, Any] = field(default_factory=dict)
    verified_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecordResultAggregationLinkCommand:
    parent_result_set_id: UUID
    child_result_set_id: UUID
    aggregation_type: AggregationType
    parent_period_id: UUID | None = None
    child_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    calculation_result_aggregation_link_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RecordRevisionCommand:
    previous_entity_id: UUID
    new_entity_id: UUID
    revised_at: datetime | None = None
    revision_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    invalidate_previous: bool = True


# =====================================================================
# Recorder
# =====================================================================


class ProvenanceRecorder:
    """Centralised, transactional writer of the provenance ledger."""

    SOFTWARE_VERSION = "agrotrace-carbon-provenance-service/0.1.0"

    def __init__(self) -> None:
        self._log = get_logger("recorder")

    # --------------- pipeline_run ---------------

    def start_pipeline_run(self, uow: UnitOfWork, cmd: StartPipelineRunCommand) -> PipelineRun:
        with record_recorder_duration("start_pipeline_run"):
            if cmd.idempotency_key:
                existing = uow.pipeline_runs.get_by_idempotency_key(cmd.idempotency_key)
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="start_pipeline_run",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "run_code": existing.run_code,
                            "farm_reference": existing.farm_reference,
                            "reporting_period_reference": existing.reporting_period_reference,
                        },
                        incoming_values={
                            "run_code": cmd.run_code,
                            "farm_reference": cmd.farm_reference,
                            "reporting_period_reference": cmd.reporting_period_reference,
                        },
                    )
                    return existing
            if uow.pipeline_runs.get_by_run_code(cmd.run_code):
                raise AlreadyExistsError(
                    f"PipelineRun with run_code={cmd.run_code!r} already exists",
                    details={"run_code": cmd.run_code},
                )
            run = PipelineRun(
                pipeline_run_id=cmd.pipeline_run_id or new_uuid7(),
                run_code=cmd.run_code,
                farm_reference=cmd.farm_reference,
                reporting_period_reference=cmd.reporting_period_reference,
                run_status=PipelineRunStatus.RUNNING,
                started_at=cmd.started_at or utcnow(),
                parent_pipeline_run_id=cmd.parent_pipeline_run_id,
                triggered_by_agent_id=cmd.triggered_by_agent_id,
                notes=cmd.notes,
                tenant_id=cmd.tenant_id,
                idempotency_key=cmd.idempotency_key,
                run_type=cmd.run_type,
                reporting_period_id=cmd.reporting_period_id,
                farm_id_hash=cmd.farm_id_hash,
                project_id_hash=cmd.project_id_hash,
                metadata=dict(cmd.metadata),
            )
            uow.pipeline_runs.add(run)
            self._enqueue_event(
                uow,
                aggregate_kind="pipeline_run",
                aggregate_id=run.pipeline_run_id,
                event_type="pipeline_run.started",
                payload={
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "run_code": run.run_code,
                    "farm_reference": run.farm_reference,
                    "reporting_period_reference": run.reporting_period_reference,
                },
            )
            PROVENANCE_RECORDS.labels(kind="pipeline_run", outcome="created").inc()
            self._log.info("pipeline_run.started", pipeline_run_id=str(run.pipeline_run_id))
            return run

    def record_reporting_period(
        self, uow: UnitOfWork, cmd: RecordReportingPeriodCommand
    ) -> ReportingPeriod:
        with record_recorder_duration("record_reporting_period"):
            if cmd.period_granularity is PeriodGranularity.DAILY and cmd.day is None:
                raise InvariantViolationError(
                    "daily reporting_period requires day",
                    details={"period_granularity": cmd.period_granularity.value},
                )
            if cmd.period_granularity is PeriodGranularity.MONTHLY and cmd.month is None:
                raise InvariantViolationError(
                    "monthly reporting_period requires month",
                    details={"period_granularity": cmd.period_granularity.value},
                )
            existing = uow.reporting_periods.get_by_label(cmd.period_label)
            if existing is not None:
                return existing
            now = utcnow()
            period = ReportingPeriod(
                reporting_period_id=cmd.reporting_period_id or new_uuid7(),
                period_start=cmd.period_start,
                period_end=cmd.period_end,
                period_granularity=cmd.period_granularity,
                year=cmd.year,
                month=cmd.month,
                day=cmd.day,
                period_label=cmd.period_label,
                status=cmd.status,
                created_at=now,
                updated_at=now,
                metadata=dict(cmd.metadata),
            )
            uow.reporting_periods.add(period)
            PROVENANCE_RECORDS.labels(kind="reporting_period", outcome="created").inc()
            return period

    # --------------- source_artifact ---------------

    def record_source_artifact(
        self, uow: UnitOfWork, cmd: RecordSourceArtifactCommand
    ) -> SourceArtifact:
        with record_recorder_duration("record_source_artifact"):
            if cmd.idempotency_key:
                existing = uow.source_artifacts.get_by_idempotency_key(cmd.idempotency_key)
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="record_source_artifact",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "pipeline_run_id": existing.pipeline_run_id,
                            "source_system": existing.source_system,
                            "original_filename": existing.original_filename,
                            "storage_uri": existing.storage_uri,
                            "content_hash": existing.content_hash,
                        },
                        incoming_values={
                            "pipeline_run_id": cmd.pipeline_run_id,
                            "source_system": cmd.source_system,
                            "original_filename": cmd.original_filename,
                            "storage_uri": cmd.storage_uri,
                            "content_hash": cmd.content_hash,
                        },
                    )
                    return existing

            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            bundle = self._ensure_bundle(uow, run.pipeline_run_id, ProvBundleType.PIPELINE_RUN)

            entity_id = cmd.prov_entity_id or new_uuid7()
            artifact_id = cmd.source_artifact_id or new_uuid7()
            received_at = cmd.received_at or utcnow()

            entity = ProvEntity(
                entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                pipeline_run_id=run.pipeline_run_id,
                entity_type=ProvEntityType.SOURCE_ARTIFACT,
                entity_kind="source_artifact",
                entity_ref_id=artifact_id,
                business_key=cmd.business_key or cmd.original_filename,
                name=cmd.original_filename,
                content_hash=cmd.content_hash,
                created_at=received_at,
            )
            uow.prov_entities.add(entity)
            uow.flush()

            artifact = SourceArtifact(
                source_artifact_id=artifact_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                source_system=cmd.source_system,
                source_layout_name=cmd.source_layout_name,
                source_layout_version=cmd.source_layout_version,
                original_filename=cmd.original_filename,
                storage_uri=cmd.storage_uri,
                mime_type=cmd.mime_type,
                file_size_bytes=cmd.file_size_bytes,
                content_hash=cmd.content_hash,
                received_at=received_at,
                idempotency_key=cmd.idempotency_key,
                metadata=dict(cmd.metadata),
            )
            uow.source_artifacts.add(artifact)

            # Flush parents first to keep SQLite FK checks deterministic.
            uow.flush()
            self._record_hash_internal(
                uow,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.SOURCE_ARTIFACT,
                subject_id=artifact_id,
                prov_entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                hash_value=cmd.content_hash,
            )
            self._enqueue_event(
                uow,
                aggregate_kind="source_artifact",
                aggregate_id=artifact_id,
                event_type="source_artifact.recorded",
                payload={
                    "source_artifact_id": str(artifact_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "content_hash": cmd.content_hash,
                },
            )
            PROVENANCE_RECORDS.labels(kind="source_artifact", outcome="created").inc()
            return artifact

    def record_source_artifact_revision(
        self, uow: UnitOfWork, cmd: RecordSourceArtifactRevisionCommand
    ) -> SourceArtifactRevision:
        with record_recorder_duration("record_source_artifact_revision"):
            existing = uow.source_artifact_revisions.get_by_artifact_and_revision(
                cmd.source_artifact_id, cmd.revision_number
            )
            if existing is not None:
                return existing

            artifact = uow.source_artifacts.get(cmd.source_artifact_id)
            if artifact is None:
                raise NotFoundError(f"SourceArtifact {cmd.source_artifact_id} not found")

            run = self._require_pipeline_run(uow, artifact.pipeline_run_id)
            bundle = self._ensure_bundle(uow, run.pipeline_run_id, ProvBundleType.PIPELINE_RUN)

            revision_id = cmd.source_artifact_revision_id or new_uuid7()
            entity_id = cmd.prov_entity_id or new_uuid7()
            received_at = cmd.received_at or utcnow()

            entity = ProvEntity(
                entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                pipeline_run_id=run.pipeline_run_id,
                entity_type=ProvEntityType.SOURCE_ARTIFACT_REVISION,
                entity_kind="source_artifact_revision",
                entity_ref_id=revision_id,
                business_key=f"{cmd.source_artifact_id}:{cmd.revision_number}",
                name=f"revision-{cmd.revision_number}",
                content_hash=cmd.content_hash,
                created_at=received_at,
            )
            uow.prov_entities.add(entity)
            uow.flush()

            revision = SourceArtifactRevision(
                source_artifact_revision_id=revision_id,
                source_artifact_id=cmd.source_artifact_id,
                revision_number=cmd.revision_number,
                storage_uri=cmd.storage_uri,
                content_hash=cmd.content_hash,
                mime_type=cmd.mime_type,
                file_size_bytes=cmd.file_size_bytes,
                received_at=received_at,
                is_current=cmd.is_current,
                prov_entity_id=entity_id,
                metadata=dict(cmd.metadata),
            )
            uow.source_artifact_revisions.add(revision)

            self._add_prov_revision(
                uow,
                previous_entity_id=artifact.prov_entity_id,
                new_entity_id=entity_id,
                revised_at=received_at,
                revision_reason="source_artifact_revision",
                metadata={},
                invalidate_previous=False,
            )

            # Flush parents first to keep SQLite FK checks deterministic.
            uow.flush()
            self._record_hash_internal(
                uow,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.SOURCE_ARTIFACT_REVISION,
                subject_id=revision_id,
                prov_entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                hash_value=cmd.content_hash,
            )
            self._enqueue_event(
                uow,
                aggregate_kind="source_artifact_revision",
                aggregate_id=revision_id,
                event_type="source_artifact_revision.recorded",
                payload={
                    "source_artifact_revision_id": str(revision_id),
                    "source_artifact_id": str(cmd.source_artifact_id),
                    "revision_number": cmd.revision_number,
                },
            )
            PROVENANCE_RECORDS.labels(kind="source_artifact_revision", outcome="created").inc()
            return revision

    # --------------- wrapper_definition ---------------

    def record_wrapper_definition(
        self, uow: UnitOfWork, cmd: RecordWrapperDefinitionCommand
    ) -> WrapperDefinition:
        with record_recorder_duration("record_wrapper_definition"):
            existing = uow.wrapper_definitions.get_by_name_version(
                cmd.wrapper_name, cmd.wrapper_version
            )
            if existing is not None:
                return existing
            definition = WrapperDefinition(
                wrapper_definition_id=cmd.wrapper_definition_id or new_uuid7(),
                wrapper_name=cmd.wrapper_name,
                wrapper_version=cmd.wrapper_version,
                source_layout_name=cmd.source_layout_name,
                source_layout_version=cmd.source_layout_version,
                schema_version=cmd.schema_version,
                code_hash=cmd.code_hash,
                wrapper_code_hash=cmd.wrapper_code_hash,
                input_schema_hash=cmd.input_schema_hash,
                output_schema_hash=cmd.output_schema_hash,
                is_active=True,
                created_at=utcnow(),
                metadata=dict(cmd.metadata),
            )
            uow.wrapper_definitions.add(definition)
            PROVENANCE_RECORDS.labels(kind="wrapper_definition", outcome="created").inc()
            return definition

    # --------------- wrapper_execution ---------------

    def record_wrapper_execution(
        self, uow: UnitOfWork, cmd: RecordWrapperExecutionCommand
    ) -> WrapperExecution:
        with record_recorder_duration("record_wrapper_execution"):
            if cmd.idempotency_key:
                existing = uow.wrapper_executions.get_by_idempotency_key(cmd.idempotency_key)
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="record_wrapper_execution",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "pipeline_run_id": existing.pipeline_run_id,
                            "wrapper_definition_id": existing.wrapper_definition_id,
                            "input_artifact_id": existing.input_artifact_id,
                            "input_source_artifact_revision_id": existing.input_source_artifact_revision_id,
                        },
                        incoming_values={
                            "pipeline_run_id": cmd.pipeline_run_id,
                            "wrapper_definition_id": cmd.wrapper_definition_id,
                            "input_artifact_id": cmd.input_artifact_id,
                            "input_source_artifact_revision_id": cmd.input_source_artifact_revision_id,
                        },
                    )
                    return existing

            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)

            wrapper_def = uow.wrapper_definitions.get(cmd.wrapper_definition_id)
            if wrapper_def is None:
                raise NotFoundError(
                    f"WrapperDefinition {cmd.wrapper_definition_id} not found"
                )
            input_artifact = uow.source_artifacts.get(cmd.input_artifact_id)
            if input_artifact is None:
                raise InvariantViolationError(
                    "wrapper_execution requires an existing source_artifact",
                    details={"input_artifact_id": str(cmd.input_artifact_id)},
                )
            if input_artifact.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "input_artifact does not belong to the same pipeline_run",
                )

            revision: SourceArtifactRevision | None = None
            if cmd.input_source_artifact_revision_id is not None:
                revision = uow.source_artifact_revisions.get(
                    cmd.input_source_artifact_revision_id
                )
                if revision is None:
                    raise NotFoundError(
                        f"SourceArtifactRevision {cmd.input_source_artifact_revision_id} not found"
                    )
                if revision.source_artifact_id != cmd.input_artifact_id:
                    raise InvariantViolationError(
                        "input_source_artifact_revision does not match input_artifact_id",
                    )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.WRAPPER_EXECUTION
            )

            agent = self._ensure_software_agent(
                uow,
                external_reference=cmd.executor_agent_external_reference
                or f"wrapper:{wrapper_def.wrapper_name}@{wrapper_def.wrapper_version}",
                name=cmd.executor_agent_name
                or f"{wrapper_def.wrapper_name}@{wrapper_def.wrapper_version}",
            )

            activity_id = cmd.prov_activity_id or new_uuid7()
            execution_id = cmd.wrapper_execution_id or new_uuid7()
            recorded_at = utcnow()
            activity = ProvActivity(
                activity_id=activity_id,
                bundle_id=bundle.bundle_id,
                pipeline_run_id=run.pipeline_run_id,
                activity_type=ProvActivityType.WRAPPER_EXECUTION,
                business_key=str(execution_id),
                name=f"{wrapper_def.wrapper_name}@{wrapper_def.wrapper_version}",
                status=cmd.execution_status.value,
                started_at=cmd.started_at,
                ended_at=cmd.finished_at,
                software_version=self.SOFTWARE_VERSION,
                recorded_at=recorded_at,
            )
            uow.prov_activities.add(activity)
            uow.flush()

            used_entity_id = (
                revision.prov_entity_id
                if revision is not None and revision.prov_entity_id is not None
                else input_artifact.prov_entity_id
            )
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=used_entity_id,
                    role=(
                        "input_source_artifact_revision"
                        if revision is not None
                        else "input_artifact"
                    ),
                    used_at=cmd.started_at,
                )
            )
            uow.prov_relations.add_associated_with(
                ProvAssociatedWith(
                    association_id=new_uuid7(),
                    activity_id=activity_id,
                    agent_id=agent.agent_id,
                    role="executor",
                )
            )

            execution = WrapperExecution(
                wrapper_execution_id=execution_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_activity_id=activity_id,
                wrapper_definition_id=cmd.wrapper_definition_id,
                input_artifact_id=cmd.input_artifact_id,
                execution_status=cmd.execution_status,
                started_at=cmd.started_at,
                finished_at=cmd.finished_at,
                warning_count=cmd.warning_count,
                error_count=cmd.error_count,
                execution_log_uri=cmd.execution_log_uri,
                idempotency_key=cmd.idempotency_key,
                input_source_artifact_revision_id=cmd.input_source_artifact_revision_id,
                execution_payload_hash=cmd.execution_payload_hash,
                runtime_version=cmd.runtime_version,
                metadata=dict(cmd.metadata),
            )
            uow.wrapper_executions.add(execution)

            self._enqueue_event(
                uow,
                aggregate_kind="wrapper_execution",
                aggregate_id=execution_id,
                event_type="wrapper_execution.recorded",
                payload={
                    "wrapper_execution_id": str(execution_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "wrapper_definition_id": str(cmd.wrapper_definition_id),
                    "input_artifact_id": str(cmd.input_artifact_id),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="wrapper_execution", outcome=cmd.execution_status.value
            ).inc()
            return execution

    # --------------- normalized_batch ---------------

    def record_normalized_batch(
        self, uow: UnitOfWork, cmd: RecordNormalizedBatchCommand
    ) -> NormalizedBatch:
        with record_recorder_duration("record_normalized_batch"):
            if cmd.idempotency_key:
                existing = uow.normalized_batches.get_by_idempotency_key(cmd.idempotency_key)
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="record_normalized_batch",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "pipeline_run_id": existing.pipeline_run_id,
                            "wrapper_execution_id": existing.wrapper_execution_id,
                            "batch_code": existing.batch_code,
                            "schema_version": existing.schema_version,
                        },
                        incoming_values={
                            "pipeline_run_id": cmd.pipeline_run_id,
                            "wrapper_execution_id": cmd.wrapper_execution_id,
                            "batch_code": cmd.batch_code,
                            "schema_version": cmd.schema_version,
                        },
                    )
                    return existing

            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            execution = uow.wrapper_executions.get(cmd.wrapper_execution_id)
            if execution is None:
                raise InvariantViolationError(
                    "normalized_batch requires an existing wrapper_execution",
                    details={"wrapper_execution_id": str(cmd.wrapper_execution_id)},
                )
            if execution.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "wrapper_execution belongs to a different pipeline_run",
                )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.WRAPPER_EXECUTION
            )

            entity_id = cmd.prov_entity_id or new_uuid7()
            batch_id = cmd.normalized_batch_id or new_uuid7()
            generated_at = cmd.generated_at or utcnow()

            entity = ProvEntity(
                entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                pipeline_run_id=run.pipeline_run_id,
                entity_type=ProvEntityType.NORMALIZED_BATCH,
                entity_kind="normalized_batch",
                entity_ref_id=batch_id,
                business_key=cmd.batch_code,
                name=cmd.batch_code,
                content_hash=cmd.content_hash,
                version_label=cmd.schema_version,
                created_at=generated_at,
            )
            uow.prov_entities.add(entity)
            uow.flush()

            uow.prov_relations.add_generated(
                ProvGenerated(
                    generated_id=new_uuid7(),
                    entity_id=entity_id,
                    activity_id=execution.prov_activity_id,
                    generated_at=generated_at,
                )
            )
            uow.prov_relations.add_derived_from(
                ProvDerivedFrom(
                    derived_id=new_uuid7(),
                    generated_entity_id=entity_id,
                    source_entity_id=self._derivation_source_entity_for_normalization(
                        uow, execution
                    ),
                    derivation_type="wrapper_normalization",
                )
            )

            batch = NormalizedBatch(
                normalized_batch_id=batch_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                wrapper_execution_id=cmd.wrapper_execution_id,
                batch_code=cmd.batch_code,
                schema_version=cmd.schema_version,
                record_count=cmd.record_count,
                storage_uri=cmd.storage_uri,
                content_hash=cmd.content_hash,
                generated_at=generated_at,
                idempotency_key=cmd.idempotency_key,
                metadata=dict(cmd.metadata),
            )
            uow.normalized_batches.add(batch)

            if cmd.content_hash:
                # Flush parents first to keep SQLite FK checks deterministic.
                uow.flush()
                self._record_hash_internal(
                    uow,
                    pipeline_run_id=run.pipeline_run_id,
                    subject_kind=HashSubjectKind.NORMALIZED_BATCH,
                    subject_id=batch_id,
                    prov_entity_id=entity_id,
                    bundle_id=bundle.bundle_id,
                    hash_value=cmd.content_hash,
                )

            self._enqueue_event(
                uow,
                aggregate_kind="normalized_batch",
                aggregate_id=batch_id,
                event_type="normalized_batch.recorded",
                payload={
                    "normalized_batch_id": str(batch_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "wrapper_execution_id": str(cmd.wrapper_execution_id),
                    "record_count": cmd.record_count,
                },
            )
            PROVENANCE_RECORDS.labels(kind="normalized_batch", outcome="created").inc()
            return batch

    # --------------- semantic_integration ---------------

    def record_semantic_integration(
        self, uow: UnitOfWork, cmd: RecordSemanticIntegrationCommand
    ) -> SemanticIntegrationExecution:
        with record_recorder_duration("record_semantic_integration"):
            if cmd.idempotency_key:
                existing = uow.semantic_integration_executions.get_by_idempotency_key(
                    cmd.idempotency_key
                )
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="record_semantic_integration",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "pipeline_run_id": existing.pipeline_run_id,
                            "normalized_batch_id": existing.normalized_batch_id,
                            "ontology_name": existing.ontology_name,
                            "ontology_version": existing.ontology_version,
                            "mapping_rule_version": existing.mapping_rule_version,
                        },
                        incoming_values={
                            "pipeline_run_id": cmd.pipeline_run_id,
                            "normalized_batch_id": cmd.normalized_batch_id,
                            "ontology_name": cmd.ontology_name,
                            "ontology_version": cmd.ontology_version,
                            "mapping_rule_version": cmd.mapping_rule_version,
                        },
                    )
                    return existing
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            batch = uow.normalized_batches.get(cmd.normalized_batch_id)
            if batch is None:
                raise InvariantViolationError(
                    "semantic_integration requires an existing normalized_batch",
                    details={"normalized_batch_id": str(cmd.normalized_batch_id)},
                )
            if batch.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "normalized_batch belongs to a different pipeline_run",
                )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.SEMANTIC_INTEGRATION
            )
            agent = self._ensure_software_agent(
                uow,
                external_reference=cmd.integrator_agent_external_reference
                or f"semantic-integrator:{cmd.ontology_name}@{cmd.ontology_version}",
                name=cmd.integrator_agent_name or "semantic-integrator",
            )

            activity_id = cmd.prov_activity_id or new_uuid7()
            integration_id = cmd.semantic_integration_execution_id or new_uuid7()

            uow.prov_activities.add(
                ProvActivity(
                    activity_id=activity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    activity_type=ProvActivityType.SEMANTIC_INTEGRATION,
                    business_key=str(integration_id),
                    name=f"semantic-integration:{cmd.ontology_name}@{cmd.ontology_version}",
                    status=cmd.execution_status.value,
                    started_at=cmd.started_at,
                    ended_at=cmd.finished_at,
                    software_version=self.SOFTWARE_VERSION,
                    recorded_at=utcnow(),
                )
            )
            uow.flush()
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=batch.prov_entity_id,
                    role="input_batch",
                    used_at=cmd.started_at,
                )
            )
            uow.prov_relations.add_associated_with(
                ProvAssociatedWith(
                    association_id=new_uuid7(),
                    activity_id=activity_id,
                    agent_id=agent.agent_id,
                    role="integrator",
                )
            )

            integration = SemanticIntegrationExecution(
                semantic_integration_execution_id=integration_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_activity_id=activity_id,
                normalized_batch_id=cmd.normalized_batch_id,
                ontology_name=cmd.ontology_name,
                ontology_version=cmd.ontology_version,
                mapping_rule_version=cmd.mapping_rule_version,
                execution_status=cmd.execution_status,
                started_at=cmd.started_at,
                finished_at=cmd.finished_at,
                triples_generated=cmd.triples_generated,
                idempotency_key=cmd.idempotency_key,
                metadata=dict(cmd.metadata),
            )
            uow.semantic_integration_executions.add(integration)

            self._enqueue_event(
                uow,
                aggregate_kind="semantic_integration_execution",
                aggregate_id=integration_id,
                event_type="semantic_integration.recorded",
                payload={
                    "semantic_integration_execution_id": str(integration_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "normalized_batch_id": str(cmd.normalized_batch_id),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="semantic_integration", outcome=cmd.execution_status.value
            ).inc()
            return integration

    # --------------- canonical_snapshot ---------------

    def record_canonical_snapshot(
        self, uow: UnitOfWork, cmd: RecordCanonicalSnapshotCommand
    ) -> CanonicalSnapshot:
        with record_recorder_duration("record_canonical_snapshot"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            integration = uow.semantic_integration_executions.get(
                cmd.semantic_integration_execution_id
            )
            if integration is None:
                raise InvariantViolationError(
                    "canonical_snapshot requires an existing semantic_integration_execution",
                    details={
                        "semantic_integration_execution_id": str(
                            cmd.semantic_integration_execution_id
                        )
                    },
                )
            if integration.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "semantic_integration_execution belongs to a different pipeline_run",
                )

            from provenance_service.domain.audit.hash_payloads import (
                canonical_snapshot_hash_payload,
            )

            snapshot_hash = compute_hash_hex(
                canonical_snapshot_hash_payload(
                    graph_name=cmd.graph_name,
                    snapshot_label=cmd.snapshot_label,
                    schema_version=cmd.schema_version,
                    payload=cmd.payload,
                    items=cmd.items,
                )
            )

            existing = uow.canonical_snapshots.get_by_hash(snapshot_hash)
            if existing is not None:
                return existing

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.SEMANTIC_INTEGRATION
            )

            entity_id = cmd.prov_entity_id or new_uuid7()
            snapshot_id = cmd.canonical_snapshot_id or new_uuid7()
            published_at = cmd.published_at or utcnow()

            uow.prov_entities.add(
                ProvEntity(
                    entity_id=entity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    entity_type=ProvEntityType.CANONICAL_SNAPSHOT,
                    entity_kind="canonical_snapshot",
                    entity_ref_id=snapshot_id,
                    business_key=cmd.snapshot_label,
                    name=cmd.snapshot_label,
                    content_hash=snapshot_hash,
                    version_label=cmd.schema_version,
                    created_at=published_at,
                )
            )
            uow.flush()
            batch_entity_id = uow.normalized_batches.get(integration.normalized_batch_id)
            if batch_entity_id is not None:
                uow.prov_relations.add_derived_from(
                    ProvDerivedFrom(
                        derived_id=new_uuid7(),
                        generated_entity_id=entity_id,
                        source_entity_id=batch_entity_id.prov_entity_id,
                        derivation_type="semantic_integration",
                    )
                )
            uow.prov_relations.add_generated(
                ProvGenerated(
                    generated_id=new_uuid7(),
                    entity_id=entity_id,
                    activity_id=integration.prov_activity_id,
                    generated_at=published_at,
                )
            )

            snapshot = CanonicalSnapshot(
                canonical_snapshot_id=snapshot_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                semantic_integration_execution_id=cmd.semantic_integration_execution_id,
                graph_name=cmd.graph_name,
                snapshot_label=cmd.snapshot_label,
                snapshot_hash=snapshot_hash,
                schema_version=cmd.schema_version,
                canonical_schema_version=cmd.canonical_schema_version or cmd.schema_version,
                item_count=len(cmd.items),
                snapshot_payload_ref=cmd.snapshot_payload_ref or cmd.storage_uri,
                storage_uri=cmd.storage_uri,
                payload=dict(cmd.payload) if cmd.payload is not None else None,
                reporting_period_id=cmd.reporting_period_id,
                published_at=published_at,
                metadata=dict(cmd.metadata),
            )
            uow.canonical_snapshots.add(snapshot)
            # Flush parent snapshot before items (SQLite FK enforcement).
            uow.flush()

            from provenance_service.domain.semantic.entities import CanonicalSnapshotItem

            for item in cmd.items:
                item_payload = dict(item)
                item_key = str(item_payload.pop("item_key", "")) or new_uuid7().hex
                uow.canonical_snapshots.add_item(
                    CanonicalSnapshotItem(
                        canonical_snapshot_item_id=new_uuid7(),
                        canonical_snapshot_id=snapshot_id,
                        item_key=item_key,
                        payload=item_payload,
                        item_hash=compute_hash_hex(item_payload),
                    )
                )

            uow.flush()
            self._record_hash_internal(
                uow,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.CANONICAL_SNAPSHOT,
                subject_id=snapshot_id,
                prov_entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                hash_value=snapshot_hash,
            )

            self._enqueue_event(
                uow,
                aggregate_kind="canonical_snapshot",
                aggregate_id=snapshot_id,
                event_type="canonical_snapshot.recorded",
                payload={
                    "canonical_snapshot_id": str(snapshot_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "snapshot_hash": snapshot_hash,
                    "graph_name": cmd.graph_name,
                },
            )
            PROVENANCE_RECORDS.labels(kind="canonical_snapshot", outcome="created").inc()
            return snapshot

    def record_ontology_resource_link(
        self, uow: UnitOfWork, cmd: RecordOntologyResourceLinkCommand
    ) -> OntologyResourceLink:
        with record_recorder_duration("record_ontology_resource_link"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            if cmd.canonical_snapshot_id is not None:
                snapshot = uow.canonical_snapshots.get(cmd.canonical_snapshot_id)
                if snapshot is None:
                    raise NotFoundError(
                        f"CanonicalSnapshot {cmd.canonical_snapshot_id} not found"
                    )
                if snapshot.pipeline_run_id != run.pipeline_run_id:
                    raise InvariantViolationError(
                        "canonical_snapshot belongs to a different pipeline_run",
                        details={
                            "canonical_snapshot_id": str(cmd.canonical_snapshot_id),
                            "pipeline_run_id": str(cmd.pipeline_run_id),
                        },
                    )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.PUBLICATION
            )
            link_id = cmd.ontology_resource_link_id or new_uuid7()
            entity_id = cmd.prov_entity_id or new_uuid7()
            published_at = cmd.published_at or utcnow()

            if cmd.prov_entity_id is None:
                uow.prov_entities.add(
                    ProvEntity(
                        entity_id=entity_id,
                        bundle_id=bundle.bundle_id,
                        pipeline_run_id=run.pipeline_run_id,
                        entity_type=ProvEntityType.ONTOLOGY_RESOURCE,
                        entity_kind="ontology_resource",
                        business_key=cmd.ontology_uri,
                        name=cmd.ontology_uri,
                        version_label=cmd.ontology_version,
                        created_at=published_at,
                    )
                )
            elif uow.prov_entities.get(entity_id) is None:
                raise NotFoundError(f"ProvEntity {entity_id} not found")

            link = OntologyResourceLink(
                ontology_resource_link_id=link_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                canonical_snapshot_id=cmd.canonical_snapshot_id,
                ontology_uri=cmd.ontology_uri,
                rdf_class=cmd.rdf_class,
                graph_name=cmd.graph_name,
                ontology_version=cmd.ontology_version,
                publication_stage=cmd.publication_stage,
                published_at=published_at,
                metadata=dict(cmd.metadata),
            )
            uow.ontology_resource_links.add(link)
            self._enqueue_event(
                uow,
                aggregate_kind="ontology_resource_link",
                aggregate_id=link_id,
                event_type="ontology_resource_link.recorded",
                payload={
                    "ontology_resource_link_id": str(link_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "ontology_uri": cmd.ontology_uri,
                    "graph_name": cmd.graph_name,
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="ontology_resource_link", outcome="created"
            ).inc()
            return link

    # --------------- calculation_method / version ---------------

    def record_calculation_method(
        self, uow: UnitOfWork, cmd: RecordCalculationMethodCommand
    ) -> CalculationMethod:
        existing = uow.calculation_methods.get_by_code(cmd.method_code)
        if existing is not None:
            return existing
        method = CalculationMethod(
            calculation_method_id=cmd.calculation_method_id or new_uuid7(),
            method_code=cmd.method_code,
            method_name=cmd.method_name,
            description=cmd.description,
            created_at=utcnow(),
        )
        uow.calculation_methods.add(method)
        PROVENANCE_RECORDS.labels(kind="calculation_method", outcome="created").inc()
        return method

    def record_calculation_method_version(
        self, uow: UnitOfWork, cmd: RecordCalculationMethodVersionCommand
    ) -> CalculationMethodVersion:
        if uow.calculation_methods.get(cmd.calculation_method_id) is None:
            raise NotFoundError(
                f"CalculationMethod {cmd.calculation_method_id} not found"
            )
        version = CalculationMethodVersion(
            calculation_method_version_id=cmd.calculation_method_version_id or new_uuid7(),
            calculation_method_id=cmd.calculation_method_id,
            version_label=cmd.version_label,
            formula_reference=cmd.formula_reference,
            formula_hash=cmd.formula_hash,
            method_document_uri=cmd.method_document_uri,
            method_document_hash=cmd.method_document_hash,
            implementation_version=cmd.implementation_version,
            effective_from=cmd.effective_from,
            effective_to=cmd.effective_to,
            status=cmd.status,
            metadata=dict(cmd.metadata),
        )
        uow.calculation_method_versions.add(version)
        PROVENANCE_RECORDS.labels(kind="calculation_method_version", outcome="created").inc()
        return version

    # --------------- calculation_parameter_set ---------------

    def record_calculation_parameter_set(
        self, uow: UnitOfWork, cmd: RecordCalculationParameterSetCommand
    ) -> CalculationParameterSet:
        with record_recorder_duration("record_calculation_parameter_set"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            method_version = uow.calculation_method_versions.get(
                cmd.calculation_method_version_id
            )
            if method_version is None:
                raise NotFoundError(
                    f"CalculationMethodVersion {cmd.calculation_method_version_id} not found"
                )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.CALCULATION
            )

            param_set_id = cmd.calculation_parameter_set_id or new_uuid7()
            entity_id = cmd.prov_entity_id or new_uuid7()
            now = utcnow()

            from provenance_service.domain.audit.hash_payloads import (
                calculation_parameter_set_hash_payload,
            )

            param_hash = compute_hash_hex(
                calculation_parameter_set_hash_payload(
                    calculation_method_version_id=cmd.calculation_method_version_id,
                    values=[
                        {
                            "name": v.parameter_name,
                            "text": v.parameter_value_text,
                            "numeric": v.parameter_value_numeric,
                            "unit": v.parameter_unit,
                            "source": v.parameter_source,
                            "is_user_editable": v.is_user_editable,
                        }
                        for v in cmd.values
                    ],
                )
            )

            uow.prov_entities.add(
                ProvEntity(
                    entity_id=entity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    entity_type=ProvEntityType.CALCULATION_PARAMETER_SET,
                    entity_kind="calculation_parameter_set",
                    entity_ref_id=param_set_id,
                    business_key=str(param_set_id),
                    name=f"parameters@{method_version.version_label}",
                    content_hash=param_hash,
                    created_at=now,
                )
            )
            uow.flush()

            param_set = CalculationParameterSet(
                calculation_parameter_set_id=param_set_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                calculation_method_version_id=cmd.calculation_method_version_id,
                parameter_set_status=cmd.parameter_set_status,
                created_by_agent_id=cmd.created_by_agent_id,
                created_at=now,
                notes=cmd.notes,
                metadata=dict(cmd.metadata),
            )
            uow.calculation_parameter_sets.add(param_set)
            uow.flush()

            for value in cmd.values:
                uow.calculation_parameter_sets.add_value(
                    CalculationParameterValue(
                        calculation_parameter_value_id=new_uuid7(),
                        calculation_parameter_set_id=param_set_id,
                        parameter_name=value.parameter_name,
                        parameter_value_text=value.parameter_value_text,
                        parameter_value_numeric=value.parameter_value_numeric,
                        parameter_unit=value.parameter_unit,
                        parameter_source=value.parameter_source,
                        is_user_editable=value.is_user_editable,
                        metadata=dict(value.metadata),
                    )
                )

            # Flush parents first to keep SQLite FK checks deterministic.
            uow.flush()
            self._record_hash_internal(
                uow,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.CALCULATION_PARAMETER_SET,
                subject_id=param_set_id,
                prov_entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                hash_value=param_hash,
            )
            PROVENANCE_RECORDS.labels(kind="calculation_parameter_set", outcome="created").inc()
            return param_set

    # --------------- calculation_execution ---------------

    def record_calculation_execution(
        self, uow: UnitOfWork, cmd: RecordCalculationExecutionCommand
    ) -> CalculationExecution:
        with record_recorder_duration("record_calculation_execution"):
            if cmd.idempotency_key:
                existing = uow.calculation_executions.get_by_idempotency_key(
                    cmd.idempotency_key
                )
                if existing is not None:
                    self._raise_if_idempotency_payload_mismatch(
                        operation="record_calculation_execution",
                        idempotency_key=cmd.idempotency_key,
                        existing_values={
                            "pipeline_run_id": existing.pipeline_run_id,
                            "canonical_snapshot_id": existing.canonical_snapshot_id,
                            "calculation_method_version_id": existing.calculation_method_version_id,
                            "calculation_parameter_set_id": existing.calculation_parameter_set_id,
                        },
                        incoming_values={
                            "pipeline_run_id": cmd.pipeline_run_id,
                            "canonical_snapshot_id": cmd.canonical_snapshot_id,
                            "calculation_method_version_id": cmd.calculation_method_version_id,
                            "calculation_parameter_set_id": cmd.calculation_parameter_set_id,
                        },
                    )
                    return existing

            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            snapshot = uow.canonical_snapshots.get(cmd.canonical_snapshot_id)
            if snapshot is None:
                raise InvariantViolationError(
                    "calculation_execution requires an existing canonical_snapshot",
                    details={"canonical_snapshot_id": str(cmd.canonical_snapshot_id)},
                )
            if snapshot.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "canonical_snapshot belongs to a different pipeline_run",
                )
            method_version = uow.calculation_method_versions.get(
                cmd.calculation_method_version_id
            )
            if method_version is None:
                raise InvariantViolationError(
                    "calculation_execution requires an existing calculation_method_version",
                    details={
                        "calculation_method_version_id": str(
                            cmd.calculation_method_version_id
                        )
                    },
                )
            param_set = uow.calculation_parameter_sets.get(cmd.calculation_parameter_set_id)
            if param_set is None:
                raise InvariantViolationError(
                    "calculation_execution requires an existing calculation_parameter_set",
                    details={
                        "calculation_parameter_set_id": str(cmd.calculation_parameter_set_id)
                    },
                )
            if param_set.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "calculation_parameter_set belongs to a different pipeline_run",
                )

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.CALCULATION
            )
            agent = self._ensure_software_agent(
                uow,
                external_reference=cmd.executor_agent_external_reference
                or f"calculation-engine:{method_version.version_label}",
                name=cmd.executor_agent_name or "calculation-engine",
            )

            activity_id = cmd.prov_activity_id or new_uuid7()
            execution_id = cmd.calculation_execution_id or new_uuid7()

            uow.prov_activities.add(
                ProvActivity(
                    activity_id=activity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    activity_type=ProvActivityType.CALCULATION_EXECUTION,
                    business_key=str(execution_id),
                    name=f"calculation:{method_version.version_label}",
                    status=cmd.execution_status.value,
                    started_at=cmd.started_at,
                    ended_at=cmd.finished_at,
                    software_version=self.SOFTWARE_VERSION,
                    recorded_at=utcnow(),
                )
            )
            uow.flush()
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=snapshot.prov_entity_id,
                    role="input_snapshot",
                    used_at=cmd.started_at,
                )
            )
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=param_set.prov_entity_id,
                    role="parameter_set",
                    used_at=cmd.started_at,
                )
            )
            uow.prov_relations.add_associated_with(
                ProvAssociatedWith(
                    association_id=new_uuid7(),
                    activity_id=activity_id,
                    agent_id=agent.agent_id,
                    role="executor",
                )
            )

            execution = CalculationExecution(
                calculation_execution_id=execution_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_activity_id=activity_id,
                canonical_snapshot_id=cmd.canonical_snapshot_id,
                calculation_method_version_id=cmd.calculation_method_version_id,
                calculation_parameter_set_id=cmd.calculation_parameter_set_id,
                execution_status=cmd.execution_status,
                started_at=cmd.started_at,
                finished_at=cmd.finished_at,
                execution_log_uri=cmd.execution_log_uri,
                idempotency_key=cmd.idempotency_key,
                reporting_period_id=cmd.reporting_period_id,
                metadata=dict(cmd.metadata),
            )
            uow.calculation_executions.add(execution)

            self._enqueue_event(
                uow,
                aggregate_kind="calculation_execution",
                aggregate_id=execution_id,
                event_type="calculation_execution.recorded",
                payload={
                    "calculation_execution_id": str(execution_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "canonical_snapshot_id": str(cmd.canonical_snapshot_id),
                    "calculation_method_version_id": str(
                        cmd.calculation_method_version_id
                    ),
                    "calculation_parameter_set_id": str(cmd.calculation_parameter_set_id),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="calculation_execution", outcome=cmd.execution_status.value
            ).inc()
            return execution

    # --------------- calculation_result_set ---------------

    def record_calculation_result_set(
        self, uow: UnitOfWork, cmd: RecordCalculationResultSetCommand
    ) -> CalculationResultSet:
        with record_recorder_duration("record_calculation_result_set"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            execution = uow.calculation_executions.get(cmd.calculation_execution_id)
            if execution is None:
                raise InvariantViolationError(
                    "calculation_result_set requires an existing calculation_execution",
                    details={"calculation_execution_id": str(cmd.calculation_execution_id)},
                )
            if execution.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "calculation_execution belongs to a different pipeline_run",
                )
            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.CALCULATION
            )
            entity_id = cmd.prov_entity_id or new_uuid7()
            result_set_id = cmd.calculation_result_set_id or new_uuid7()
            generated_at = cmd.generated_at or utcnow()

            from provenance_service.domain.audit.hash_payloads import (
                calculation_result_set_hash_payload,
            )

            summary_hash = compute_hash_hex(
                calculation_result_set_hash_payload(
                    calculation_execution_id=cmd.calculation_execution_id,
                    items=[
                        {
                            "type": item.result_type.value,
                            "name": item.result_name,
                            "value": item.result_value,
                            "unit": item.result_unit,
                            "dimension_reference": item.dimension_reference,
                        }
                        for item in cmd.items
                    ],
                )
            )

            uow.prov_entities.add(
                ProvEntity(
                    entity_id=entity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    entity_type=ProvEntityType.CALCULATION_RESULT_SET,
                    entity_kind="calculation_result_set",
                    entity_ref_id=result_set_id,
                    business_key=str(result_set_id),
                    name=f"result_set:{cmd.calculation_execution_id}",
                    content_hash=summary_hash,
                    created_at=generated_at,
                )
            )
            uow.flush()
            uow.prov_relations.add_generated(
                ProvGenerated(
                    generated_id=new_uuid7(),
                    entity_id=entity_id,
                    activity_id=execution.prov_activity_id,
                    generated_at=generated_at,
                )
            )

            result_set = CalculationResultSet(
                calculation_result_set_id=result_set_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=entity_id,
                calculation_execution_id=cmd.calculation_execution_id,
                result_set_status=cmd.result_set_status,
                generated_at=generated_at,
                summary_hash=summary_hash,
                reporting_period_id=cmd.reporting_period_id,
                result_scope=cmd.result_scope,
                consolidation_type=cmd.consolidation_type,
                supersedes_id=cmd.supersedes_id,
                correction_reason=cmd.correction_reason,
                metadata=dict(cmd.metadata),
            )
            uow.calculation_result_sets.add(result_set)
            uow.flush()

            for item in cmd.items:
                uow.calculation_result_sets.add_item(
                    CalculationResultItem(
                        calculation_result_item_id=new_uuid7(),
                        calculation_result_set_id=result_set_id,
                        result_type=item.result_type,
                        result_name=item.result_name,
                        result_value=item.result_value,
                        result_unit=item.result_unit,
                        dimension_reference=item.dimension_reference,
                        metadata=dict(item.metadata),
                    )
                )

            # Flush parents first to keep SQLite FK checks deterministic.
            uow.flush()
            self._record_hash_internal(
                uow,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.CALCULATION_RESULT_SET,
                subject_id=result_set_id,
                prov_entity_id=entity_id,
                bundle_id=bundle.bundle_id,
                hash_value=summary_hash,
            )

            self._enqueue_event(
                uow,
                aggregate_kind="calculation_result_set",
                aggregate_id=result_set_id,
                event_type="calculation_result_set.recorded",
                payload={
                    "calculation_result_set_id": str(result_set_id),
                    "calculation_execution_id": str(cmd.calculation_execution_id),
                    "pipeline_run_id": str(run.pipeline_run_id),
                    "summary_hash": summary_hash,
                    "result_count": len(cmd.items),
                },
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=cmd.calculation_execution_id,
                calculation_result_set_id=result_set_id,
                reporting_period_id=cmd.reporting_period_id,
            )
            if cmd.result_set_status is CalculationResultSetStatus.PRELIMINARY:
                self.record_observable_event(
                    uow,
                    event_type="CALCULATION_PRELIMINARY_RESULT_CREATED",
                    aggregate_type="calculation_result_set",
                    aggregate_id=result_set_id,
                    payload={
                        "event_type": "CALCULATION_PRELIMINARY_RESULT_CREATED",
                        "calculation_result_set_id": str(result_set_id),
                        "calculation_execution_id": str(cmd.calculation_execution_id),
                        "pipeline_run_id": str(run.pipeline_run_id),
                        "reporting_period_id": (
                            str(cmd.reporting_period_id) if cmd.reporting_period_id else None
                        ),
                        "result_scope": (
                            cmd.result_scope.value if cmd.result_scope else None
                        ),
                        "consolidation_type": (
                            cmd.consolidation_type.value if cmd.consolidation_type else None
                        ),
                        "status": cmd.result_set_status.value,
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_execution_id=cmd.calculation_execution_id,
                    calculation_result_set_id=result_set_id,
                    reporting_period_id=cmd.reporting_period_id,
                )
            if cmd.result_scope is ResultScope.MONTHLY and cmd.consolidation_type in (
                ConsolidationType.DAILY_TO_MONTHLY,
                ConsolidationType.DIRECT,
            ):
                self.record_observable_event(
                    uow,
                    event_type="MONTHLY_RESULT_CONSOLIDATED",
                    aggregate_type="calculation_result_set",
                    aggregate_id=result_set_id,
                    payload={
                        "event_type": "MONTHLY_RESULT_CONSOLIDATED",
                        "calculation_result_set_id": str(result_set_id),
                        "reporting_period_id": (
                            str(cmd.reporting_period_id) if cmd.reporting_period_id else None
                        ),
                        "result_scope": "monthly",
                        "consolidation_type": (
                            cmd.consolidation_type.value if cmd.consolidation_type else None
                        ),
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_execution_id=cmd.calculation_execution_id,
                    calculation_result_set_id=result_set_id,
                    reporting_period_id=cmd.reporting_period_id,
                )
            if cmd.result_scope is ResultScope.ANNUAL and cmd.consolidation_type in (
                ConsolidationType.MONTHLY_TO_ANNUAL,
                ConsolidationType.DIRECT,
            ):
                self.record_observable_event(
                    uow,
                    event_type="ANNUAL_RESULT_CONSOLIDATED",
                    aggregate_type="calculation_result_set",
                    aggregate_id=result_set_id,
                    payload={
                        "event_type": "ANNUAL_RESULT_CONSOLIDATED",
                        "calculation_result_set_id": str(result_set_id),
                        "reporting_period_id": (
                            str(cmd.reporting_period_id) if cmd.reporting_period_id else None
                        ),
                        "result_scope": "annual",
                        "consolidation_type": (
                            cmd.consolidation_type.value if cmd.consolidation_type else None
                        ),
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_execution_id=cmd.calculation_execution_id,
                    calculation_result_set_id=result_set_id,
                    reporting_period_id=cmd.reporting_period_id,
                )
            PROVENANCE_RECORDS.labels(kind="calculation_result_set", outcome="created").inc()
            return result_set

    # --------------- calculation_review ---------------

    def record_calculation_review(
        self, uow: UnitOfWork, cmd: RecordCalculationReviewCommand
    ) -> CalculationReview:
        with record_recorder_duration("record_calculation_review"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            result_set = uow.calculation_result_sets.get(cmd.calculation_result_set_id)
            if result_set is None:
                raise InvariantViolationError(
                    "calculation_review requires an existing calculation_result_set",
                    details={
                        "calculation_result_set_id": str(cmd.calculation_result_set_id)
                    },
                )
            if result_set.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "calculation_result_set belongs to a different pipeline_run",
                )
            reviewer = uow.prov_agents.get(cmd.reviewer_agent_id)
            if reviewer is None:
                raise NotFoundError(f"ProvAgent {cmd.reviewer_agent_id} (reviewer) not found")

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.CALCULATION
            )
            activity_id = cmd.prov_activity_id or new_uuid7()
            review_id = cmd.calculation_review_id or new_uuid7()
            reviewed_at = cmd.reviewed_at or utcnow()

            uow.prov_activities.add(
                ProvActivity(
                    activity_id=activity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    activity_type=ProvActivityType.CALCULATION_REVIEW,
                    business_key=str(review_id),
                    name=f"review:{cmd.decision.value}",
                    status=cmd.decision.value,
                    started_at=reviewed_at,
                    ended_at=reviewed_at,
                    software_version=self.SOFTWARE_VERSION,
                    recorded_at=reviewed_at,
                )
            )
            uow.flush()
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=result_set.prov_entity_id,
                    role="reviewed_result_set",
                    used_at=reviewed_at,
                )
            )
            uow.prov_relations.add_associated_with(
                ProvAssociatedWith(
                    association_id=new_uuid7(),
                    activity_id=activity_id,
                    agent_id=cmd.reviewer_agent_id,
                    role="reviewer",
                )
            )

            review = CalculationReview(
                calculation_review_id=review_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_activity_id=activity_id,
                calculation_result_set_id=cmd.calculation_result_set_id,
                reviewer_agent_id=cmd.reviewer_agent_id,
                decision=cmd.decision,
                review_comment=cmd.review_comment,
                reviewed_at=reviewed_at,
                evidence_uri=cmd.evidence_uri,
                reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
                metadata=dict(cmd.metadata),
            )
            uow.calculation_reviews.add(review)

            uow.audit_events.add(
                AuditEvent(
                    audit_event_id=new_uuid7(),
                    event_type=f"calculation_review.{cmd.decision.value}",
                    actor_agent_id=cmd.reviewer_agent_id,
                    subject_kind="calculation_result_set",
                    subject_id=cmd.calculation_result_set_id,
                    payload={
                        "calculation_review_id": str(review_id),
                        "decision": cmd.decision.value,
                        "review_comment": cmd.review_comment,
                    },
                    recorded_at=reviewed_at,
                )
            )
            self._enqueue_event(
                uow,
                aggregate_kind="calculation_review",
                aggregate_id=review_id,
                event_type=f"calculation_review.{cmd.decision.value}",
                payload={
                    "calculation_review_id": str(review_id),
                    "calculation_result_set_id": str(cmd.calculation_result_set_id),
                    "decision": cmd.decision.value,
                },
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=cmd.calculation_result_set_id,
                reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
            )
            if cmd.decision is CalculationReviewDecision.APPROVED:
                self.record_observable_event(
                    uow,
                    event_type="CALCULATION_APPROVED",
                    aggregate_type="calculation_result_set",
                    aggregate_id=cmd.calculation_result_set_id,
                    payload={
                        "event_type": "CALCULATION_APPROVED",
                        "aggregate_type": "calculation_result_set",
                        "aggregate_id": str(cmd.calculation_result_set_id),
                        "calculation_result_set_id": str(cmd.calculation_result_set_id),
                        "calculation_execution_id": str(result_set.calculation_execution_id),
                        "pipeline_run_id": str(run.pipeline_run_id),
                        "reporting_period_id": (
                            str(cmd.reporting_period_id or result_set.reporting_period_id)
                            if (cmd.reporting_period_id or result_set.reporting_period_id)
                            else None
                        ),
                        "result_scope": (
                            result_set.result_scope.value if result_set.result_scope else None
                        ),
                        "consolidation_type": (
                            result_set.consolidation_type.value
                            if result_set.consolidation_type
                            else None
                        ),
                        "approved_at": reviewed_at.isoformat(),
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_execution_id=result_set.calculation_execution_id,
                    calculation_result_set_id=cmd.calculation_result_set_id,
                    reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
                )
            elif cmd.decision is CalculationReviewDecision.REJECTED:
                self.record_observable_event(
                    uow,
                    event_type="CALCULATION_REJECTED",
                    aggregate_type="calculation_result_set",
                    aggregate_id=cmd.calculation_result_set_id,
                    payload={
                        "event_type": "CALCULATION_REJECTED",
                        "calculation_result_set_id": str(cmd.calculation_result_set_id),
                        "pipeline_run_id": str(run.pipeline_run_id),
                        "decision": cmd.decision.value,
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_result_set_id=cmd.calculation_result_set_id,
                    reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
                )
            PROVENANCE_RECORDS.labels(
                kind="calculation_review", outcome=cmd.decision.value
            ).inc()
            if cmd.decision is CalculationReviewDecision.APPROVED:
                rs = uow.calculation_result_sets.get(cmd.calculation_result_set_id)
                if rs is not None and rs.result_set_status is CalculationResultSetStatus.PRELIMINARY:
                    uow.calculation_result_sets.update_status(
                        cmd.calculation_result_set_id,
                        CalculationResultSetStatus.APPROVED,
                    )
                    uow.calculation_result_sets.update_approved_at(
                        cmd.calculation_result_set_id, reviewed_at
                    )
            return review

    # --------------- result_publication ---------------

    def record_result_publication(
        self, uow: UnitOfWork, cmd: RecordResultPublicationCommand
    ) -> ResultPublicationExecution:
        with record_recorder_duration("record_result_publication"):
            run = self._require_pipeline_run(uow, cmd.pipeline_run_id)
            result_set = uow.calculation_result_sets.get(cmd.calculation_result_set_id)
            if result_set is None:
                raise InvariantViolationError(
                    "result_publication requires an existing calculation_result_set",
                )
            if result_set.pipeline_run_id != run.pipeline_run_id:
                raise InvariantViolationError(
                    "calculation_result_set belongs to a different pipeline_run",
                )
            if result_set.result_set_status is not CalculationResultSetStatus.APPROVED:
                raise InvariantViolationError(
                    "result_publication requires an APPROVED calculation_result_set",
                    details={"result_set_status": result_set.result_set_status.value},
                )

            review_id = cmd.calculation_review_id
            if review_id is not None:
                review = uow.calculation_reviews.get(review_id)
                if review is None:
                    raise InvariantViolationError(
                        "calculation_review_id provided but review not found",
                    )
                if review.decision is not CalculationReviewDecision.APPROVED:
                    raise InvariantViolationError(
                        "result_publication requires an APPROVED review when one is supplied",
                        details={"decision": review.decision.value},
                    )
                if review.pipeline_run_id != run.pipeline_run_id:
                    raise InvariantViolationError(
                        "calculation_review belongs to a different pipeline_run",
                    )
            else:
                reviews = uow.calculation_reviews.list_for_result_set(
                    cmd.calculation_result_set_id
                )
                approved = [
                    r
                    for r in reviews
                    if r.decision is CalculationReviewDecision.APPROVED
                ]
                if not approved:
                    raise InvariantViolationError(
                        "result_publication requires an APPROVED calculation_review",
                    )
                review_id = approved[-1].calculation_review_id

            bundle = self._ensure_bundle(
                uow, run.pipeline_run_id, ProvBundleType.PUBLICATION
            )
            agent = self._ensure_software_agent(
                uow,
                external_reference=cmd.publisher_agent_external_reference
                or f"publisher:{cmd.ontology_name}@{cmd.ontology_version}",
                name=cmd.publisher_agent_name or "publisher",
            )

            activity_id = cmd.prov_activity_id or new_uuid7()
            publication_id = cmd.result_publication_execution_id or new_uuid7()
            published_at = cmd.published_at or utcnow()

            uow.prov_activities.add(
                ProvActivity(
                    activity_id=activity_id,
                    bundle_id=bundle.bundle_id,
                    pipeline_run_id=run.pipeline_run_id,
                    activity_type=ProvActivityType.RESULT_PUBLICATION,
                    business_key=str(publication_id),
                    name=f"publication:{cmd.target_graph_name}",
                    status=cmd.publication_status.value,
                    started_at=published_at,
                    ended_at=published_at if cmd.publication_status
                    is ResultPublicationStatus.PUBLISHED
                    else None,
                    software_version=self.SOFTWARE_VERSION,
                    recorded_at=utcnow(),
                )
            )
            uow.flush()
            uow.prov_relations.add_used(
                ProvUsed(
                    used_id=new_uuid7(),
                    activity_id=activity_id,
                    entity_id=result_set.prov_entity_id,
                    role="published_result_set",
                    used_at=published_at,
                )
            )
            uow.prov_relations.add_associated_with(
                ProvAssociatedWith(
                    association_id=new_uuid7(),
                    activity_id=activity_id,
                    agent_id=agent.agent_id,
                    role="publisher",
                )
            )

            publication = ResultPublicationExecution(
                result_publication_execution_id=publication_id,
                pipeline_run_id=run.pipeline_run_id,
                prov_activity_id=activity_id,
                calculation_result_set_id=cmd.calculation_result_set_id,
                calculation_review_id=review_id,
                target_graph_name=cmd.target_graph_name,
                ontology_name=cmd.ontology_name,
                ontology_version=cmd.ontology_version,
                publication_status=cmd.publication_status,
                published_at=published_at,
                reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
                publication_payload_hash=cmd.publication_payload_hash,
                ontology_resource_uri=cmd.ontology_resource_uri or cmd.ontology_uri,
                publication_version=cmd.publication_version,
                metadata=dict(cmd.metadata),
            )
            uow.result_publication_executions.add(publication)

            if cmd.create_ontology_resource_link and cmd.ontology_uri:
                link_entity_id = new_uuid7()
                uow.prov_entities.add(
                    ProvEntity(
                        entity_id=link_entity_id,
                        bundle_id=bundle.bundle_id,
                        pipeline_run_id=run.pipeline_run_id,
                        entity_type=ProvEntityType.ONTOLOGY_RESOURCE,
                        entity_kind="ontology_resource",
                        business_key=cmd.ontology_uri,
                        name=cmd.ontology_uri,
                        version_label=cmd.ontology_version,
                        created_at=published_at,
                    )
                )
                uow.flush()
                uow.prov_relations.add_generated(
                    ProvGenerated(
                        generated_id=new_uuid7(),
                        entity_id=link_entity_id,
                        activity_id=activity_id,
                        generated_at=published_at,
                    )
                )
                uow.ontology_resource_links.add(
                    OntologyResourceLink(
                        ontology_resource_link_id=new_uuid7(),
                        pipeline_run_id=run.pipeline_run_id,
                        prov_entity_id=link_entity_id,
                        canonical_snapshot_id=None,
                        ontology_uri=cmd.ontology_uri,
                        rdf_class=cmd.rdf_class,
                        graph_name=cmd.target_graph_name,
                        ontology_version=cmd.ontology_version,
                        publication_stage=PublicationStage.PUBLICATION_FINAL
                        if cmd.publication_status is ResultPublicationStatus.PUBLISHED
                        else PublicationStage.PRELIMINARY,
                        published_at=published_at,
                        metadata=dict(cmd.metadata),
                    )
                )

            self._enqueue_event(
                uow,
                aggregate_kind="result_publication_execution",
                aggregate_id=publication_id,
                event_type=f"result_publication.{cmd.publication_status.value}",
                payload={
                    "result_publication_execution_id": str(publication_id),
                    "calculation_result_set_id": str(cmd.calculation_result_set_id),
                    "target_graph_name": cmd.target_graph_name,
                    "ontology_name": cmd.ontology_name,
                    "ontology_version": cmd.ontology_version,
                    "status": cmd.publication_status.value,
                },
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=cmd.calculation_result_set_id,
                reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
            )
            if cmd.publication_status is ResultPublicationStatus.PUBLISHED:
                uow.calculation_result_sets.update_published_at(
                    cmd.calculation_result_set_id, published_at
                )
                self.record_observable_event(
                    uow,
                    event_type="APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY",
                    aggregate_type="calculation_result_set",
                    aggregate_id=cmd.calculation_result_set_id,
                    payload={
                        "event_type": "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY",
                        "calculation_result_set_id": str(cmd.calculation_result_set_id),
                        "pipeline_run_id": str(run.pipeline_run_id),
                        "target_graph_name": cmd.target_graph_name,
                        "ontology_name": cmd.ontology_name,
                        "ontology_version": cmd.ontology_version,
                        "ontology_resource_uri": cmd.ontology_resource_uri or cmd.ontology_uri,
                        "publication_payload_hash": cmd.publication_payload_hash,
                        "published_at": published_at.isoformat(),
                    },
                    pipeline_run_id=run.pipeline_run_id,
                    calculation_result_set_id=cmd.calculation_result_set_id,
                    reporting_period_id=cmd.reporting_period_id or result_set.reporting_period_id,
                    source_table="calculation_result_publication_execution",
                    source_record_id=publication_id,
                )
            PROVENANCE_RECORDS.labels(
                kind="result_publication", outcome=cmd.publication_status.value
            ).inc()
            return publication

    def record_result_aggregation_link(
        self, uow: UnitOfWork, cmd: RecordResultAggregationLinkCommand
    ) -> CalculationResultAggregationLink:
        with record_recorder_duration("record_result_aggregation_link"):
            parent = uow.calculation_result_sets.get(cmd.parent_result_set_id)
            if parent is None:
                raise NotFoundError(
                    f"Parent CalculationResultSet {cmd.parent_result_set_id} not found"
                )
            child = uow.calculation_result_sets.get(cmd.child_result_set_id)
            if child is None:
                raise NotFoundError(
                    f"Child CalculationResultSet {cmd.child_result_set_id} not found"
                )
            link = CalculationResultAggregationLink(
                calculation_result_aggregation_link_id=(
                    cmd.calculation_result_aggregation_link_id or new_uuid7()
                ),
                parent_result_set_id=cmd.parent_result_set_id,
                child_result_set_id=cmd.child_result_set_id,
                aggregation_type=cmd.aggregation_type.value,
                parent_period_id=cmd.parent_period_id,
                child_period_id=cmd.child_period_id,
                created_at=utcnow(),
                metadata=dict(cmd.metadata),
            )
            uow.result_aggregation_links.add(link)
            if cmd.aggregation_type is AggregationType.DAILY_TO_MONTHLY:
                self.record_observable_event(
                    uow,
                    event_type="DAILY_DATA_AGGREGATED_TO_MONTHLY",
                    aggregate_type="calculation_result_set",
                    aggregate_id=cmd.parent_result_set_id,
                    payload={
                        "event_type": "DAILY_DATA_AGGREGATED_TO_MONTHLY",
                        "parent_result_set_id": str(cmd.parent_result_set_id),
                        "child_result_set_id": str(cmd.child_result_set_id),
                        "aggregation_type": cmd.aggregation_type.value,
                    },
                    calculation_result_set_id=cmd.parent_result_set_id,
                    reporting_period_id=cmd.parent_period_id,
                )
            elif cmd.aggregation_type is AggregationType.MONTHLY_TO_ANNUAL:
                self.record_observable_event(
                    uow,
                    event_type="MONTHLY_DATA_AGGREGATED_TO_ANNUAL",
                    aggregate_type="calculation_result_set",
                    aggregate_id=cmd.parent_result_set_id,
                    payload={
                        "event_type": "MONTHLY_DATA_AGGREGATED_TO_ANNUAL",
                        "parent_result_set_id": str(cmd.parent_result_set_id),
                        "child_result_set_id": str(cmd.child_result_set_id),
                        "aggregation_type": cmd.aggregation_type.value,
                    },
                    calculation_result_set_id=cmd.parent_result_set_id,
                    reporting_period_id=cmd.parent_period_id,
                )
            PROVENANCE_RECORDS.labels(
                kind="result_aggregation_link", outcome="created"
            ).inc()
            return link

    # --------------- hash ---------------

    def record_hash(self, uow: UnitOfWork, cmd: RecordHashCommand) -> HashRecord:
        with record_recorder_duration("record_hash"):
            self._require_pipeline_run(uow, cmd.pipeline_run_id)
            existing = uow.hash_records.find_by_subject(
                cmd.subject_kind.value, cmd.subject_id, cmd.hash_algorithm.value
            )
            if existing is not None:
                if existing.hash_value != cmd.hash_value:
                    raise IdempotencyConflictError(
                        "Hash already exists for subject with a different value",
                        details={
                            "subject_kind": cmd.subject_kind.value,
                            "subject_id": str(cmd.subject_id),
                            "existing": existing.hash_value,
                            "submitted": cmd.hash_value,
                        },
                    )
                return existing

            return self._record_hash_internal(
                uow,
                pipeline_run_id=cmd.pipeline_run_id,
                subject_kind=cmd.subject_kind,
                subject_id=cmd.subject_id,
                prov_entity_id=cmd.prov_entity_id,
                bundle_id=cmd.bundle_id,
                hash_value=cmd.hash_value,
                hash_algorithm=cmd.hash_algorithm,
                computed_at=cmd.computed_at,
                computed_by_version=cmd.computed_by_version,
                metadata=cmd.metadata,
            )

    # --------------- blockchain_anchor ---------------

    def record_blockchain_anchor(
        self, uow: UnitOfWork, cmd: RecordBlockchainAnchorCommand
    ) -> BlockchainAnchor:
        with record_recorder_duration("record_blockchain_anchor"):
            self._require_pipeline_run(uow, cmd.pipeline_run_id)
            hash_record = uow.hash_records.get(cmd.hash_record_id)
            if hash_record is None:
                raise InvariantViolationError(
                    "blockchain_anchor requires an existing hash_record",
                    details={"hash_record_id": str(cmd.hash_record_id)},
                )

            request_id = (cmd.metadata or {}).get("request_id")
            if cmd.evidence_package_external_id:
                existing = uow.blockchain_anchors.find_by_evidence_package_external_id(
                    cmd.evidence_package_external_id,
                    pipeline_run_id=cmd.pipeline_run_id,
                )
                if existing is not None:
                    existing_request = (existing.metadata or {}).get("request_id")
                    same_request = request_id and existing_request == request_id
                    same_pending = (
                        existing.anchor_status
                        in (BlockchainAnchorStatus.PENDING, BlockchainAnchorStatus.SUBMITTED)
                        and cmd.anchor_status
                        in (BlockchainAnchorStatus.PENDING, BlockchainAnchorStatus.SUBMITTED)
                    )
                    if same_request or same_pending:
                        PROVENANCE_RECORDS.labels(
                            kind="blockchain_anchor", outcome="idempotent"
                        ).inc()
                        return existing

            submitted_at = cmd.submitted_at
            if submitted_at is None and cmd.anchor_status is BlockchainAnchorStatus.PENDING:
                submitted_at = utcnow()

            meta = dict(cmd.metadata)
            anchor = BlockchainAnchor(
                blockchain_anchor_id=new_uuid7(),
                pipeline_run_id=cmd.pipeline_run_id,
                hash_record_id=cmd.hash_record_id,
                blockchain_network=cmd.blockchain_network,
                chain_id=cmd.chain_id,
                transaction_hash=cmd.transaction_hash,
                block_number=cmd.block_number,
                anchor_status=cmd.anchor_status,
                merkle_root=cmd.merkle_root,
                confirmations=cmd.confirmations,
                anchored_at=cmd.anchored_at,
                verification_uri=cmd.verification_uri,
                anchor_provider=cmd.anchor_provider,
                anchor_mode=cmd.anchor_mode,
                evidence_package_external_id=cmd.evidence_package_external_id,
                package_hash=cmd.package_hash,
                metadata_hash=cmd.metadata_hash,
                submitted_at=submitted_at,
                confirmed_at=cmd.confirmed_at,
                failed_reason=cmd.failed_reason,
                metadata=meta,
            )
            uow.blockchain_anchors.add(anchor)

            self._enqueue_event(
                uow,
                aggregate_kind="blockchain_anchor",
                aggregate_id=anchor.blockchain_anchor_id,
                event_type=f"blockchain_anchor.{cmd.anchor_status.value}",
                pipeline_run_id=cmd.pipeline_run_id,
                payload={
                    "blockchain_anchor_id": str(anchor.blockchain_anchor_id),
                    "hash_record_id": str(cmd.hash_record_id),
                    "blockchain_network": cmd.blockchain_network,
                    "transaction_hash": cmd.transaction_hash,
                    "evidence_package_id": cmd.evidence_package_external_id,
                    "package_hash": cmd.package_hash,
                    "merkle_root": cmd.merkle_root,
                    "network_code": cmd.blockchain_network,
                    "request_id": request_id,
                    "cycle_id": meta.get("cycle_id"),
                    "publication_id": meta.get("publication_id"),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="blockchain_anchor", outcome=cmd.anchor_status.value
            ).inc()
            return anchor

    def confirm_blockchain_anchor(
        self, uow: UnitOfWork, cmd: ConfirmBlockchainAnchorCommand
    ) -> BlockchainAnchor:
        with record_recorder_duration("confirm_blockchain_anchor"):
            anchor = self._resolve_blockchain_anchor(
                uow,
                blockchain_anchor_id=cmd.blockchain_anchor_id,
                evidence_package_external_id=cmd.evidence_package_external_id,
                pipeline_run_id=cmd.pipeline_run_id,
            )
            if (
                anchor.anchor_status is BlockchainAnchorStatus.CONFIRMED
                and cmd.transaction_hash
                and anchor.transaction_hash == cmd.transaction_hash
            ):
                PROVENANCE_RECORDS.labels(
                    kind="blockchain_anchor", outcome="idempotent_confirm"
                ).inc()
                return anchor

            confirmed_at = cmd.confirmed_at or utcnow()
            merged_meta = dict(anchor.metadata or {})
            merged_meta.update(cmd.metadata or {})

            uow.blockchain_anchors.update_status(
                anchor.blockchain_anchor_id,
                anchor_status=cmd.anchor_status.value,
                transaction_hash=cmd.transaction_hash,
                block_number=cmd.block_number,
                confirmations=cmd.confirmations,
                anchored_at=cmd.anchored_at or confirmed_at,
                chain_id=cmd.chain_id,
                verification_uri=cmd.verification_uri,
                confirmed_at=confirmed_at,
                failed_reason=cmd.failed_reason,
                metadata=merged_meta,
            )
            refreshed = uow.blockchain_anchors.get(anchor.blockchain_anchor_id)
            if refreshed is None:
                raise NotFoundError(
                    f"BlockchainAnchor {anchor.blockchain_anchor_id} not found after update"
                )

            self._enqueue_event(
                uow,
                aggregate_kind="blockchain_anchor",
                aggregate_id=refreshed.blockchain_anchor_id,
                event_type=f"blockchain_anchor.{cmd.anchor_status.value}",
                pipeline_run_id=refreshed.pipeline_run_id,
                payload={
                    "blockchain_anchor_id": str(refreshed.blockchain_anchor_id),
                    "hash_record_id": str(refreshed.hash_record_id),
                    "blockchain_network": refreshed.blockchain_network,
                    "transaction_hash": refreshed.transaction_hash,
                    "evidence_package_id": refreshed.evidence_package_external_id,
                    "package_hash": refreshed.package_hash,
                    "merkle_root": refreshed.merkle_root,
                    "network_code": refreshed.blockchain_network,
                    "chain_id": refreshed.chain_id,
                    "block_number": refreshed.block_number,
                    "cycle_id": merged_meta.get("cycle_id"),
                    "publication_id": merged_meta.get("publication_id"),
                    "contract_address": merged_meta.get("contract_address"),
                    "receipt_status": merged_meta.get("receipt_status"),
                    "event_identifier": merged_meta.get("event_identifier"),
                    "confirmed_at": confirmed_at.isoformat(),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="blockchain_anchor", outcome=cmd.anchor_status.value
            ).inc()
            return refreshed

    def record_integrity_verification(
        self, uow: UnitOfWork, cmd: RecordIntegrityVerificationCommand
    ) -> AuditEvent:
        with record_recorder_duration("record_integrity_verification"):
            self._require_pipeline_run(uow, cmd.pipeline_run_id)
            anchor = uow.blockchain_anchors.get(cmd.blockchain_anchor_id)
            if anchor is None:
                raise NotFoundError(
                    f"BlockchainAnchor {cmd.blockchain_anchor_id} not found"
                )

            result_norm = (cmd.result or "").strip().lower()
            if result_norm not in ("match", "divergence"):
                raise InvariantViolationError(
                    "integrity verification result must be 'match' or 'divergence'",
                    details={"result": cmd.result},
                )

            existing_events = uow.audit_events.list_for_subject(
                "blockchain_anchor", cmd.blockchain_anchor_id
            )
            for ev in existing_events:
                if (ev.payload or {}).get("verification_id") == cmd.verification_id:
                    PROVENANCE_RECORDS.labels(
                        kind="integrity_verification", outcome="idempotent"
                    ).inc()
                    return ev

            verified_at = cmd.verified_at or utcnow()
            payload = {
                "verification_id": cmd.verification_id,
                "result": result_norm,
                "local_values": dict(cmd.local_values or {}),
                "recovered_values": dict(cmd.recovered_values or {}),
                "verified_at": verified_at.isoformat(),
                "evidence_package_id": anchor.evidence_package_external_id,
                "pipeline_run_id": str(cmd.pipeline_run_id),
                **{
                    k: v
                    for k, v in (cmd.metadata or {}).items()
                    if k
                    in (
                        "cycle_id",
                        "publication_id",
                        "package_hash",
                        "merkle_root",
                        "agent",
                        "service",
                    )
                },
            }
            event = AuditEvent(
                audit_event_id=new_uuid7(),
                event_type=f"integrity_verification.{result_norm}",
                actor_agent_id=None,
                subject_kind="blockchain_anchor",
                subject_id=cmd.blockchain_anchor_id,
                payload=payload,
                recorded_at=verified_at,
            )
            uow.audit_events.add(event)
            self._enqueue_event(
                uow,
                aggregate_kind="integrity_verification",
                aggregate_id=event.audit_event_id,
                event_type=f"integrity_verification.{result_norm}",
                pipeline_run_id=cmd.pipeline_run_id,
                payload={
                    "audit_event_id": str(event.audit_event_id),
                    "blockchain_anchor_id": str(cmd.blockchain_anchor_id),
                    "verification_id": cmd.verification_id,
                    "result": result_norm,
                    "evidence_package_id": anchor.evidence_package_external_id,
                    "cycle_id": payload.get("cycle_id"),
                    "verified_at": verified_at.isoformat(),
                },
            )
            PROVENANCE_RECORDS.labels(
                kind="integrity_verification", outcome=result_norm
            ).inc()
            return event

    def _resolve_blockchain_anchor(
        self,
        uow: UnitOfWork,
        *,
        blockchain_anchor_id: UUID | None,
        evidence_package_external_id: str | None,
        pipeline_run_id: UUID | None,
    ) -> BlockchainAnchor:
        if blockchain_anchor_id is not None:
            anchor = uow.blockchain_anchors.get(blockchain_anchor_id)
            if anchor is None:
                raise NotFoundError(f"BlockchainAnchor {blockchain_anchor_id} not found")
            return anchor
        if evidence_package_external_id:
            anchor = uow.blockchain_anchors.find_by_evidence_package_external_id(
                evidence_package_external_id,
                pipeline_run_id=pipeline_run_id,
            )
            if anchor is None:
                raise NotFoundError(
                    "BlockchainAnchor not found for evidence_package_external_id",
                )
            return anchor
        raise InvariantViolationError(
            "confirm_blockchain_anchor requires blockchain_anchor_id or evidence_package_external_id"
        )

    # --------------- revision ---------------

    def record_revision(self, uow: UnitOfWork, cmd: RecordRevisionCommand) -> ProvRevision:
        previous = uow.prov_entities.get(cmd.previous_entity_id)
        if previous is None:
            raise NotFoundError(f"ProvEntity {cmd.previous_entity_id} not found")
        new = uow.prov_entities.get(cmd.new_entity_id)
        if new is None:
            raise NotFoundError(f"ProvEntity {cmd.new_entity_id} not found")
        if previous.entity_id == new.entity_id:
            raise InvariantViolationError("revision requires distinct previous and new entities")

        rev = self._add_prov_revision(
            uow,
            previous_entity_id=cmd.previous_entity_id,
            new_entity_id=cmd.new_entity_id,
            revised_at=cmd.revised_at or utcnow(),
            revision_reason=cmd.revision_reason,
            metadata=dict(cmd.metadata),
            invalidate_previous=cmd.invalidate_previous,
        )
        PROVENANCE_RECORDS.labels(kind="prov_revision", outcome="created").inc()
        return rev

    # =====================================================================
    # Internal helpers
    # =====================================================================

    def _require_pipeline_run(self, uow: UnitOfWork, pipeline_run_id: UUID) -> PipelineRun:
        run = uow.pipeline_runs.get(pipeline_run_id)
        if run is None:
            raise NotFoundError(f"PipelineRun {pipeline_run_id} not found")
        return run

    def _ensure_bundle(
        self, uow: UnitOfWork, pipeline_run_id: UUID, bundle_type: ProvBundleType
    ) -> ProvBundle:
        for existing in uow.prov_bundles.list_by_pipeline_run(pipeline_run_id):
            if (
                existing.bundle_type is bundle_type
                and existing.status is ProvBundleStatus.OPEN
            ):
                return existing
        bundle = ProvBundle(
            bundle_id=new_uuid7(),
            pipeline_run_id=pipeline_run_id,
            bundle_type=bundle_type,
            status=ProvBundleStatus.OPEN,
            created_at=utcnow(),
            name=f"{bundle_type.value}-bundle",
        )
        uow.prov_bundles.add(bundle)
        uow.flush()
        return bundle

    def _ensure_software_agent(
        self, uow: UnitOfWork, *, external_reference: str, name: str
    ) -> ProvAgent:
        existing = uow.prov_agents.get_by_external_reference(external_reference)
        if existing is not None:
            return existing
        agent = ProvAgent(
            agent_id=new_uuid7(),
            agent_type=ProvAgentType.SOFTWARE,
            name=name,
            external_reference=external_reference,
            created_at=utcnow(),
        )
        uow.prov_agents.add(agent)
        return agent

    def _add_prov_revision(
        self,
        uow: UnitOfWork,
        *,
        previous_entity_id: UUID,
        new_entity_id: UUID,
        revised_at: datetime,
        revision_reason: str | None,
        metadata: dict[str, Any],
        invalidate_previous: bool,
    ) -> ProvRevision:
        revision = ProvRevision(
            revision_id=new_uuid7(),
            previous_entity_id=previous_entity_id,
            new_entity_id=new_entity_id,
            revision_reason=revision_reason,
            revised_at=revised_at,
            metadata=metadata,
        )
        uow.prov_relations.add_revision(revision)
        if invalidate_previous:
            uow.prov_entities.invalidate(previous_entity_id)
        return revision

    def _derivation_source_entity_for_normalization(
        self, uow: UnitOfWork, execution: WrapperExecution
    ) -> UUID:
        if execution.input_source_artifact_revision_id is not None:
            rev = uow.source_artifact_revisions.get(
                execution.input_source_artifact_revision_id
            )
            if rev is None:
                raise NotFoundError(
                    f"SourceArtifactRevision {execution.input_source_artifact_revision_id} not found"
                )
            if rev.prov_entity_id is not None:
                return rev.prov_entity_id
        return self._entity_id_for_source_artifact(uow, execution.input_artifact_id)

    def _entity_id_for_source_artifact(self, uow: UnitOfWork, artifact_id: UUID) -> UUID:
        artifact = uow.source_artifacts.get(artifact_id)
        if artifact is None:
            raise NotFoundError(f"SourceArtifact {artifact_id} not found")
        return artifact.prov_entity_id

    def _record_hash_internal(
        self,
        uow: UnitOfWork,
        *,
        pipeline_run_id: UUID,
        subject_kind: HashSubjectKind,
        subject_id: UUID,
        prov_entity_id: UUID | None,
        bundle_id: UUID | None,
        hash_value: str,
        hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256,
        computed_at: datetime | None = None,
        computed_by_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HashRecord:
        existing = uow.hash_records.find_by_subject(
            subject_kind.value, subject_id, hash_algorithm.value
        )
        if existing is not None:
            return existing
        record = HashRecord(
            hash_record_id=new_uuid7(),
            pipeline_run_id=pipeline_run_id,
            prov_entity_id=prov_entity_id,
            bundle_id=bundle_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            hash_algorithm=hash_algorithm,
            hash_value=hash_value,
            computed_at=computed_at or utcnow(),
            computed_by_version=computed_by_version or self.SOFTWARE_VERSION,
            hash_scope=hash_scope_for_subject(subject_kind).value,
            canonicalization_method=default_canonicalization_method(),
            canonical_payload_hash=hash_value,
            created_by_service=self.SOFTWARE_VERSION,
            record_created_at=computed_at or utcnow(),
            metadata=dict(metadata or {}),
        )
        uow.hash_records.add(record)
        uow.flush()
        self.record_observable_event(
            uow,
            event_type="LOCAL_HASH_CREATED",
            aggregate_type=subject_kind.value,
            aggregate_id=subject_id,
            payload={
                "event_type": "LOCAL_HASH_CREATED",
                "hash_record_id": str(record.hash_record_id),
                "subject_kind": subject_kind.value,
                "subject_id": str(subject_id),
                "hash_value": hash_value,
                "hash_scope": record.hash_scope,
                "canonicalization_method": record.canonicalization_method,
                "pipeline_run_id": str(pipeline_run_id),
            },
            pipeline_run_id=pipeline_run_id,
            source_table="audit_hash_record",
            source_record_id=record.hash_record_id,
        )
        return record

    def _raise_if_idempotency_payload_mismatch(
        self,
        *,
        operation: str,
        idempotency_key: str,
        existing_values: dict[str, Any],
        incoming_values: dict[str, Any],
    ) -> None:
        mismatches: dict[str, dict[str, str]] = {}
        for field_name in existing_values:
            existing = self._normalize_idempotent_value(existing_values[field_name])
            incoming = self._normalize_idempotent_value(incoming_values[field_name])
            if existing != incoming:
                mismatches[field_name] = {"existing": existing, "incoming": incoming}
        if mismatches:
            raise IdempotencyConflictError(
                f"Idempotency key {idempotency_key!r} was reused with a different payload",
                details={
                    "operation": operation,
                    "idempotency_key": idempotency_key,
                    "mismatches": mismatches,
                },
            )

    @staticmethod
    def _normalize_idempotent_value(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, Decimal):
            return format(value, "f")
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def record_observable_event(
        self,
        uow: UnitOfWork,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        payload: dict[str, Any],
        pipeline_run_id: UUID | None = None,
        calculation_execution_id: UUID | None = None,
        calculation_result_set_id: UUID | None = None,
        reporting_period_id: UUID | None = None,
        source_table: str | None = None,
        source_record_id: UUID | None = None,
    ) -> None:
        """Register a blockchain-observable event in the outbox (same transaction)."""

        enriched = dict(payload)
        enriched.setdefault("event_type", event_type)
        enriched.setdefault("aggregate_type", aggregate_type)
        enriched.setdefault("aggregate_id", str(aggregate_id))
        self._enqueue_event(
            uow,
            aggregate_kind=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=enriched,
            pipeline_run_id=pipeline_run_id,
            calculation_execution_id=calculation_execution_id,
            calculation_result_set_id=calculation_result_set_id,
            reporting_period_id=reporting_period_id,
            source_table=source_table,
            source_record_id=source_record_id,
        )

    def _enqueue_event(
        self,
        uow: UnitOfWork,
        *,
        aggregate_kind: str,
        aggregate_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        pipeline_run_id: UUID | None = None,
        calculation_execution_id: UUID | None = None,
        calculation_result_set_id: UUID | None = None,
        reporting_period_id: UUID | None = None,
        source_table: str | None = None,
        source_record_id: UUID | None = None,
    ) -> None:
        uow.outbox.add(
            OutboxEvent(
                outbox_event_id=new_uuid7(),
                aggregate_kind=aggregate_kind,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                created_at=utcnow(),
                status=OutboxStatus.PENDING,
                pipeline_run_id=pipeline_run_id,
                calculation_execution_id=calculation_execution_id,
                calculation_result_set_id=calculation_result_set_id,
                reporting_period_id=reporting_period_id,
                source_table=source_table,
                source_record_id=source_record_id,
            )
        )
