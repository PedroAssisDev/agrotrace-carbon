"""Declarative base + shared SQL types and naming conventions.

SQLite-compatible types: JSON, Uuid, Enum as VARCHAR (``native_enum=False``).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, MetaData, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase

from provenance_service.domain.shared.enums import (
    AggregationType,
    AnchorMode,
    BlockchainAnchorStatus,
    CalculationExecutionStatus,
    CalculationMethodStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    ConsolidationType,
    HashAlgorithm,
    HashScope,
    HashSubjectKind,
    OutboxStatus,
    ParameterSetStatus,
    PeriodGranularity,
    PipelineRunStatus,
    ProvActivityType,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
    PublicationStage,
    ReportingPeriodStatus,
    ResultPublicationStatus,
    ResultScope,
    RunType,
    SemanticExecutionStatus,
    WrapperExecutionStatus,
)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata
    type_annotation_map: dict[type, Any] = {dict[str, Any]: JSON}


def _str_enum(enum_cls: type, name: str) -> SAEnum:
    """Persist enum members as plain strings (SQLite-friendly)."""

    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=False,
        validate_strings=True,
        values_callable=lambda c: [e.value for e in c],
    )


PIPELINE_RUN_STATUS_T = _str_enum(PipelineRunStatus, "pipeline_run_status")
WRAPPER_EXECUTION_STATUS_T = _str_enum(WrapperExecutionStatus, "wrapper_execution_status")
PROV_BUNDLE_TYPE_T = _str_enum(ProvBundleType, "prov_bundle_type")
PROV_BUNDLE_STATUS_T = _str_enum(ProvBundleStatus, "prov_bundle_status")
PROV_ENTITY_TYPE_T = _str_enum(ProvEntityType, "prov_entity_type")
PROV_ACTIVITY_TYPE_T = _str_enum(ProvActivityType, "prov_activity_type")
PROV_AGENT_TYPE_T = _str_enum(ProvAgentType, "prov_agent_type")
SEMANTIC_EXECUTION_STATUS_T = _str_enum(SemanticExecutionStatus, "semantic_execution_status")
PUBLICATION_STAGE_T = _str_enum(PublicationStage, "publication_stage")
CALCULATION_METHOD_STATUS_T = _str_enum(CalculationMethodStatus, "calculation_method_status")
PARAMETER_SET_STATUS_T = _str_enum(ParameterSetStatus, "parameter_set_status")
CALCULATION_EXECUTION_STATUS_T = _str_enum(
    CalculationExecutionStatus, "calculation_execution_status"
)
CALCULATION_RESULT_SET_STATUS_T = _str_enum(
    CalculationResultSetStatus, "calculation_result_set_status"
)
CALCULATION_RESULT_TYPE_T = _str_enum(CalculationResultType, "calculation_result_type")
CALCULATION_REVIEW_DECISION_T = _str_enum(
    CalculationReviewDecision, "calculation_review_decision"
)
RESULT_PUBLICATION_STATUS_T = _str_enum(
    ResultPublicationStatus, "result_publication_status"
)
HASH_ALGORITHM_T = _str_enum(HashAlgorithm, "hash_algorithm")
HASH_SUBJECT_KIND_T = _str_enum(HashSubjectKind, "hash_subject_kind")
BLOCKCHAIN_ANCHOR_STATUS_T = _str_enum(BlockchainAnchorStatus, "blockchain_anchor_status")
OUTBOX_STATUS_T = _str_enum(OutboxStatus, "outbox_status")
PERIOD_GRANULARITY_T = _str_enum(PeriodGranularity, "period_granularity")
REPORTING_PERIOD_STATUS_T = _str_enum(ReportingPeriodStatus, "reporting_period_status")
RESULT_SCOPE_T = _str_enum(ResultScope, "result_scope")
CONSOLIDATION_TYPE_T = _str_enum(ConsolidationType, "consolidation_type")
AGGREGATION_TYPE_T = _str_enum(AggregationType, "aggregation_type")
HASH_SCOPE_T = _str_enum(HashScope, "hash_scope")
RUN_TYPE_T = _str_enum(RunType, "run_type")
ANCHOR_MODE_T = _str_enum(AnchorMode, "anchor_mode")

# Portable UUID column type (works with SQLite and PostgreSQL).
UUID_T = Uuid(as_uuid=True)
