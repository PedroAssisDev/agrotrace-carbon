"""FastAPI dependency providers (DI container, explicit and synchronous).

The application is built top-down here: settings → engine → sessionmaker →
UnitOfWork factory → ``ProvenanceRecorder`` → use cases. Each dependency is
cached at process scope so that we don't pay for re-imports per request.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Annotated, ContextManager, Iterator

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from provenance_service.application.ports import (
    BlockchainAnchorClient,
    EventPublisher,
    OntologyClient,
    WrapperMetadataClient,
)
from provenance_service.application.services.provenance_recorder import ProvenanceRecorder
from provenance_service.application.unit_of_work import UnitOfWork
from provenance_service.application.use_cases import (
    ComputeAndRecordHash,
    GetBundleGraph,
    GetPipelineRun,
    GetPipelineRunTrace,
    ListOutboxEvents,
    ListPipelineRuns,
    RegisterBlockchainAnchor,
    RegisterCalculationExecution,
    RegisterCalculationMethod,
    RegisterCalculationMethodVersion,
    RegisterCalculationParameterSet,
    RegisterCalculationResultSet,
    RegisterCalculationReview,
    RegisterCanonicalSnapshot,
    RegisterNormalizedBatch,
    RegisterOntologyResourceLink,
    RegisterResultPublication,
    RegisterReportingPeriod,
    RegisterResultAggregationLink,
    RegisterSemanticIntegration,
    RegisterSourceArtifact,
    RegisterSourceArtifactRevision,
    RegisterWrapperDefinition,
    RegisterWrapperExecution,
    StartPipelineRun,
    VerifyIntegrity,
)
from provenance_service.infrastructure.adapters import (
    LoggingEventPublisher,
    StubBlockchainAnchorClient,
    StubOntologyClient,
    StubWrapperMetadataClient,
)
from provenance_service.infrastructure.config import Settings, get_settings
from provenance_service.infrastructure.db.session import get_sessionmaker
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from provenance_service.infrastructure.outbox import OutboxDispatcher

# ============================================================
# Core providers
# ============================================================


def provide_settings() -> Settings:
    return get_settings()


def provide_session_factory() -> sessionmaker[Session]:
    return get_sessionmaker()


SessionFactoryDep = Annotated[sessionmaker[Session], Depends(provide_session_factory)]


def provide_uow_factory(
    session_factory: SessionFactoryDep,
):
    """Return a callable that produces a fresh :class:`UnitOfWork` context manager."""

    @contextmanager
    def _factory() -> Iterator[UnitOfWork]:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            yield uow

    return _factory


def get_uow_factory(
    session_factory: sessionmaker[Session] | None = None,
):
    """Programmatic accessor (non-FastAPI) for the same UoW factory."""
    sf = session_factory or get_sessionmaker()

    @contextmanager
    def _factory() -> Iterator[UnitOfWork]:
        with SqlAlchemyUnitOfWork(sf) as uow:
            yield uow

    return _factory


UoWFactoryDep = Annotated[
    "callable[[], ContextManager[UnitOfWork]]", Depends(provide_uow_factory)
]


# ============================================================
# Outbound ports (stubs by default)
# ============================================================


@lru_cache(maxsize=1)
def _ontology_client() -> OntologyClient:
    return StubOntologyClient()


@lru_cache(maxsize=1)
def _blockchain_client() -> BlockchainAnchorClient:
    return StubBlockchainAnchorClient()


@lru_cache(maxsize=1)
def _wrapper_metadata_client() -> WrapperMetadataClient:
    return StubWrapperMetadataClient()


@lru_cache(maxsize=1)
def _event_publisher() -> EventPublisher:
    return LoggingEventPublisher()


def provide_ontology_client() -> OntologyClient:
    return _ontology_client()


def provide_blockchain_client() -> BlockchainAnchorClient:
    return _blockchain_client()


def provide_wrapper_metadata_client() -> WrapperMetadataClient:
    return _wrapper_metadata_client()


def provide_event_publisher() -> EventPublisher:
    return _event_publisher()


# ============================================================
# Recorder + use cases
# ============================================================


@lru_cache(maxsize=1)
def _recorder() -> ProvenanceRecorder:
    return ProvenanceRecorder()


def provide_recorder() -> ProvenanceRecorder:
    return _recorder()


RecorderDep = Annotated[ProvenanceRecorder, Depends(provide_recorder)]


def provide_start_pipeline_run(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> StartPipelineRun:
    return StartPipelineRun(uow_factory, recorder)


def provide_register_source_artifact(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterSourceArtifact:
    return RegisterSourceArtifact(uow_factory, recorder)


def provide_register_wrapper_definition(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterWrapperDefinition:
    return RegisterWrapperDefinition(uow_factory, recorder)


def provide_register_wrapper_execution(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterWrapperExecution:
    return RegisterWrapperExecution(uow_factory, recorder)


def provide_register_normalized_batch(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterNormalizedBatch:
    return RegisterNormalizedBatch(uow_factory, recorder)


def provide_register_semantic_integration(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterSemanticIntegration:
    return RegisterSemanticIntegration(uow_factory, recorder)


def provide_register_canonical_snapshot(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCanonicalSnapshot:
    return RegisterCanonicalSnapshot(uow_factory, recorder)


def provide_register_ontology_resource_link(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterOntologyResourceLink:
    return RegisterOntologyResourceLink(uow_factory, recorder)


def provide_register_calculation_method(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationMethod:
    return RegisterCalculationMethod(uow_factory, recorder)


def provide_register_calculation_method_version(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationMethodVersion:
    return RegisterCalculationMethodVersion(uow_factory, recorder)


def provide_register_calculation_parameter_set(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationParameterSet:
    return RegisterCalculationParameterSet(uow_factory, recorder)


def provide_register_calculation_execution(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationExecution:
    return RegisterCalculationExecution(uow_factory, recorder)


def provide_register_calculation_result_set(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationResultSet:
    return RegisterCalculationResultSet(uow_factory, recorder)


def provide_register_calculation_review(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterCalculationReview:
    return RegisterCalculationReview(uow_factory, recorder)


def provide_register_result_publication(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterResultPublication:
    return RegisterResultPublication(uow_factory, recorder)


def provide_register_reporting_period(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterReportingPeriod:
    return RegisterReportingPeriod(uow_factory, recorder)


def provide_register_result_aggregation_link(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterResultAggregationLink:
    return RegisterResultAggregationLink(uow_factory, recorder)


def provide_compute_and_record_hash(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> ComputeAndRecordHash:
    return ComputeAndRecordHash(uow_factory, recorder)


def provide_register_blockchain_anchor(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterBlockchainAnchor:
    return RegisterBlockchainAnchor(uow_factory, recorder)


def provide_get_bundle_graph(uow_factory: UoWFactoryDep) -> GetBundleGraph:
    return GetBundleGraph(uow_factory)


def provide_get_pipeline_run(uow_factory: UoWFactoryDep) -> GetPipelineRun:
    return GetPipelineRun(uow_factory)


def provide_list_pipeline_runs(uow_factory: UoWFactoryDep) -> ListPipelineRuns:
    return ListPipelineRuns(uow_factory)


def provide_get_pipeline_run_trace(uow_factory: UoWFactoryDep) -> GetPipelineRunTrace:
    return GetPipelineRunTrace(uow_factory)


def provide_register_source_artifact_revision(
    uow_factory: UoWFactoryDep, recorder: RecorderDep
) -> RegisterSourceArtifactRevision:
    return RegisterSourceArtifactRevision(uow_factory, recorder)


def provide_list_outbox_events(uow_factory: UoWFactoryDep) -> ListOutboxEvents:
    return ListOutboxEvents(uow_factory)


def provide_verify_integrity(uow_factory: UoWFactoryDep) -> VerifyIntegrity:
    return VerifyIntegrity(uow_factory)


# ============================================================
# Outbox dispatcher
# ============================================================


def provide_outbox_dispatcher(
    settings: Annotated[Settings, Depends(provide_settings)],
    uow_factory: UoWFactoryDep,
) -> OutboxDispatcher:
    return OutboxDispatcher(
        uow_factory,
        _event_publisher(),
        batch_size=settings.outbox_batch_size,
    )
