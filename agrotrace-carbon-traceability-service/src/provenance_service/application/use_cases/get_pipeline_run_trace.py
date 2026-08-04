"""Aggregate read model for a pipeline run (demo / support)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.audit.entities import HashRecord
from provenance_service.domain.calculation.entities import (
    CalculationExecution,
    CalculationMethod,
    CalculationMethodVersion,
    CalculationParameterSet,
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
    WrapperExecution,
)
from provenance_service.domain.prov_core.entities import ProvBundle
from provenance_service.domain.semantic.entities import (
    CanonicalSnapshot,
    CanonicalSnapshotItem,
    OntologyResourceLink,
    SemanticIntegrationExecution,
)
from provenance_service.domain.shared.errors import NotFoundError


@dataclass(slots=True)
class PipelineRunTraceData:
    run: PipelineRun
    source_artifacts: list[SourceArtifact]
    source_artifact_revisions: list[SourceArtifactRevision]
    wrapper_executions: list[WrapperExecution]
    normalized_batches: list[NormalizedBatch]
    semantic_integrations: list[SemanticIntegrationExecution]
    canonical_snapshots: list[CanonicalSnapshot]
    canonical_snapshot_items: dict[UUID, list[CanonicalSnapshotItem]]
    ontology_resource_links: list[OntologyResourceLink]
    calculation_executions: list[CalculationExecution]
    calculation_parameter_sets: list[CalculationParameterSet]
    calculation_method_versions: list[CalculationMethodVersion]
    calculation_methods: list[CalculationMethod]
    calculation_result_sets: list[CalculationResultSet]
    calculation_result_items: dict[UUID, list[CalculationResultItem]]
    calculation_reviews: list[CalculationReview]
    result_publications: list[ResultPublicationExecution]
    hash_records: list[HashRecord]
    prov_bundles: list[ProvBundle]


class GetPipelineRunTrace:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, pipeline_run_id: UUID) -> PipelineRunTraceData:
        with self._uow_factory() as uow:
            run = uow.pipeline_runs.get(pipeline_run_id)
            if run is None:
                raise NotFoundError(f"PipelineRun {pipeline_run_id} not found")

            source_artifacts = uow.source_artifacts.list_by_pipeline_run(pipeline_run_id)
            revisions = uow.source_artifact_revisions.list_by_pipeline_run(pipeline_run_id)
            wrapper_executions = uow.wrapper_executions.list_by_pipeline_run(pipeline_run_id)
            normalized_batches = uow.normalized_batches.list_by_pipeline_run(pipeline_run_id)
            semantic_integrations = uow.semantic_integration_executions.list_by_pipeline_run(
                pipeline_run_id
            )
            canonical_snapshots = uow.canonical_snapshots.list_by_pipeline_run(pipeline_run_id)
            snap_items: dict[UUID, list[CanonicalSnapshotItem]] = {}
            for snap in canonical_snapshots:
                snap_items[snap.canonical_snapshot_id] = uow.canonical_snapshots.list_items(
                    snap.canonical_snapshot_id
                )

            ontology_links = uow.ontology_resource_links.list_by_pipeline_run(pipeline_run_id)
            calc_executions = uow.calculation_executions.list_by_pipeline_run(pipeline_run_id)
            param_sets = uow.calculation_parameter_sets.list_by_pipeline_run(pipeline_run_id)
            result_sets = uow.calculation_result_sets.list_by_pipeline_run(pipeline_run_id)
            result_items: dict[UUID, list[CalculationResultItem]] = {}
            reviews: list[CalculationReview] = []
            for rs in result_sets:
                result_items[rs.calculation_result_set_id] = uow.calculation_result_sets.list_items(
                    rs.calculation_result_set_id
                )
                reviews.extend(
                    uow.calculation_reviews.list_for_result_set(rs.calculation_result_set_id)
                )

            publications = uow.result_publication_executions.list_by_pipeline_run(
                pipeline_run_id
            )
            hashes = uow.hash_records.list_by_pipeline_run(pipeline_run_id)
            bundles = uow.prov_bundles.list_by_pipeline_run(pipeline_run_id)

            version_ids: set[UUID] = set()
            for ex in calc_executions:
                version_ids.add(ex.calculation_method_version_id)
            for ps in param_sets:
                version_ids.add(ps.calculation_method_version_id)

            versions: list[CalculationMethodVersion] = []
            method_ids: set[UUID] = set()
            for vid in version_ids:
                v = uow.calculation_method_versions.get(vid)
                if v is not None:
                    versions.append(v)
                    method_ids.add(v.calculation_method_id)

            methods: list[CalculationMethod] = []
            for mid in method_ids:
                m = uow.calculation_methods.get(mid)
                if m is not None:
                    methods.append(m)

            return PipelineRunTraceData(
                run=run,
                source_artifacts=source_artifacts,
                source_artifact_revisions=revisions,
                wrapper_executions=wrapper_executions,
                normalized_batches=normalized_batches,
                semantic_integrations=semantic_integrations,
                canonical_snapshots=canonical_snapshots,
                canonical_snapshot_items=snap_items,
                ontology_resource_links=ontology_links,
                calculation_executions=calc_executions,
                calculation_parameter_sets=param_sets,
                calculation_method_versions=versions,
                calculation_methods=methods,
                calculation_result_sets=result_sets,
                calculation_result_items=result_items,
                calculation_reviews=reviews,
                result_publications=publications,
                hash_records=hashes,
                prov_bundles=bundles,
            )
