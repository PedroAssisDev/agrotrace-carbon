"""HTTP DTOs for the ``prov_core`` bounded context (read-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import (
    ProvActivityType,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
)
from provenance_service.interfaces.api.schemas.common import ReadApiBaseModel


class ProvBundleResponse(ReadApiBaseModel):
    bundle_id: UUID
    pipeline_run_id: UUID
    bundle_type: ProvBundleType
    name: str | None
    status: ProvBundleStatus
    created_at: datetime
    closed_at: datetime | None
    metadata: dict[str, Any]


class ProvEntityResponse(ReadApiBaseModel):
    entity_id: UUID
    bundle_id: UUID
    pipeline_run_id: UUID
    entity_type: ProvEntityType
    entity_kind: str | None
    entity_ref_id: UUID | None
    business_key: str | None
    name: str | None
    description: str | None
    version_label: str | None
    content_hash: str | None
    created_at: datetime
    invalidated_at: datetime | None
    metadata: dict[str, Any]


class ProvActivityResponse(ReadApiBaseModel):
    activity_id: UUID
    bundle_id: UUID
    pipeline_run_id: UUID
    activity_type: ProvActivityType
    business_key: str | None
    name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    software_version: str | None
    recorded_at: datetime
    metadata: dict[str, Any]


class ProvAgentResponse(ReadApiBaseModel):
    agent_id: UUID
    agent_type: ProvAgentType
    name: str
    external_reference: str | None
    organization_name: str | None
    created_at: datetime
    metadata: dict[str, Any]


class GraphNode(ReadApiBaseModel):
    kind: str
    id: UUID
    name: str | None
    attributes: dict[str, Any]


class GraphEdge(ReadApiBaseModel):
    relation: str
    source_id: UUID
    target_id: UUID
    role: str | None = None


class GraphRevisionEdge(ReadApiBaseModel):
    previous_entity_id: UUID
    new_entity_id: UUID
    revision_reason: str | None = None


class BundleGraphResponse(ReadApiBaseModel):
    bundle_id: UUID
    pipeline_run_id: UUID
    bundle_type: str
    status: str
    entities: list[GraphNode]
    activities: list[GraphNode]
    agents: list[GraphNode]
    used: list[GraphEdge]
    generated: list[GraphEdge]
    associated_with: list[GraphEdge]
    derived_from: list[GraphEdge] = []
    revisions: list[GraphRevisionEdge] = []
