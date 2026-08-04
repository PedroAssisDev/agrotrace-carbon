"""HTTP DTOs for the ``calculation`` bounded context."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from provenance_service.domain.shared.enums import (
    AggregationType,
    CalculationExecutionStatus,
    CalculationMethodStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    ConsolidationType,
    ParameterSetStatus,
    ResultPublicationStatus,
    ResultScope,
)
from provenance_service.interfaces.api.schemas.common import (
    ApiBaseModel,
    ReadApiBaseModel,
    WriteApiBaseModel,
)


# ----------------- calculation_method -----------------


class RegisterCalculationMethodRequest(ApiBaseModel):
    method_code: str = Field(min_length=1, max_length=128)
    method_name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CalculationMethodResponse(ReadApiBaseModel):
    calculation_method_id: UUID
    method_code: str
    method_name: str
    description: str | None
    created_at: datetime


# ----------------- calculation_method_version -----------------


class RegisterCalculationMethodVersionRequest(WriteApiBaseModel):
    calculation_method_id: UUID
    version_label: str = Field(min_length=1, max_length=64)
    status: CalculationMethodStatus = CalculationMethodStatus.ACTIVE
    formula_reference: str | None = None
    implementation_version: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    formula_hash: str | None = None
    method_document_uri: str | None = None
    method_document_hash: str | None = None


class CalculationMethodVersionResponse(ReadApiBaseModel):
    calculation_method_version_id: UUID
    calculation_method_id: UUID
    version_label: str
    formula_reference: str | None
    implementation_version: str | None
    effective_from: datetime | None
    effective_to: datetime | None
    status: CalculationMethodStatus
    formula_hash: str | None = None
    method_document_uri: str | None = None
    method_document_hash: str | None = None
    metadata: dict[str, Any]


# ----------------- calculation_parameter_set -----------------


class ParameterValueInputDto(WriteApiBaseModel):
    parameter_name: str = Field(min_length=1, max_length=255)
    parameter_value_text: str | None = None
    parameter_value_numeric: Decimal | None = None
    parameter_unit: str | None = None
    parameter_source: str | None = None
    is_user_editable: bool = False


class RegisterCalculationParameterSetRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    calculation_method_version_id: UUID
    values: list[ParameterValueInputDto] = Field(min_length=1)
    parameter_set_status: ParameterSetStatus = ParameterSetStatus.LOCKED
    created_by_agent_id: UUID | None = None
    notes: str | None = None


class CalculationParameterSetResponse(ReadApiBaseModel):
    calculation_parameter_set_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    calculation_method_version_id: UUID
    parameter_set_status: ParameterSetStatus
    created_by_agent_id: UUID | None
    created_at: datetime
    notes: str | None
    metadata: dict[str, Any]


# ----------------- calculation_execution -----------------


class RegisterCalculationExecutionRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    canonical_snapshot_id: UUID
    calculation_method_version_id: UUID
    calculation_parameter_set_id: UUID
    started_at: datetime
    execution_status: CalculationExecutionStatus = CalculationExecutionStatus.SUCCEEDED
    finished_at: datetime | None = None
    execution_log_uri: str | None = None
    executor_agent_external_reference: str | None = None
    executor_agent_name: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=128)
    reporting_period_id: UUID | None = None


class CalculationExecutionResponse(ReadApiBaseModel):
    calculation_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    canonical_snapshot_id: UUID
    calculation_method_version_id: UUID
    calculation_parameter_set_id: UUID
    execution_status: CalculationExecutionStatus
    started_at: datetime
    finished_at: datetime | None
    execution_log_uri: str | None
    idempotency_key: str | None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any]


# ----------------- calculation_result_set -----------------


class ResultItemInputDto(WriteApiBaseModel):
    result_type: CalculationResultType
    result_name: str = Field(min_length=1, max_length=255)
    result_value: Decimal
    result_unit: str = Field(min_length=1, max_length=64)
    dimension_reference: str | None = None


class RegisterCalculationResultSetRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    calculation_execution_id: UUID
    items: list[ResultItemInputDto] = Field(min_length=1)
    generated_at: datetime | None = None
    result_set_status: CalculationResultSetStatus = CalculationResultSetStatus.PRELIMINARY
    reporting_period_id: UUID | None = None
    result_scope: ResultScope | None = None
    consolidation_type: ConsolidationType | None = None
    supersedes_id: UUID | None = None
    correction_reason: str | None = None


class CalculationResultItemResponse(ReadApiBaseModel):
    calculation_result_item_id: UUID
    calculation_result_set_id: UUID
    result_type: CalculationResultType
    result_name: str
    result_value: Decimal
    result_unit: str
    dimension_reference: str | None
    metadata: dict[str, Any]


class CalculationResultSetResponse(ReadApiBaseModel):
    calculation_result_set_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    calculation_execution_id: UUID
    result_set_status: CalculationResultSetStatus
    generated_at: datetime
    summary_hash: str | None
    superseded_by_id: UUID | None
    reporting_period_id: UUID | None = None
    result_scope: ResultScope | None = None
    consolidation_type: ConsolidationType | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None
    supersedes_id: UUID | None = None
    correction_reason: str | None = None
    metadata: dict[str, Any]
    items: list[CalculationResultItemResponse] = Field(default_factory=list)


# ----------------- calculation_review -----------------


class RegisterCalculationReviewRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    calculation_result_set_id: UUID
    reviewer_agent_id: UUID
    decision: CalculationReviewDecision
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    evidence_uri: str | None = None
    reporting_period_id: UUID | None = None


class CalculationReviewResponse(ReadApiBaseModel):
    calculation_review_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    calculation_result_set_id: UUID
    reviewer_agent_id: UUID
    decision: CalculationReviewDecision
    review_comment: str | None
    reviewed_at: datetime
    evidence_uri: str | None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any]


# ----------------- result_publication -----------------


class RegisterResultPublicationRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    calculation_result_set_id: UUID
    target_graph_name: str = Field(min_length=1, max_length=255)
    ontology_name: str = Field(min_length=1, max_length=128)
    ontology_version: str = Field(min_length=1, max_length=64)
    publication_status: ResultPublicationStatus = ResultPublicationStatus.PUBLISHED
    calculation_review_id: UUID | None = None
    published_at: datetime | None = None
    publisher_agent_external_reference: str | None = None
    publisher_agent_name: str | None = None
    create_ontology_resource_link: bool = True
    ontology_uri: str | None = None
    rdf_class: str | None = None
    reporting_period_id: UUID | None = None
    publication_payload_hash: str | None = None
    ontology_resource_uri: str | None = None
    publication_version: str | None = None


class ResultPublicationExecutionResponse(ReadApiBaseModel):
    result_publication_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    calculation_result_set_id: UUID
    calculation_review_id: UUID | None
    target_graph_name: str
    ontology_name: str
    ontology_version: str
    publication_status: ResultPublicationStatus
    published_at: datetime | None
    reporting_period_id: UUID | None = None
    publication_payload_hash: str | None = None
    ontology_resource_uri: str | None = None
    publication_version: str | None = None
    metadata: dict[str, Any]


# ----------------- result_aggregation_link -----------------


class RegisterResultAggregationLinkRequest(WriteApiBaseModel):
    parent_result_set_id: UUID
    child_result_set_id: UUID
    aggregation_type: AggregationType
    parent_period_id: UUID | None = None
    child_period_id: UUID | None = None


class CalculationResultAggregationLinkResponse(ReadApiBaseModel):
    calculation_result_aggregation_link_id: UUID
    parent_result_set_id: UUID
    child_result_set_id: UUID
    aggregation_type: AggregationType
    parent_period_id: UUID | None = None
    child_period_id: UUID | None = None
    created_at: datetime
    metadata: dict[str, Any]


class CalculationResultAggregationLinkListResponse(ReadApiBaseModel):
    items: list[CalculationResultAggregationLinkResponse]
