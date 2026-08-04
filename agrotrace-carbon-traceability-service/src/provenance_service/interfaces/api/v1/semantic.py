"""Semantic-context HTTP routes (3 endpoints)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from provenance_service.application.services import (
    RecordCanonicalSnapshotCommand,
    RecordSemanticIntegrationCommand,
)
from provenance_service.application.use_cases import (
    RegisterCanonicalSnapshot,
    RegisterOntologyResourceLink,
    RegisterSemanticIntegration,
)
from provenance_service.application.use_cases.register_ontology_resource_link import (
    RegisterOntologyResourceLinkCommand,
)
from provenance_service.interfaces.api.deps import (
    provide_register_canonical_snapshot,
    provide_register_ontology_resource_link,
    provide_register_semantic_integration,
)
from provenance_service.interfaces.api.schemas.semantic import (
    CanonicalSnapshotResponse,
    OntologyResourceLinkResponse,
    RegisterCanonicalSnapshotRequest,
    RegisterOntologyResourceLinkRequest,
    RegisterSemanticIntegrationRequest,
    SemanticIntegrationExecutionResponse,
)

router = APIRouter(tags=["semantic"])


@router.post(
    "/semantic-integrations",
    response_model=SemanticIntegrationExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_semantic_integration(
    payload: RegisterSemanticIntegrationRequest,
    use_case: Annotated[
        RegisterSemanticIntegration, Depends(provide_register_semantic_integration)
    ],
) -> SemanticIntegrationExecutionResponse:
    cmd = RecordSemanticIntegrationCommand(**payload.model_dump())
    integration = use_case.execute(cmd)
    return SemanticIntegrationExecutionResponse.model_validate(integration)


@router.post(
    "/canonical-snapshots",
    response_model=CanonicalSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_canonical_snapshot(
    payload: RegisterCanonicalSnapshotRequest,
    use_case: Annotated[
        RegisterCanonicalSnapshot, Depends(provide_register_canonical_snapshot)
    ],
) -> CanonicalSnapshotResponse:
    body = payload.model_dump()
    raw_items = body.pop("items", []) or []
    items = [{"item_key": item["item_key"], **item["payload"]} for item in raw_items]
    cmd = RecordCanonicalSnapshotCommand(**body, items=items)
    snapshot = use_case.execute(cmd)
    return CanonicalSnapshotResponse.model_validate(snapshot)


@router.post(
    "/ontology-links",
    response_model=OntologyResourceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_ontology_link(
    payload: RegisterOntologyResourceLinkRequest,
    use_case: Annotated[
        RegisterOntologyResourceLink, Depends(provide_register_ontology_resource_link)
    ],
) -> OntologyResourceLinkResponse:
    cmd = RegisterOntologyResourceLinkCommand(**payload.model_dump())
    link = use_case.execute(cmd)
    return OntologyResourceLinkResponse.model_validate(link)
