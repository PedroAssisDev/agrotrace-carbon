"""Pipeline-context HTTP routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from provenance_service.application.services import (
    RecordNormalizedBatchCommand,
    RecordSourceArtifactCommand,
    RecordSourceArtifactRevisionCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    StartPipelineRunCommand,
)
from provenance_service.application.use_cases import (
    GetBundleGraph,
    GetPipelineRun,
    GetPipelineRunTrace,
    ListPipelineRuns,
    ListPipelineRunsQuery,
    PipelineRunTraceData,
    RegisterNormalizedBatch,
    RegisterSourceArtifact,
    RegisterSourceArtifactRevision,
    RegisterWrapperDefinition,
    RegisterWrapperExecution,
    StartPipelineRun,
)
from provenance_service.application.use_cases.get_bundle_graph import BundleGraph
from provenance_service.domain.shared.errors import NotFoundError
from provenance_service.interfaces.api.deps import (
    SessionFactoryDep,
    provide_get_bundle_graph,
    provide_get_pipeline_run,
    provide_get_pipeline_run_trace,
    provide_list_pipeline_runs,
    provide_register_normalized_batch,
    provide_register_source_artifact,
    provide_register_source_artifact_revision,
    provide_register_wrapper_definition,
    provide_register_wrapper_execution,
    provide_start_pipeline_run,
)
from provenance_service.interfaces.api.schemas.calculation import (
    CalculationExecutionResponse,
    CalculationMethodResponse,
    CalculationMethodVersionResponse,
    CalculationParameterSetResponse,
    CalculationResultItemResponse,
    CalculationResultSetResponse,
    CalculationReviewResponse,
    ResultPublicationExecutionResponse,
)
from provenance_service.interfaces.api.schemas.pipeline import (
    CanonicalSnapshotItemTrace,
    CanonicalSnapshotTraceResponse,
    NormalizedBatchResponse,
    PipelineRunBundleGraphRow,
    PipelineRunListResponse,
    PipelineRunGraphsResponse,
    PipelineRunResponse,
    PipelineRunTraceResponse,
    RegisterNormalizedBatchRequest,
    RegisterSourceArtifactRequest,
    RegisterSourceArtifactRevisionRequest,
    RegisterWrapperDefinitionRequest,
    RegisterWrapperExecutionRequest,
    SourceArtifactResponse,
    SourceArtifactRevisionResponse,
    StartPipelineRunRequest,
    WrapperDefinitionResponse,
    WrapperExecutionResponse,
)
from provenance_service.interfaces.api.schemas.audit import HashRecordResponse
from provenance_service.interfaces.api.schemas.prov import (
    BundleGraphResponse,
    GraphEdge,
    GraphNode,
    GraphRevisionEdge,
    ProvBundleResponse,
)
from provenance_service.interfaces.api.schemas.semantic import (
    CanonicalSnapshotResponse,
    OntologyResourceLinkResponse,
    SemanticIntegrationExecutionResponse,
)
router = APIRouter(tags=["pipeline"])


def _bundle_graph_to_response(graph: BundleGraph) -> BundleGraphResponse:
    return BundleGraphResponse(
        bundle_id=graph.bundle_id,
        pipeline_run_id=graph.pipeline_run_id,
        bundle_type=graph.bundle_type,
        status=graph.status,
        entities=[GraphNode.model_validate(n) for n in graph.entities],
        activities=[GraphNode.model_validate(n) for n in graph.activities],
        agents=[GraphNode.model_validate(n) for n in graph.agents],
        used=[GraphEdge.model_validate(e) for e in graph.used],
        generated=[GraphEdge.model_validate(e) for e in graph.generated],
        associated_with=[GraphEdge.model_validate(e) for e in graph.associated_with],
        derived_from=[GraphEdge.model_validate(e) for e in graph.derived_from],
        revisions=[GraphRevisionEdge.model_validate(e) for e in graph.revisions],
    )


def _trace_to_http(data: PipelineRunTraceData) -> PipelineRunTraceResponse:
    canonical_rows = []
    for snap in data.canonical_snapshots:
        raw_items = data.canonical_snapshot_items.get(snap.canonical_snapshot_id, [])
        canonical_rows.append(
            CanonicalSnapshotTraceResponse(
                snapshot=CanonicalSnapshotResponse.model_validate(snap),
                items=[
                    CanonicalSnapshotItemTrace(
                        canonical_snapshot_item_id=i.canonical_snapshot_item_id,
                        canonical_snapshot_id=i.canonical_snapshot_id,
                        item_key=i.item_key,
                        item_hash=i.item_hash,
                        payload=dict(i.payload) if i.payload is not None else {},
                    )
                    for i in raw_items
                ],
            )
        )

    result_sets: list[CalculationResultSetResponse] = []
    for rs in data.calculation_result_sets:
        items = data.calculation_result_items.get(rs.calculation_result_set_id, [])
        result_sets.append(
            CalculationResultSetResponse(
                calculation_result_set_id=rs.calculation_result_set_id,
                pipeline_run_id=rs.pipeline_run_id,
                prov_entity_id=rs.prov_entity_id,
                calculation_execution_id=rs.calculation_execution_id,
                result_set_status=rs.result_set_status,
                generated_at=rs.generated_at,
                summary_hash=rs.summary_hash,
                superseded_by_id=rs.superseded_by_id,
                metadata=dict(rs.metadata),
                items=[CalculationResultItemResponse.model_validate(i) for i in items],
            )
        )

    return PipelineRunTraceResponse(
        pipeline_run=PipelineRunResponse.model_validate(data.run),
        source_artifacts=[SourceArtifactResponse.model_validate(a) for a in data.source_artifacts],
        source_artifact_revisions=[
            SourceArtifactRevisionResponse.model_validate(r) for r in data.source_artifact_revisions
        ],
        wrapper_executions=[
            WrapperExecutionResponse.model_validate(e) for e in data.wrapper_executions
        ],
        normalized_batches=[
            NormalizedBatchResponse.model_validate(b) for b in data.normalized_batches
        ],
        semantic_integration_executions=[
            SemanticIntegrationExecutionResponse.model_validate(s)
            for s in data.semantic_integrations
        ],
        canonical_snapshots=canonical_rows,
        ontology_resource_links=[
            OntologyResourceLinkResponse.model_validate(o) for o in data.ontology_resource_links
        ],
        calculation_executions=[
            CalculationExecutionResponse.model_validate(e) for e in data.calculation_executions
        ],
        calculation_parameter_sets=[
            CalculationParameterSetResponse.model_validate(p) for p in data.calculation_parameter_sets
        ],
        calculation_method_versions=[
            CalculationMethodVersionResponse.model_validate(v)
            for v in data.calculation_method_versions
        ],
        calculation_methods=[
            CalculationMethodResponse.model_validate(m) for m in data.calculation_methods
        ],
        calculation_result_sets=result_sets,
        calculation_reviews=[
            CalculationReviewResponse.model_validate(r) for r in data.calculation_reviews
        ],
        result_publication_executions=[
            ResultPublicationExecutionResponse.model_validate(p)
            for p in data.result_publications
        ],
        hash_records=[HashRecordResponse.model_validate(h) for h in data.hash_records],
        prov_bundles=[ProvBundleResponse.model_validate(b) for b in data.prov_bundles],
    )


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_pipeline_run(
    payload: StartPipelineRunRequest,
    use_case: Annotated[StartPipelineRun, Depends(provide_start_pipeline_run)],
) -> PipelineRunResponse:
    cmd = StartPipelineRunCommand(**payload.model_dump())
    run = use_case.execute(cmd)
    return PipelineRunResponse.model_validate(run)


@router.get("/pipeline-runs/{pipeline_run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(
    pipeline_run_id: UUID,
    use_case: Annotated[GetPipelineRun, Depends(provide_get_pipeline_run)],
) -> PipelineRunResponse:
    run = use_case.execute(pipeline_run_id)
    return PipelineRunResponse.model_validate(run)


@router.get("/pipeline-runs", response_model=PipelineRunListResponse)
def list_pipeline_runs(
    use_case: Annotated[ListPipelineRuns, Depends(provide_list_pipeline_runs)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    run_status: str | None = Query(default=None),
    farm_reference: str | None = Query(default=None),
    started_from: datetime | None = Query(default=None),
    started_to: datetime | None = Query(default=None),
) -> PipelineRunListResponse:
    result = use_case.execute(
        ListPipelineRunsQuery(
            limit=limit,
            offset=offset,
            run_status=run_status,
            farm_reference=farm_reference,
            started_from=started_from,
            started_to=started_to,
        )
    )
    return PipelineRunListResponse(
        items=[PipelineRunResponse.model_validate(r) for r in result.items],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.post(
    "/source-artifacts",
    response_model=SourceArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_source_artifact(
    payload: RegisterSourceArtifactRequest,
    use_case: Annotated[
        RegisterSourceArtifact, Depends(provide_register_source_artifact)
    ],
) -> SourceArtifactResponse:
    cmd = RecordSourceArtifactCommand(**payload.model_dump())
    artifact = use_case.execute(cmd)
    return SourceArtifactResponse.model_validate(artifact)


@router.post(
    "/source-artifact-revisions",
    response_model=SourceArtifactRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_source_artifact_revision(
    payload: RegisterSourceArtifactRevisionRequest,
    use_case: Annotated[
        RegisterSourceArtifactRevision,
        Depends(provide_register_source_artifact_revision),
    ],
) -> SourceArtifactRevisionResponse:
    cmd = RecordSourceArtifactRevisionCommand(**payload.model_dump())
    revision = use_case.execute(cmd)
    return SourceArtifactRevisionResponse.model_validate(revision)


@router.get(
    "/source-artifacts/{source_artifact_id}", response_model=SourceArtifactResponse
)
def get_source_artifact(
    source_artifact_id: UUID,
    session_factory: SessionFactoryDep,
) -> SourceArtifactResponse:
    from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    with SqlAlchemyUnitOfWork(session_factory) as uow:
        artifact = uow.source_artifacts.get(source_artifact_id)
        if artifact is None:
            raise NotFoundError(f"SourceArtifact {source_artifact_id} not found")
        return SourceArtifactResponse.model_validate(artifact)


@router.post(
    "/wrapper-definitions",
    response_model=WrapperDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_wrapper_definition(
    payload: RegisterWrapperDefinitionRequest,
    use_case: Annotated[
        RegisterWrapperDefinition, Depends(provide_register_wrapper_definition)
    ],
) -> WrapperDefinitionResponse:
    cmd = RecordWrapperDefinitionCommand(**payload.model_dump())
    definition = use_case.execute(cmd)
    return WrapperDefinitionResponse.model_validate(definition)


@router.post(
    "/wrapper-executions",
    response_model=WrapperExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_wrapper_execution(
    payload: RegisterWrapperExecutionRequest,
    use_case: Annotated[
        RegisterWrapperExecution, Depends(provide_register_wrapper_execution)
    ],
) -> WrapperExecutionResponse:
    cmd = RecordWrapperExecutionCommand(**payload.model_dump())
    execution = use_case.execute(cmd)
    return WrapperExecutionResponse.model_validate(execution)


@router.post(
    "/normalized-batches",
    response_model=NormalizedBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_normalized_batch(
    payload: RegisterNormalizedBatchRequest,
    use_case: Annotated[
        RegisterNormalizedBatch, Depends(provide_register_normalized_batch)
    ],
) -> NormalizedBatchResponse:
    cmd = RecordNormalizedBatchCommand(**payload.model_dump())
    batch = use_case.execute(cmd)
    return NormalizedBatchResponse.model_validate(batch)


@router.get(
    "/pipeline-runs/{pipeline_run_id}/trace",
    response_model=PipelineRunTraceResponse,
)
def get_pipeline_run_trace(
    pipeline_run_id: UUID,
    use_case: Annotated[
        GetPipelineRunTrace, Depends(provide_get_pipeline_run_trace)
    ],
) -> PipelineRunTraceResponse:
    data = use_case.execute(pipeline_run_id)
    return _trace_to_http(data)


@router.get(
    "/pipeline-runs/{pipeline_run_id}/graph",
    response_model=PipelineRunGraphsResponse,
)
def get_pipeline_run_graphs(
    pipeline_run_id: UUID,
    trace_uc: Annotated[
        GetPipelineRunTrace, Depends(provide_get_pipeline_run_trace)
    ],
    graph_uc: Annotated[GetBundleGraph, Depends(provide_get_bundle_graph)],
) -> PipelineRunGraphsResponse:
    trace = trace_uc.execute(pipeline_run_id)
    rows = [
        PipelineRunBundleGraphRow(
            bundle_id=b.bundle_id,
            graph=_bundle_graph_to_response(graph_uc.execute(b.bundle_id)),
        )
        for b in trace.prov_bundles
    ]
    return PipelineRunGraphsResponse(
        pipeline_run_id=pipeline_run_id,
        bundle_graphs=rows,
    )
