"""HTTP DTOs for the ``semantic`` bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from provenance_service.domain.shared.enums import (
    PublicationStage,
    SemanticExecutionStatus,
)
from provenance_service.interfaces.api.schemas.common import (
    ReadApiBaseModel,
    WriteApiBaseModel,
)


# ----------------- semantic_integration_execution -----------------


class RegisterSemanticIntegrationRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    normalized_batch_id: UUID
    ontology_name: str = Field(min_length=1, max_length=128)
    ontology_version: str = Field(min_length=1, max_length=64)
    mapping_rule_version: str = Field(min_length=1, max_length=64)
    started_at: datetime
    execution_status: SemanticExecutionStatus = SemanticExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    triples_generated: int | None = Field(default=None, ge=0)
    integrator_agent_external_reference: str | None = None
    integrator_agent_name: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)


class SemanticIntegrationExecutionResponse(ReadApiBaseModel):
    semantic_integration_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    normalized_batch_id: UUID
    ontology_name: str
    ontology_version: str
    mapping_rule_version: str
    execution_status: SemanticExecutionStatus
    started_at: datetime
    finished_at: datetime | None
    triples_generated: int | None
    idempotency_key: str | None
    metadata: dict[str, Any]


# ----------------- canonical_snapshot -----------------


class CanonicalSnapshotItemInput(WriteApiBaseModel):
    item_key: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any]


class RegisterCanonicalSnapshotRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    semantic_integration_execution_id: UUID
    graph_name: str = Field(min_length=1, max_length=255)
    snapshot_label: str = Field(min_length=1, max_length=255)
    schema_version: str | None = None
    storage_uri: str | None = None
    payload: dict[str, Any] | None = None
    items: list[CanonicalSnapshotItemInput] = Field(default_factory=list)
    published_at: datetime | None = None
    reporting_period_id: UUID | None = None
    canonical_schema_version: str | None = None
    item_count: int | None = Field(default=None, ge=0)
    snapshot_payload_ref: str | None = None


class CanonicalSnapshotResponse(ReadApiBaseModel):
    canonical_snapshot_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    semantic_integration_execution_id: UUID
    graph_name: str
    snapshot_label: str
    snapshot_hash: str
    schema_version: str | None
    storage_uri: str | None
    payload: dict[str, Any] | None
    published_at: datetime
    reporting_period_id: UUID | None = None
    canonical_schema_version: str | None = None
    item_count: int | None = None
    snapshot_payload_ref: str | None = None
    metadata: dict[str, Any]


# ----------------- ontology_resource_link -----------------


class RegisterOntologyResourceLinkRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    ontology_uri: str = Field(min_length=1, max_length=1024)
    graph_name: str = Field(min_length=1, max_length=255)
    publication_stage: PublicationStage = PublicationStage.FINAL
    prov_entity_id: UUID | None = None
    canonical_snapshot_id: UUID | None = None
    rdf_class: str | None = None
    ontology_version: str | None = None
    published_at: datetime | None = None


class OntologyResourceLinkResponse(ReadApiBaseModel):
    ontology_resource_link_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID | None
    canonical_snapshot_id: UUID | None
    ontology_uri: str
    rdf_class: str | None
    graph_name: str
    ontology_version: str | None
    publication_stage: PublicationStage
    published_at: datetime
    metadata: dict[str, Any]
