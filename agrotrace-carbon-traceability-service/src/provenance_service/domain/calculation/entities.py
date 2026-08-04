"""Calculation-context aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import (
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


@dataclass(slots=True)
class CalculationMethod:
    calculation_method_id: UUID
    method_code: str
    method_name: str
    created_at: datetime
    description: str | None = None


@dataclass(slots=True)
class CalculationMethodVersion:
    calculation_method_version_id: UUID
    calculation_method_id: UUID
    version_label: str
    status: CalculationMethodStatus
    formula_reference: str | None = None
    formula_hash: str | None = None
    method_document_uri: str | None = None
    method_document_hash: str | None = None
    implementation_version: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationParameterSet:
    calculation_parameter_set_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    calculation_method_version_id: UUID
    parameter_set_status: ParameterSetStatus
    created_at: datetime
    created_by_agent_id: UUID | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationParameterValue:
    calculation_parameter_value_id: UUID
    calculation_parameter_set_id: UUID
    parameter_name: str
    parameter_value_text: str | None = None
    parameter_value_numeric: Decimal | None = None
    parameter_unit: str | None = None
    parameter_source: str | None = None
    is_user_editable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationExecution:
    calculation_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    canonical_snapshot_id: UUID
    calculation_method_version_id: UUID
    calculation_parameter_set_id: UUID
    execution_status: CalculationExecutionStatus
    started_at: datetime
    finished_at: datetime | None = None
    execution_log_uri: str | None = None
    idempotency_key: str | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationResultSet:
    calculation_result_set_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID
    calculation_execution_id: UUID
    result_set_status: CalculationResultSetStatus
    generated_at: datetime
    summary_hash: str | None = None
    superseded_by_id: UUID | None = None
    reporting_period_id: UUID | None = None
    result_scope: ResultScope | None = None
    consolidation_type: ConsolidationType | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None
    supersedes_id: UUID | None = None
    correction_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationResultItem:
    calculation_result_item_id: UUID
    calculation_result_set_id: UUID
    result_type: CalculationResultType
    result_name: str
    result_value: Decimal
    result_unit: str
    dimension_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationReview:
    calculation_review_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    calculation_result_set_id: UUID
    reviewer_agent_id: UUID
    decision: CalculationReviewDecision
    reviewed_at: datetime
    review_comment: str | None = None
    evidence_uri: str | None = None
    reporting_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResultPublicationExecution:
    result_publication_execution_id: UUID
    pipeline_run_id: UUID
    prov_activity_id: UUID
    calculation_result_set_id: UUID
    target_graph_name: str
    ontology_name: str
    ontology_version: str
    publication_status: ResultPublicationStatus
    calculation_review_id: UUID | None = None
    published_at: datetime | None = None
    reporting_period_id: UUID | None = None
    publication_payload_hash: str | None = None
    ontology_resource_uri: str | None = None
    publication_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalculationResultAggregationLink:
    calculation_result_aggregation_link_id: UUID
    parent_result_set_id: UUID
    child_result_set_id: UUID
    aggregation_type: str
    created_at: datetime
    parent_period_id: UUID | None = None
    child_period_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
