"""PROV-DM relations as standalone aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class ProvUsed:
    used_id: UUID
    activity_id: UUID
    entity_id: UUID
    role: str | None = None
    used_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvGenerated:
    generated_id: UUID
    entity_id: UUID
    activity_id: UUID
    generated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvDerivedFrom:
    derived_id: UUID
    generated_entity_id: UUID
    source_entity_id: UUID
    derivation_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvAssociatedWith:
    association_id: UUID
    activity_id: UUID
    agent_id: UUID
    role: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProvRevision:
    revision_id: UUID
    previous_entity_id: UUID
    new_entity_id: UUID
    revised_at: datetime
    revision_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
