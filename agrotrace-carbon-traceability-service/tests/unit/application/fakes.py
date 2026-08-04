"""In-memory fakes used by the recorder unit tests.

Each repository keeps its aggregates in a dict indexed by primary key. This
intentionally mirrors the surface that the SQLAlchemy implementations expose
(``add`` + ``get`` + the read helpers used by the recorder), so unit tests
exercise the same control flow we run in production.
"""

from __future__ import annotations

from dataclasses import replace
from types import TracebackType
from typing import Any
from uuid import UUID

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
    ProvAttribute,
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
    CanonicalSnapshotItem,
    OntologyResourceLink,
    SemanticIntegrationExecution,
)
from provenance_service.domain.shared.enums import CalculationResultSetStatus, OutboxStatus


class _BaseRepo:
    def __init__(self) -> None:
        self.items: dict[UUID, Any] = {}


class FakePipelineRunRepo(_BaseRepo):
    def add(self, run: PipelineRun) -> None:
        self.items[run.pipeline_run_id] = run

    def get(self, pipeline_run_id: UUID) -> PipelineRun | None:
        return self.items.get(pipeline_run_id)

    def get_by_run_code(self, run_code: str) -> PipelineRun | None:
        for r in self.items.values():
            if r.run_code == run_code:
                return r
        return None

    def get_by_idempotency_key(self, key: str) -> PipelineRun | None:
        for r in self.items.values():
            if r.idempotency_key == key:
                return r
        return None

    def list_filtered(
        self,
        *,
        limit: int,
        offset: int,
        run_status: str | None = None,
        farm_reference: str | None = None,
        started_from: object | None = None,
        started_to: object | None = None,
    ) -> tuple[list[PipelineRun], int]:
        rows = list(self.items.values())
        if run_status:
            rows = [r for r in rows if r.run_status.value == run_status]
        if farm_reference:
            rows = [r for r in rows if r.farm_reference == farm_reference]
        total = len(rows)
        return rows[offset : offset + limit], total

    def update_status(
        self, pipeline_run_id: UUID, status, finished_at=None  # type: ignore[no-untyped-def]
    ) -> None:
        run = self.items[pipeline_run_id]
        self.items[pipeline_run_id] = replace(
            run, run_status=status, finished_at=finished_at
        )


class FakeSourceArtifactRepo(_BaseRepo):
    def add(self, artifact: SourceArtifact) -> None:
        self.items[artifact.source_artifact_id] = artifact

    def get(self, artifact_id: UUID) -> SourceArtifact | None:
        return self.items.get(artifact_id)

    def get_by_idempotency_key(self, key: str) -> SourceArtifact | None:
        for a in self.items.values():
            if a.idempotency_key == key:
                return a
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[SourceArtifact]:
        return [a for a in self.items.values() if a.pipeline_run_id == pipeline_run_id]


class FakeSourceArtifactRevisionRepo(_BaseRepo):
    def __init__(self, artifacts: FakeSourceArtifactRepo) -> None:
        super().__init__()
        self._artifacts = artifacts

    def add(self, revision: SourceArtifactRevision) -> None:
        self.items[revision.source_artifact_revision_id] = revision

    def get(self, revision_id: UUID) -> SourceArtifactRevision | None:
        return self.items.get(revision_id)

    def get_by_artifact_and_revision(
        self, source_artifact_id: UUID, revision_number: int
    ) -> SourceArtifactRevision | None:
        for r in self.items.values():
            if r.source_artifact_id == source_artifact_id and r.revision_number == revision_number:
                return r
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[SourceArtifactRevision]:
        out: list[SourceArtifactRevision] = []
        for r in self.items.values():
            art = self._artifacts.get(r.source_artifact_id)
            if art is not None and art.pipeline_run_id == pipeline_run_id:
                out.append(r)
        return out


class FakeWrapperDefinitionRepo(_BaseRepo):
    def add(self, definition: WrapperDefinition) -> None:
        self.items[definition.wrapper_definition_id] = definition

    def get(self, wrapper_definition_id: UUID) -> WrapperDefinition | None:
        return self.items.get(wrapper_definition_id)

    def get_by_name_version(self, name: str, version: str) -> WrapperDefinition | None:
        for d in self.items.values():
            if d.wrapper_name == name and d.wrapper_version == version:
                return d
        return None

    def update_active(self, wrapper_definition_id: UUID, is_active: bool) -> None:
        d = self.items[wrapper_definition_id]
        self.items[wrapper_definition_id] = replace(d, is_active=is_active)


class FakeWrapperExecutionRepo(_BaseRepo):
    def add(self, execution: WrapperExecution) -> None:
        self.items[execution.wrapper_execution_id] = execution

    def get(self, wrapper_execution_id: UUID) -> WrapperExecution | None:
        return self.items.get(wrapper_execution_id)

    def get_by_idempotency_key(self, key: str) -> WrapperExecution | None:
        for e in self.items.values():
            if e.idempotency_key == key:
                return e
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[WrapperExecution]:
        return [e for e in self.items.values() if e.pipeline_run_id == pipeline_run_id]


class FakeNormalizedBatchRepo(_BaseRepo):
    def add(self, batch: NormalizedBatch) -> None:
        self.items[batch.normalized_batch_id] = batch

    def get(self, normalized_batch_id: UUID) -> NormalizedBatch | None:
        return self.items.get(normalized_batch_id)

    def get_by_idempotency_key(self, key: str) -> NormalizedBatch | None:
        for b in self.items.values():
            if b.idempotency_key == key:
                return b
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[NormalizedBatch]:
        return [b for b in self.items.values() if b.pipeline_run_id == pipeline_run_id]


class FakeProvBundleRepo(_BaseRepo):
    def add(self, bundle: ProvBundle) -> None:
        self.items[bundle.bundle_id] = bundle

    def get(self, bundle_id: UUID) -> ProvBundle | None:
        return self.items.get(bundle_id)

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[ProvBundle]:
        return [b for b in self.items.values() if b.pipeline_run_id == pipeline_run_id]

    def close(self, bundle_id: UUID) -> None:  # pragma: no cover - unused in unit tests
        b = self.items[bundle_id]
        self.items[bundle_id] = replace(b, closed_at=None)


class FakeProvEntityRepo(_BaseRepo):
    def add(self, entity: ProvEntity) -> None:
        self.items[entity.entity_id] = entity

    def get(self, entity_id: UUID) -> ProvEntity | None:
        return self.items.get(entity_id)

    def list_by_bundle(self, bundle_id: UUID) -> list[ProvEntity]:
        return [e for e in self.items.values() if e.bundle_id == bundle_id]

    def invalidate(self, entity_id: UUID) -> None:
        from provenance_service.domain.shared.time import utcnow

        e = self.items[entity_id]
        self.items[entity_id] = replace(e, invalidated_at=utcnow())


class FakeProvActivityRepo(_BaseRepo):
    def add(self, activity: ProvActivity) -> None:
        self.items[activity.activity_id] = activity

    def get(self, activity_id: UUID) -> ProvActivity | None:
        return self.items.get(activity_id)

    def list_by_bundle(self, bundle_id: UUID) -> list[ProvActivity]:
        return [a for a in self.items.values() if a.bundle_id == bundle_id]


class FakeProvAgentRepo(_BaseRepo):
    def add(self, agent: ProvAgent) -> None:
        self.items[agent.agent_id] = agent

    def get(self, agent_id: UUID) -> ProvAgent | None:
        return self.items.get(agent_id)

    def get_by_external_reference(self, external_reference: str) -> ProvAgent | None:
        for a in self.items.values():
            if a.external_reference == external_reference:
                return a
        return None


class FakeProvRelationRepo:
    def __init__(self) -> None:
        self.used: list[ProvUsed] = []
        self.generated: list[ProvGenerated] = []
        self.derived_from: list[ProvDerivedFrom] = []
        self.associated_with: list[ProvAssociatedWith] = []
        self.revisions: list[ProvRevision] = []

    def add_used(self, relation: ProvUsed) -> None:
        self.used.append(relation)

    def add_generated(self, relation: ProvGenerated) -> None:
        self.generated.append(relation)

    def add_derived_from(self, relation: ProvDerivedFrom) -> None:
        self.derived_from.append(relation)

    def add_associated_with(self, relation: ProvAssociatedWith) -> None:
        self.associated_with.append(relation)

    def add_revision(self, revision: ProvRevision) -> None:
        self.revisions.append(revision)

    def list_used_by_activity(self, activity_id: UUID) -> list[ProvUsed]:
        return [u for u in self.used if u.activity_id == activity_id]

    def list_generated_by_activity(self, activity_id: UUID) -> list[ProvGenerated]:
        return [g for g in self.generated if g.activity_id == activity_id]

    def list_derived_for_entity(self, entity_id: UUID) -> list[ProvDerivedFrom]:
        return [d for d in self.derived_from if d.generated_entity_id == entity_id]

    def list_associations_for_activity(self, activity_id: UUID) -> list[ProvAssociatedWith]:
        return [a for a in self.associated_with if a.activity_id == activity_id]


class FakeProvAttributeRepo:
    def __init__(self) -> None:
        self.items: list[ProvAttribute] = []

    def add(self, attr: ProvAttribute) -> None:
        self.items.append(attr)

    def list_for_entity(self, entity_id: UUID) -> list[ProvAttribute]:
        return [a for a in self.items if a.entity_id == entity_id]

    def list_for_activity(self, activity_id: UUID) -> list[ProvAttribute]:
        return [a for a in self.items if a.activity_id == activity_id]

    def list_for_agent(self, agent_id: UUID) -> list[ProvAttribute]:
        return [a for a in self.items if a.agent_id == agent_id]


class FakeSemanticIntegrationRepo(_BaseRepo):
    def add(self, execution: SemanticIntegrationExecution) -> None:
        self.items[execution.semantic_integration_execution_id] = execution

    def get(self, _id: UUID) -> SemanticIntegrationExecution | None:
        return self.items.get(_id)

    def get_by_idempotency_key(
        self, key: str
    ) -> SemanticIntegrationExecution | None:
        for x in self.items.values():
            if x.idempotency_key == key:
                return x
        return None

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[SemanticIntegrationExecution]:
        return [
            x for x in self.items.values() if x.pipeline_run_id == pipeline_run_id
        ]


class FakeCanonicalSnapshotRepo(_BaseRepo):
    def __init__(self) -> None:
        super().__init__()
        self.items_per_snapshot: dict[UUID, list[CanonicalSnapshotItem]] = {}

    def add(self, snapshot: CanonicalSnapshot) -> None:
        self.items[snapshot.canonical_snapshot_id] = snapshot

    def get(self, _id: UUID) -> CanonicalSnapshot | None:
        return self.items.get(_id)

    def get_by_hash(self, snapshot_hash: str) -> CanonicalSnapshot | None:
        for s in self.items.values():
            if s.snapshot_hash == snapshot_hash:
                return s
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[CanonicalSnapshot]:
        return [
            s for s in self.items.values() if s.pipeline_run_id == pipeline_run_id
        ]

    def add_item(self, item: CanonicalSnapshotItem) -> None:
        self.items_per_snapshot.setdefault(item.canonical_snapshot_id, []).append(item)

    def list_items(self, snapshot_id: UUID) -> list[CanonicalSnapshotItem]:
        return list(self.items_per_snapshot.get(snapshot_id, []))


class FakeOntologyResourceLinkRepo(_BaseRepo):
    def add(self, link: OntologyResourceLink) -> None:
        self.items[link.ontology_resource_link_id] = link

    def get(self, _id: UUID) -> OntologyResourceLink | None:
        return self.items.get(_id)

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[OntologyResourceLink]:
        return [
            link
            for link in self.items.values()
            if link.pipeline_run_id == pipeline_run_id
        ]


class FakeCalculationMethodRepo(_BaseRepo):
    def add(self, method: CalculationMethod) -> None:
        self.items[method.calculation_method_id] = method

    def get(self, _id: UUID) -> CalculationMethod | None:
        return self.items.get(_id)

    def get_by_code(self, method_code: str) -> CalculationMethod | None:
        for m in self.items.values():
            if m.method_code == method_code:
                return m
        return None

    def list_all(self) -> list[CalculationMethod]:
        return list(self.items.values())


class FakeCalculationMethodVersionRepo(_BaseRepo):
    def add(self, version: CalculationMethodVersion) -> None:
        self.items[version.calculation_method_version_id] = version

    def get(self, _id: UUID) -> CalculationMethodVersion | None:
        return self.items.get(_id)

    def list_by_method(self, method_id: UUID) -> list[CalculationMethodVersion]:
        return [
            v for v in self.items.values() if v.calculation_method_id == method_id
        ]


class FakeCalculationParameterSetRepo(_BaseRepo):
    def __init__(self) -> None:
        super().__init__()
        self.values_per_set: dict[UUID, list[CalculationParameterValue]] = {}

    def add(self, parameter_set: CalculationParameterSet) -> None:
        self.items[parameter_set.calculation_parameter_set_id] = parameter_set

    def add_value(self, value: CalculationParameterValue) -> None:
        self.values_per_set.setdefault(
            value.calculation_parameter_set_id, []
        ).append(value)

    def get(self, _id: UUID) -> CalculationParameterSet | None:
        return self.items.get(_id)

    def list_values(self, _id: UUID) -> list[CalculationParameterValue]:
        return list(self.values_per_set.get(_id, []))

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[CalculationParameterSet]:
        return [
            s for s in self.items.values() if s.pipeline_run_id == pipeline_run_id
        ]


class FakeCalculationExecutionRepo(_BaseRepo):
    def add(self, execution: CalculationExecution) -> None:
        self.items[execution.calculation_execution_id] = execution

    def get(self, _id: UUID) -> CalculationExecution | None:
        return self.items.get(_id)

    def get_by_idempotency_key(self, key: str) -> CalculationExecution | None:
        for e in self.items.values():
            if e.idempotency_key == key:
                return e
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[CalculationExecution]:
        return [
            e for e in self.items.values() if e.pipeline_run_id == pipeline_run_id
        ]


class FakeCalculationResultSetRepo(_BaseRepo):
    def __init__(self) -> None:
        super().__init__()
        self.items_per_set: dict[UUID, list[CalculationResultItem]] = {}

    def add(self, result_set: CalculationResultSet) -> None:
        self.items[result_set.calculation_result_set_id] = result_set

    def add_item(self, item: CalculationResultItem) -> None:
        self.items_per_set.setdefault(
            item.calculation_result_set_id, []
        ).append(item)

    def get(self, _id: UUID) -> CalculationResultSet | None:
        return self.items.get(_id)

    def list_items(self, _id: UUID) -> list[CalculationResultItem]:
        return list(self.items_per_set.get(_id, []))

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[CalculationResultSet]:
        return [
            s for s in self.items.values() if s.pipeline_run_id == pipeline_run_id
        ]

    def update_status(
        self, calculation_result_set_id: UUID, status: CalculationResultSetStatus
    ) -> None:
        rs = self.items[calculation_result_set_id]
        self.items[calculation_result_set_id] = replace(rs, result_set_status=status)

    def update_approved_at(
        self, calculation_result_set_id: UUID, approved_at: object
    ) -> None:
        rs = self.items[calculation_result_set_id]
        self.items[calculation_result_set_id] = replace(rs, approved_at=approved_at)

    def update_published_at(
        self, calculation_result_set_id: UUID, published_at: object
    ) -> None:
        rs = self.items[calculation_result_set_id]
        self.items[calculation_result_set_id] = replace(rs, published_at=published_at)

    def mark_superseded(self, current_id: UUID, superseded_by_id: UUID) -> None:
        rs = self.items[current_id]
        self.items[current_id] = replace(rs, superseded_by_id=superseded_by_id)


class FakeCalculationReviewRepo(_BaseRepo):
    def add(self, review: CalculationReview) -> None:
        self.items[review.calculation_review_id] = review

    def get(self, _id: UUID) -> CalculationReview | None:
        return self.items.get(_id)

    def list_for_result_set(self, result_set_id: UUID) -> list[CalculationReview]:
        return [
            r for r in self.items.values() if r.calculation_result_set_id == result_set_id
        ]


class FakeResultPublicationRepo(_BaseRepo):
    def add(self, publication: ResultPublicationExecution) -> None:
        self.items[publication.result_publication_execution_id] = publication

    def get(self, _id: UUID) -> ResultPublicationExecution | None:
        return self.items.get(_id)

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[ResultPublicationExecution]:
        return [
            p for p in self.items.values() if p.pipeline_run_id == pipeline_run_id
        ]


class FakeResultAggregationLinkRepo:
    def __init__(self) -> None:
        self.items: list[CalculationResultAggregationLink] = []

    def add(self, link: CalculationResultAggregationLink) -> None:
        self.items.append(link)

    def list_children(self, parent_result_set_id: UUID) -> list[CalculationResultAggregationLink]:
        return [
            l for l in self.items if l.parent_result_set_id == parent_result_set_id
        ]

    def list_parents(self, child_result_set_id: UUID) -> list[CalculationResultAggregationLink]:
        return [
            l for l in self.items if l.child_result_set_id == child_result_set_id
        ]


class FakeReportingPeriodRepo(_BaseRepo):
    def add(self, period: ReportingPeriod) -> None:
        self.items[period.reporting_period_id] = period

    def get(self, _id: UUID) -> ReportingPeriod | None:
        return self.items.get(_id)

    def get_by_label(self, period_label: str) -> ReportingPeriod | None:
        for p in self.items.values():
            if p.period_label == period_label:
                return p
        return None

    def list_all(self) -> list[ReportingPeriod]:
        return list(self.items.values())


class FakeHashRecordRepo(_BaseRepo):
    def add(self, record: HashRecord) -> None:
        self.items[record.hash_record_id] = record

    def get(self, _id: UUID) -> HashRecord | None:
        return self.items.get(_id)

    def find_by_subject(
        self, subject_kind: str, subject_id: UUID, hash_algorithm: str
    ) -> HashRecord | None:
        for r in self.items.values():
            if (
                r.subject_kind.value == subject_kind
                and r.subject_id == subject_id
                and r.hash_algorithm.value == hash_algorithm
            ):
                return r
        return None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[HashRecord]:
        return [
            r for r in self.items.values() if r.pipeline_run_id == pipeline_run_id
        ]


class FakeBlockchainAnchorRepo(_BaseRepo):
    def add(self, anchor: BlockchainAnchor) -> None:
        self.items[anchor.blockchain_anchor_id] = anchor

    def get(self, _id: UUID) -> BlockchainAnchor | None:
        return self.items.get(_id)

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[BlockchainAnchor]:
        return [
            a for a in self.items.values() if a.pipeline_run_id == pipeline_run_id
        ]


class FakeOutboxRepo:
    def __init__(self) -> None:
        self.items: dict[UUID, OutboxEvent] = {}
        self.failures: list[tuple[UUID, str]] = []

    def add(self, event: OutboxEvent) -> None:
        self.items[event.outbox_event_id] = event

    def list_pending(self, limit: int) -> list[OutboxEvent]:
        return [
            e for e in self.items.values() if e.status is OutboxStatus.PENDING
        ][:limit]

    def list_filtered(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        aggregate_kind: str | None = None,
    ) -> tuple[list[OutboxEvent], int]:
        rows = list(self.items.values())
        if status:
            rows = [e for e in rows if e.status.value == status]
        if aggregate_kind:
            rows = [e for e in rows if e.aggregate_kind == aggregate_kind]
        total = len(rows)
        return rows[offset : offset + limit], total

    def mark_published(self, outbox_event_id: UUID) -> None:
        from provenance_service.domain.shared.time import utcnow

        e = self.items[outbox_event_id]
        self.items[outbox_event_id] = replace(
            e, status=OutboxStatus.PUBLISHED, published_at=utcnow()
        )

    def mark_failed(self, outbox_event_id: UUID, *, reason: str) -> None:
        e = self.items[outbox_event_id]
        self.items[outbox_event_id] = replace(e, status=OutboxStatus.FAILED)
        self.failures.append((outbox_event_id, reason))


class FakeAuditEventRepo:
    def __init__(self) -> None:
        self.items: list[AuditEvent] = []

    def add(self, event: AuditEvent) -> None:
        self.items.append(event)

    def list_for_subject(self, subject_kind: str, subject_id: UUID) -> list[AuditEvent]:
        return [
            e
            for e in self.items
            if e.subject_kind == subject_kind and e.subject_id == subject_id
        ]


class FakeUnitOfWork:
    """Sufficient surface to satisfy the recorder's ``UnitOfWork`` protocol."""

    def __init__(self) -> None:
        self.pipeline_runs = FakePipelineRunRepo()
        self.source_artifacts = FakeSourceArtifactRepo()
        self.source_artifact_revisions = FakeSourceArtifactRevisionRepo(
            self.source_artifacts
        )
        self.wrapper_definitions = FakeWrapperDefinitionRepo()
        self.wrapper_executions = FakeWrapperExecutionRepo()
        self.normalized_batches = FakeNormalizedBatchRepo()

        self.prov_bundles = FakeProvBundleRepo()
        self.prov_entities = FakeProvEntityRepo()
        self.prov_activities = FakeProvActivityRepo()
        self.prov_agents = FakeProvAgentRepo()
        self.prov_relations = FakeProvRelationRepo()
        self.prov_attributes = FakeProvAttributeRepo()

        self.semantic_integration_executions = FakeSemanticIntegrationRepo()
        self.canonical_snapshots = FakeCanonicalSnapshotRepo()
        self.ontology_resource_links = FakeOntologyResourceLinkRepo()

        self.calculation_methods = FakeCalculationMethodRepo()
        self.calculation_method_versions = FakeCalculationMethodVersionRepo()
        self.calculation_parameter_sets = FakeCalculationParameterSetRepo()
        self.calculation_executions = FakeCalculationExecutionRepo()
        self.calculation_result_sets = FakeCalculationResultSetRepo()
        self.calculation_reviews = FakeCalculationReviewRepo()
        self.result_publication_executions = FakeResultPublicationRepo()
        self.result_aggregation_links = FakeResultAggregationLinkRepo()
        self.reporting_periods = FakeReportingPeriodRepo()

        self.hash_records = FakeHashRecordRepo()
        self.blockchain_anchors = FakeBlockchainAnchorRepo()
        self.outbox = FakeOutboxRepo()
        self.audit_events = FakeAuditEventRepo()

        self.committed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def flush(self) -> None:
        pass
