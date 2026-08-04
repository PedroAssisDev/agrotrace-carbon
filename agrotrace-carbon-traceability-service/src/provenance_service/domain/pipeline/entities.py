"""Pipeline-context aggregates: pure dataclasses, no SQLA."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import PipelineRunStatus, RunType, WrapperExecutionStatus


@dataclass(slots=True)
class PipelineRun:
    pipeline_run_id: UUID
    run_code: str
    farm_reference: str
    reporting_period_reference: str
    run_status: PipelineRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    parent_pipeline_run_id: UUID | None = None
    triggered_by_agent_id: UUID | None = None
    notes: str | None = None
    tenant_id: UUID | None = None
    idempotency_key: str | None = None
    run_type: RunType | None = None
    reporting_period_id: UUID | None = None
    farm_id_hash: str | None = None
    project_id_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceArtifact:
    source_artifact_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    source_system: str
    original_filename: str
    storage_uri: str
    content_hash: str
    received_at: datetime
    source_layout_name: str | None = None
    source_layout_version: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceArtifactRevision:
    source_artifact_revision_id: UUID
    source_artifact_id: UUID
    revision_number: int
    storage_uri: str
    content_hash: str
    received_at: datetime
    is_current: bool = True
    mime_type: str | None = None
    file_size_bytes: int | None = None
    prov_entity_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WrapperDefinition:
    wrapper_definition_id: UUID
    wrapper_name: str
    wrapper_version: str
    source_layout_name: str
    created_at: datetime
    is_active: bool = True
    source_layout_version: str | None = None
    schema_version: str | None = None
    code_hash: str | None = None
    wrapper_code_hash: str | None = None
    input_schema_hash: str | None = None
    output_schema_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WrapperExecution:
    wrapper_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    wrapper_definition_id: UUID
    input_artifact_id: UUID
    execution_status: WrapperExecutionStatus
    started_at: datetime
    finished_at: datetime | None = None
    warning_count: int = 0
    error_count: int = 0
    execution_log_uri: str | None = None
    idempotency_key: str | None = None
    input_source_artifact_revision_id: UUID | None = None
    execution_payload_hash: str | None = None
    runtime_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NormalizedBatch:
    normalized_batch_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    wrapper_execution_id: UUID
    batch_code: str
    schema_version: str
    record_count: int
    generated_at: datetime
    storage_uri: str | None = None
    content_hash: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
