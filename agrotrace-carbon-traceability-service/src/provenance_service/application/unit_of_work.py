"""Unit of Work protocol.

A UoW is a context-manager bundling all repositories of a single transactional
boundary. The :class:`ProvenanceRecorder` and the use cases interact with the
ledger only through this seam.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from provenance_service.domain.audit.repositories import (
    AuditEventRepository,
    BlockchainAnchorRepository,
    HashRecordRepository,
    OutboxRepository,
)
from provenance_service.domain.calculation.repositories import (
    CalculationExecutionRepository,
    CalculationMethodRepository,
    CalculationMethodVersionRepository,
    CalculationParameterSetRepository,
    CalculationResultSetRepository,
    CalculationReviewRepository,
    ResultPublicationExecutionRepository,
)
from provenance_service.domain.pipeline.repositories import (
    NormalizedBatchRepository,
    PipelineRunRepository,
    SourceArtifactRepository,
    SourceArtifactRevisionRepository,
    WrapperDefinitionRepository,
    WrapperExecutionRepository,
)
from provenance_service.domain.prov_core.repositories import (
    ProvActivityRepository,
    ProvAgentRepository,
    ProvAttributeRepository,
    ProvBundleRepository,
    ProvEntityRepository,
    ProvRelationRepository,
)
from provenance_service.domain.semantic.repositories import (
    CanonicalSnapshotRepository,
    OntologyResourceLinkRepository,
    SemanticIntegrationExecutionRepository,
)


class UnitOfWork(Protocol):
    pipeline_runs: PipelineRunRepository
    source_artifacts: SourceArtifactRepository
    source_artifact_revisions: SourceArtifactRevisionRepository
    wrapper_definitions: WrapperDefinitionRepository
    wrapper_executions: WrapperExecutionRepository
    normalized_batches: NormalizedBatchRepository

    prov_bundles: ProvBundleRepository
    prov_entities: ProvEntityRepository
    prov_activities: ProvActivityRepository
    prov_agents: ProvAgentRepository
    prov_relations: ProvRelationRepository
    prov_attributes: ProvAttributeRepository

    semantic_integration_executions: SemanticIntegrationExecutionRepository
    canonical_snapshots: CanonicalSnapshotRepository
    ontology_resource_links: OntologyResourceLinkRepository

    calculation_methods: CalculationMethodRepository
    calculation_method_versions: CalculationMethodVersionRepository
    calculation_parameter_sets: CalculationParameterSetRepository
    calculation_executions: CalculationExecutionRepository
    calculation_result_sets: CalculationResultSetRepository
    calculation_reviews: CalculationReviewRepository
    result_publication_executions: ResultPublicationExecutionRepository

    hash_records: HashRecordRepository
    blockchain_anchors: BlockchainAnchorRepository
    outbox: OutboxRepository
    audit_events: AuditEventRepository

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def flush(self) -> None: ...
