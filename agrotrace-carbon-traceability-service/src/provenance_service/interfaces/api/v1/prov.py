"""PROV-core read-only HTTP routes (5 endpoints)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from provenance_service.application.use_cases import GetBundleGraph
from provenance_service.domain.shared.errors import NotFoundError
from provenance_service.interfaces.api.deps import (
    SessionFactoryDep,
    provide_get_bundle_graph,
)
from provenance_service.interfaces.api.schemas.prov import (
    BundleGraphResponse,
    GraphEdge,
    GraphNode,
    GraphRevisionEdge,
    ProvActivityResponse,
    ProvAgentResponse,
    ProvBundleResponse,
    ProvEntityResponse,
)
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(tags=["prov"])


@router.get("/bundles/{bundle_id}", response_model=ProvBundleResponse)
def get_bundle(
    bundle_id: UUID, session_factory: SessionFactoryDep
) -> ProvBundleResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        bundle = uow.prov_bundles.get(bundle_id)
        if bundle is None:
            raise NotFoundError(f"ProvBundle {bundle_id} not found")
        return ProvBundleResponse.model_validate(bundle)


@router.get("/entities/{entity_id}", response_model=ProvEntityResponse)
def get_entity(
    entity_id: UUID, session_factory: SessionFactoryDep
) -> ProvEntityResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        entity = uow.prov_entities.get(entity_id)
        if entity is None:
            raise NotFoundError(f"ProvEntity {entity_id} not found")
        return ProvEntityResponse.model_validate(entity)


@router.get("/activities/{activity_id}", response_model=ProvActivityResponse)
def get_activity(
    activity_id: UUID, session_factory: SessionFactoryDep
) -> ProvActivityResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        activity = uow.prov_activities.get(activity_id)
        if activity is None:
            raise NotFoundError(f"ProvActivity {activity_id} not found")
        return ProvActivityResponse.model_validate(activity)


@router.get("/agents/{agent_id}", response_model=ProvAgentResponse)
def get_agent(agent_id: UUID, session_factory: SessionFactoryDep) -> ProvAgentResponse:
    with SqlAlchemyUnitOfWork(session_factory) as uow:
        agent = uow.prov_agents.get(agent_id)
        if agent is None:
            raise NotFoundError(f"ProvAgent {agent_id} not found")
        return ProvAgentResponse.model_validate(agent)


@router.get("/bundles/{bundle_id}/graph", response_model=BundleGraphResponse)
def get_bundle_graph(
    bundle_id: UUID,
    use_case: Annotated[GetBundleGraph, Depends(provide_get_bundle_graph)],
) -> BundleGraphResponse:
    graph = use_case.execute(bundle_id)
    return BundleGraphResponse(
        bundle_id=graph.bundle_id,
        pipeline_run_id=graph.pipeline_run_id,
        bundle_type=graph.bundle_type,
        status=graph.status,
        entities=[GraphNode.model_validate(node) for node in graph.entities],
        activities=[GraphNode.model_validate(node) for node in graph.activities],
        agents=[GraphNode.model_validate(node) for node in graph.agents],
        used=[GraphEdge.model_validate(edge) for edge in graph.used],
        generated=[GraphEdge.model_validate(edge) for edge in graph.generated],
        associated_with=[
            GraphEdge.model_validate(edge) for edge in graph.associated_with
        ],
        derived_from=[GraphEdge.model_validate(edge) for edge in graph.derived_from],
        revisions=[
            GraphRevisionEdge.model_validate(edge) for edge in graph.revisions
        ],
    )
