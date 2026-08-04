"""Semantic-context aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import (
    PublicationStage,
    SemanticExecutionStatus,
)


@dataclass(slots=True)
class SemanticIntegrationExecution:
    semantic_integration_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    normalized_batch_id: UUID
    ontology_name: str
    ontology_version: str
    mapping_rule_version: str
    execution_status: SemanticExecutionStatus
    started_at: datetime
    finished_at: datetime | None = None
    triples_generated: int | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CanonicalSnapshot:
    canonical_snapshot_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    semantic_integration_execution_id: UUID
    graph_name: str
    snapshot_label: str
    snapshot_hash: str
    published_at: datetime
    schema_version: str | None = None
    canonical_schema_version: str | None = None
    item_count: int | None = None
    snapshot_payload_ref: str | None = None
    storage_uri: str | None = None
    payload: dict[str, Any] | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CanonicalSnapshotItem:
    canonical_snapshot_item_id: UUID
    canonical_snapshot_id: UUID
    item_key: str
    payload: dict[str, Any]
    item_hash: str | None = None


@dataclass(slots=True)
class OntologyResourceLink:
    ontology_resource_link_id: UUID
    pipeline_run_id: UUID
    ontology_uri: str
    graph_name: str
    publication_stage: PublicationStage
    published_at: datetime
    prov_entity_id: UUID | None = None
    canonical_snapshot_id: UUID | None = None
    rdf_class: str | None = None
    ontology_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
