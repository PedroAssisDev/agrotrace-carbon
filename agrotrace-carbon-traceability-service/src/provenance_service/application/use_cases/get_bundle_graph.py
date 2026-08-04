"""Project a bundle's PROV graph for the read API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.shared.errors import NotFoundError


@dataclass(slots=True)
class BundleGraphNode:
    kind: str
    id: UUID
    name: str | None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BundleGraphEdge:
    relation: str
    source_id: UUID
    target_id: UUID
    role: str | None = None


@dataclass(slots=True)
class BundleGraphRevisionEdge:
    previous_entity_id: UUID
    new_entity_id: UUID
    revision_reason: str | None = None


@dataclass(slots=True)
class BundleGraph:
    bundle_id: UUID
    pipeline_run_id: UUID
    bundle_type: str
    status: str
    entities: list[BundleGraphNode] = field(default_factory=list)
    activities: list[BundleGraphNode] = field(default_factory=list)
    agents: list[BundleGraphNode] = field(default_factory=list)
    used: list[BundleGraphEdge] = field(default_factory=list)
    generated: list[BundleGraphEdge] = field(default_factory=list)
    associated_with: list[BundleGraphEdge] = field(default_factory=list)
    derived_from: list[BundleGraphEdge] = field(default_factory=list)
    revisions: list[BundleGraphRevisionEdge] = field(default_factory=list)


class GetBundleGraph:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, bundle_id: UUID) -> BundleGraph:
        with self._uow_factory() as uow:
            bundle = uow.prov_bundles.get(bundle_id)
            if bundle is None:
                raise NotFoundError(f"ProvBundle {bundle_id} not found")

            graph = BundleGraph(
                bundle_id=bundle.bundle_id,
                pipeline_run_id=bundle.pipeline_run_id,
                bundle_type=bundle.bundle_type.value,
                status=bundle.status.value,
            )

            entities = uow.prov_entities.list_by_bundle(bundle_id)
            for e in entities:
                graph.entities.append(
                    BundleGraphNode(
                        kind="entity",
                        id=e.entity_id,
                        name=e.name,
                        attributes={
                            "entity_type": e.entity_type.value,
                            "entity_kind": e.entity_kind,
                            "business_key": e.business_key,
                            "content_hash": e.content_hash,
                            "version_label": e.version_label,
                            "invalidated_at": e.invalidated_at.isoformat()
                            if e.invalidated_at
                            else None,
                        },
                    )
                )

            seen_agents: set[UUID] = set()
            activities = uow.prov_activities.list_by_bundle(bundle_id)
            for a in activities:
                graph.activities.append(
                    BundleGraphNode(
                        kind="activity",
                        id=a.activity_id,
                        name=a.name,
                        attributes={
                            "activity_type": a.activity_type.value,
                            "status": a.status,
                            "started_at": a.started_at.isoformat() if a.started_at else None,
                            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
                        },
                    )
                )

                for u in uow.prov_relations.list_used_by_activity(a.activity_id):
                    graph.used.append(
                        BundleGraphEdge(
                            relation="used",
                            source_id=u.activity_id,
                            target_id=u.entity_id,
                            role=u.role,
                        )
                    )

                for g in uow.prov_relations.list_generated_by_activity(a.activity_id):
                    graph.generated.append(
                        BundleGraphEdge(
                            relation="generated",
                            source_id=g.activity_id,
                            target_id=g.entity_id,
                        )
                    )

                for assoc in uow.prov_relations.list_associations_for_activity(a.activity_id):
                    graph.associated_with.append(
                        BundleGraphEdge(
                            relation="associated_with",
                            source_id=assoc.activity_id,
                            target_id=assoc.agent_id,
                            role=assoc.role,
                        )
                    )
                    if assoc.agent_id not in seen_agents:
                        agent = uow.prov_agents.get(assoc.agent_id)
                        if agent is not None:
                            graph.agents.append(
                                BundleGraphNode(
                                    kind="agent",
                                    id=agent.agent_id,
                                    name=agent.name,
                                    attributes={
                                        "agent_type": agent.agent_type.value,
                                        "external_reference": agent.external_reference,
                                        "organization_name": agent.organization_name,
                                    },
                                )
                            )
                            seen_agents.add(assoc.agent_id)

            entity_ids = {e.entity_id for e in entities}
            for eid in entity_ids:
                for d in uow.prov_relations.list_derived_for_entity(eid):
                    graph.derived_from.append(
                        BundleGraphEdge(
                            relation="derived_from",
                            source_id=d.source_entity_id,
                            target_id=d.generated_entity_id,
                            role=d.derivation_type,
                        )
                    )

            for rev in uow.prov_relations.list_revisions_for_pipeline_run(
                bundle.pipeline_run_id
            ):
                if rev.previous_entity_id in entity_ids or rev.new_entity_id in entity_ids:
                    graph.revisions.append(
                        BundleGraphRevisionEdge(
                            previous_entity_id=rev.previous_entity_id,
                            new_entity_id=rev.new_entity_id,
                            revision_reason=rev.revision_reason,
                        )
                    )

            return graph
