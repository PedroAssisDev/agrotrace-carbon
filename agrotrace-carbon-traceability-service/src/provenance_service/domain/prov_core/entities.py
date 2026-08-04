"""W3C PROV-DM aligned entities (pure dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(slots=True)
class ProvBundle:
    bundle_id: UUID
    pipeline_run_id: UUID
    bundle_type: ProvBundleType
    status: ProvBundleStatus
    created_at: datetime
    name: str | None = None
    closed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvEntity:
    entity_id: UUID
    bundle_id: UUID
    pipeline_run_id: UUID
    entity_type: ProvEntityType
    created_at: datetime
    entity_kind: str | None = None
    entity_ref_id: UUID | None = None
    business_key: str | None = None
    name: str | None = None
    description: str | None = None
    version_label: str | None = None
    content_hash: str | None = None
    invalidated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvActivity:
    activity_id: UUID
    bundle_id: UUID
    pipeline_run_id: UUID
    activity_type: ProvActivityType
    status: str
    recorded_at: datetime
    business_key: str | None = None
    name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    software_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvAgent:
    agent_id: UUID
    agent_type: ProvAgentType
    name: str
    created_at: datetime
    external_reference: str | None = None
    organization_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvAttribute:
    prov_attribute_id: UUID
    attr_key: str
    attr_value: dict[str, Any]
    recorded_at: datetime
    entity_id: UUID | None = None
    activity_id: UUID | None = None
    agent_id: UUID | None = None
