"""SQLAlchemy implementation of the Unit of Work."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from provenance_service.infrastructure.db.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyBlockchainAnchorRepository,
    SqlAlchemyCalculationExecutionRepository,
    SqlAlchemyCalculationMethodRepository,
    SqlAlchemyCalculationMethodVersionRepository,
    SqlAlchemyCalculationParameterSetRepository,
    SqlAlchemyCalculationResultAggregationLinkRepository,
    SqlAlchemyCalculationResultSetRepository,
    SqlAlchemyCalculationReviewRepository,
    SqlAlchemyCanonicalSnapshotRepository,
    SqlAlchemyHashRecordRepository,
    SqlAlchemyNormalizedBatchRepository,
    SqlAlchemyOntologyResourceLinkRepository,
    SqlAlchemyOutboxRepository,
    SqlAlchemyPipelineRunRepository,
    SqlAlchemyProvActivityRepository,
    SqlAlchemyProvAgentRepository,
    SqlAlchemyProvAttributeRepository,
    SqlAlchemyProvBundleRepository,
    SqlAlchemyProvEntityRepository,
    SqlAlchemyProvRelationRepository,
    SqlAlchemyReportingPeriodRepository,
    SqlAlchemyResultPublicationExecutionRepository,
    SqlAlchemySemanticIntegrationExecutionRepository,
    SqlAlchemySourceArtifactRepository,
    SqlAlchemySourceArtifactRevisionRepository,
    SqlAlchemyWrapperDefinitionRepository,
    SqlAlchemyWrapperExecutionRepository,
)


class SqlAlchemyUnitOfWork:
    """One UoW per logical write transaction.

    Usage::

        with SqlAlchemyUnitOfWork(session_factory) as uow:
            uow.pipeline_runs.add(...)
            uow.commit()

    Calling ``commit`` is required; if not called, ``__exit__`` rolls back.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed: bool = False

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        return self._session

    def __enter__(self) -> Self:
        self._session = self._session_factory()
        self._committed = False
        self._wire_repositories(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        self._session.flush()
        self._session.commit()
        self._committed = True

    def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        self._session.rollback()

    def flush(self) -> None:
        """Flush pending ORM state to the database (FK ordering on SQLite)."""

        if self._session is None:
            raise RuntimeError("UnitOfWork not entered")
        self._session.flush()

    def _wire_repositories(self, session: Session) -> None:
        self.pipeline_runs = SqlAlchemyPipelineRunRepository(session)
        self.source_artifacts = SqlAlchemySourceArtifactRepository(session)
        self.source_artifact_revisions = SqlAlchemySourceArtifactRevisionRepository(
            session
        )
        self.wrapper_definitions = SqlAlchemyWrapperDefinitionRepository(session)
        self.wrapper_executions = SqlAlchemyWrapperExecutionRepository(session)
        self.normalized_batches = SqlAlchemyNormalizedBatchRepository(session)

        self.prov_bundles = SqlAlchemyProvBundleRepository(session)
        self.prov_entities = SqlAlchemyProvEntityRepository(session)
        self.prov_activities = SqlAlchemyProvActivityRepository(session)
        self.prov_agents = SqlAlchemyProvAgentRepository(session)
        self.prov_relations = SqlAlchemyProvRelationRepository(session)
        self.prov_attributes = SqlAlchemyProvAttributeRepository(session)

        self.semantic_integration_executions = (
            SqlAlchemySemanticIntegrationExecutionRepository(session)
        )
        self.canonical_snapshots = SqlAlchemyCanonicalSnapshotRepository(session)
        self.ontology_resource_links = SqlAlchemyOntologyResourceLinkRepository(session)

        self.calculation_methods = SqlAlchemyCalculationMethodRepository(session)
        self.calculation_method_versions = SqlAlchemyCalculationMethodVersionRepository(session)
        self.calculation_parameter_sets = SqlAlchemyCalculationParameterSetRepository(session)
        self.calculation_executions = SqlAlchemyCalculationExecutionRepository(session)
        self.calculation_result_sets = SqlAlchemyCalculationResultSetRepository(session)
        self.calculation_reviews = SqlAlchemyCalculationReviewRepository(session)
        self.result_publication_executions = (
            SqlAlchemyResultPublicationExecutionRepository(session)
        )
        self.result_aggregation_links = SqlAlchemyCalculationResultAggregationLinkRepository(
            session
        )

        self.reporting_periods = SqlAlchemyReportingPeriodRepository(session)

        self.hash_records = SqlAlchemyHashRecordRepository(session)
        self.blockchain_anchors = SqlAlchemyBlockchainAnchorRepository(session)
        self.outbox = SqlAlchemyOutboxRepository(session)
        self.audit_events = SqlAlchemyAuditEventRepository(session)
