"""HTTP DTOs for the ``pipeline`` bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from provenance_service.domain.shared.enums import (
    PipelineRunStatus,
    RunType,
    WrapperExecutionStatus,
)
from provenance_service.interfaces.api.schemas.audit import HashRecordResponse
from provenance_service.interfaces.api.schemas.calculation import (
    CalculationExecutionResponse,
    CalculationMethodResponse,
    CalculationMethodVersionResponse,
    CalculationParameterSetResponse,
    CalculationResultSetResponse,
    CalculationReviewResponse,
    ResultPublicationExecutionResponse,
)
from provenance_service.interfaces.api.schemas.common import (
    ReadApiBaseModel,
    WriteApiBaseModel,
)
from provenance_service.interfaces.api.schemas.prov import (
    BundleGraphResponse,
    ProvBundleResponse,
)
from provenance_service.interfaces.api.schemas.semantic import (
    CanonicalSnapshotResponse,
    OntologyResourceLinkResponse,
    SemanticIntegrationExecutionResponse,
)


# -------------------------- pipeline_run --------------------------


class StartPipelineRunRequest(WriteApiBaseModel):
    run_code: str = Field(min_length=1, max_length=128)
    farm_reference: str = Field(min_length=1, max_length=255)
    reporting_period_reference: str = Field(min_length=1, max_length=128)
    started_at: datetime | None = None
    parent_pipeline_run_id: UUID | None = None
    triggered_by_agent_id: UUID | None = None
    notes: str | None = None
    tenant_id: UUID | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)
    run_type: RunType | None = None
    reporting_period_id: UUID | None = None
    farm_id_hash: str | None = None
    project_id_hash: str | None = None


class PipelineRunResponse(ReadApiBaseModel):
    pipeline_run_id: UUID
    run_code: str
    farm_reference: str
    reporting_period_reference: str
    run_status: PipelineRunStatus
    started_at: datetime
    finished_at: datetime | None
    parent_pipeline_run_id: UUID | None
    triggered_by_agent_id: UUID | None
    tenant_id: UUID | None
    notes: str | None
    idempotency_key: str | None
    run_type: RunType | None = None
    reporting_period_id: UUID | None = None
    farm_id_hash: str | None = None
    project_id_hash: str | None = None
    metadata: dict[str, Any]


class PipelineRunListResponse(ReadApiBaseModel):
    items: list[PipelineRunResponse]
    total: int
    limit: int
    offset: int


# -------------------------- source_artifact --------------------------


class RegisterSourceArtifactRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    source_system: str = Field(min_length=1, max_length=128)
    original_filename: str = Field(min_length=1, max_length=512)
    storage_uri: str = Field(min_length=1, max_length=1024)
    content_hash: str = Field(min_length=4, max_length=128)
    received_at: datetime | None = None
    source_layout_name: str | None = None
    source_layout_version: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    business_key: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)


class RegisterSourceArtifactRevisionRequest(WriteApiBaseModel):
    source_artifact_id: UUID
    revision_number: int = Field(ge=1)
    storage_uri: str = Field(min_length=1, max_length=1024)
    content_hash: str = Field(min_length=4, max_length=128)
    received_at: datetime | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    is_current: bool = True


class SourceArtifactResponse(ReadApiBaseModel):
    source_artifact_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    source_system: str
    source_layout_name: str | None
    source_layout_version: str | None
    original_filename: str
    storage_uri: str
    mime_type: str | None
    file_size_bytes: int | None
    content_hash: str
    received_at: datetime
    idempotency_key: str | None
    metadata: dict[str, Any]


# -------------------------- wrapper_definition --------------------------


class RegisterWrapperDefinitionRequest(WriteApiBaseModel):
    wrapper_name: str = Field(min_length=1, max_length=128)
    wrapper_version: str = Field(min_length=1, max_length=64)
    source_layout_name: str = Field(min_length=1, max_length=128)
    source_layout_version: str | None = None
    schema_version: str | None = None
    code_hash: str | None = None
    wrapper_code_hash: str | None = None
    input_schema_hash: str | None = None
    output_schema_hash: str | None = None


class WrapperDefinitionResponse(ReadApiBaseModel):
    wrapper_definition_id: UUID
    wrapper_name: str
    wrapper_version: str
    source_layout_name: str
    source_layout_version: str | None
    schema_version: str | None
    code_hash: str | None
    wrapper_code_hash: str | None = None
    input_schema_hash: str | None = None
    output_schema_hash: str | None = None
    is_active: bool
    created_at: datetime
    metadata: dict[str, Any]


# -------------------------- wrapper_execution --------------------------


class RegisterWrapperExecutionRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    wrapper_definition_id: UUID
    input_artifact_id: UUID
    started_at: datetime
    execution_status: WrapperExecutionStatus = WrapperExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    execution_log_uri: str | None = None
    executor_agent_external_reference: str | None = None
    executor_agent_name: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)
    input_source_artifact_revision_id: UUID | None = None
    execution_payload_hash: str | None = None
    runtime_version: str | None = None


class WrapperExecutionResponse(ReadApiBaseModel):
    wrapper_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    wrapper_definition_id: UUID
    input_artifact_id: UUID
    execution_status: WrapperExecutionStatus
    started_at: datetime
    finished_at: datetime | None
    warning_count: int
    error_count: int
    execution_log_uri: str | None
    idempotency_key: str | None
    input_source_artifact_revision_id: UUID | None = None
    execution_payload_hash: str | None = None
    runtime_version: str | None = None
    metadata: dict[str, Any]


class SourceArtifactRevisionResponse(ReadApiBaseModel):
    source_artifact_revision_id: UUID
    source_artifact_id: UUID
    revision_number: int
    storage_uri: str
    content_hash: str
    mime_type: str | None
    file_size_bytes: int | None
    received_at: datetime
    is_current: bool
    prov_entity_id: UUID | None
    metadata: dict[str, Any]


# -------------------------- normalized_batch --------------------------


class RegisterNormalizedBatchRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    wrapper_execution_id: UUID
    batch_code: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=64)
    record_count: int = Field(ge=0)
    generated_at: datetime | None = None
    storage_uri: str | None = None
    content_hash: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)


class NormalizedBatchResponse(ReadApiBaseModel):
    normalized_batch_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    wrapper_execution_id: UUID
    batch_code: str
    schema_version: str
    record_count: int
    storage_uri: str | None
    content_hash: str | None
    generated_at: datetime
    idempotency_key: str | None
    metadata: dict[str, Any]


class CanonicalSnapshotItemTrace(ReadApiBaseModel):
    canonical_snapshot_item_id: UUID
    canonical_snapshot_id: UUID
    item_key: str
    item_hash: str | None
    payload: dict[str, Any]


class CanonicalSnapshotTraceResponse(ReadApiBaseModel):
    snapshot: CanonicalSnapshotResponse
    items: list[CanonicalSnapshotItemTrace]


class PipelineRunTraceResponse(ReadApiBaseModel):
    pipeline_run: PipelineRunResponse
    source_artifacts: list[SourceArtifactResponse]
    source_artifact_revisions: list[SourceArtifactRevisionResponse]
    wrapper_executions: list[WrapperExecutionResponse]
    normalized_batches: list[NormalizedBatchResponse]
    semantic_integration_executions: list[SemanticIntegrationExecutionResponse]
    canonical_snapshots: list[CanonicalSnapshotTraceResponse]
    ontology_resource_links: list[OntologyResourceLinkResponse]
    calculation_executions: list[CalculationExecutionResponse]
    calculation_parameter_sets: list[CalculationParameterSetResponse]
    calculation_method_versions: list[CalculationMethodVersionResponse]
    calculation_methods: list[CalculationMethodResponse]
    calculation_result_sets: list[CalculationResultSetResponse]
    calculation_reviews: list[CalculationReviewResponse]
    result_publication_executions: list[ResultPublicationExecutionResponse]
    hash_records: list[HashRecordResponse]
    prov_bundles: list[ProvBundleResponse]


class PipelineRunBundleGraphRow(ReadApiBaseModel):
    bundle_id: UUID
    graph: BundleGraphResponse


class PipelineRunGraphsResponse(ReadApiBaseModel):
    pipeline_run_id: UUID
    bundle_graphs: list[PipelineRunBundleGraphRow]
