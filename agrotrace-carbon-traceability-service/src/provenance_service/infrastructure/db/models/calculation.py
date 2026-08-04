"""Calculation bounded-context tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from provenance_service.infrastructure.db.models.base import (
    AGGREGATION_TYPE_T,
    CALCULATION_EXECUTION_STATUS_T,
    CALCULATION_METHOD_STATUS_T,
    CALCULATION_RESULT_SET_STATUS_T,
    CALCULATION_RESULT_TYPE_T,
    CALCULATION_REVIEW_DECISION_T,
    CONSOLIDATION_TYPE_T,
    PARAMETER_SET_STATUS_T,
    RESULT_PUBLICATION_STATUS_T,
    RESULT_SCOPE_T,
    Base,
    UUID_T,
)


def _calc(name: str) -> str:
    return f"calculation_{name}"


def _pl(name: str) -> str:
    return f"pipeline_{name}"


def _pc(name: str) -> str:
    return f"prov_core_{name}"


def _sem(name: str) -> str:
    return f"semantic_{name}"


def _rep(name: str) -> str:
    return f"reporting_{name}"


class CalculationMethodModel(Base):
    __tablename__ = _calc("calculation_method")
    __table_args__ = (UniqueConstraint("method_code", name="uq_calculation_method_method_code"),)

    calculation_method_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    method_code: Mapped[str] = mapped_column(String(64), nullable=False)
    method_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CalculationMethodVersionModel(Base):
    __tablename__ = _calc("calculation_method_version")
    __table_args__ = (
        UniqueConstraint(
            "calculation_method_id",
            "version_label",
            name="uq_calculation_method_version_calculation_method_id_version_label",
        ),
        Index(
            "ix_calculation_method_version_calculation_method_id",
            "calculation_method_id",
        ),
    )

    calculation_method_version_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    calculation_method_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_method')}.calculation_method_id",
            name="fk_calculation_method_version_calculation_method_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    formula_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    method_document_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    method_document_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    implementation_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(CALCULATION_METHOD_STATUS_T, nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationParameterSetModel(Base):
    __tablename__ = _calc("calculation_parameter_set")
    __table_args__ = (
        UniqueConstraint("prov_entity_id", name="uq_calculation_parameter_set_prov_entity_id"),
        Index("ix_calculation_parameter_set_pipeline_run_id", "pipeline_run_id"),
        Index(
            "ix_calculation_parameter_set_method_version_id",
            "calculation_method_version_id",
        ),
    )

    calculation_parameter_set_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_calculation_parameter_set_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_calculation_parameter_set_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_method_version_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_method_version')}.calculation_method_version_id",
            name="fk_calculation_parameter_set_calculation_method_version_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    parameter_set_status: Mapped[str] = mapped_column(PARAMETER_SET_STATUS_T, nullable=False)
    created_by_agent_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_calculation_parameter_set_created_by_agent_id",
            use_alter=True,
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationParameterValueModel(Base):
    __tablename__ = _calc("calculation_parameter_value")
    __table_args__ = (
        Index(
            "ix_calculation_parameter_value_calculation_parameter_set_id",
            "calculation_parameter_set_id",
        ),
        Index("ix_calculation_parameter_value_parameter_name", "parameter_name"),
    )

    calculation_parameter_value_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    calculation_parameter_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_parameter_set')}.calculation_parameter_set_id",
            name="fk_calculation_parameter_value_calculation_parameter_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    parameter_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parameter_value_text: Mapped[str | None] = mapped_column(String, nullable=True)
    parameter_value_numeric: Mapped[Decimal | None] = mapped_column(
        Numeric(38, 12), nullable=True
    )
    parameter_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameter_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_user_editable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationExecutionModel(Base):
    __tablename__ = _calc("calculation_execution")
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_calculation_execution_idempotency_key"),
        UniqueConstraint("prov_activity_id", name="uq_calculation_execution_prov_activity_id"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_calculation_execution_finished_at_ge_started_at",
        ),
        Index("ix_calculation_execution_pipeline_run_id", "pipeline_run_id"),
        Index("ix_calculation_execution_canonical_snapshot_id", "canonical_snapshot_id"),
    )

    calculation_execution_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_calculation_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_calculation_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    canonical_snapshot_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_sem('canonical_snapshot')}.canonical_snapshot_id",
            name="fk_calculation_execution_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_method_version_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_method_version')}.calculation_method_version_id",
            name="fk_calculation_execution_calculation_method_version_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_parameter_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_parameter_set')}.calculation_parameter_set_id",
            name="fk_calculation_execution_calculation_parameter_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    execution_status: Mapped[str] = mapped_column(
        CALCULATION_EXECUTION_STATUS_T, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_log_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_calculation_execution_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationResultSetModel(Base):
    __tablename__ = _calc("calculation_result_set")
    __table_args__ = (
        UniqueConstraint("prov_entity_id", name="uq_calculation_result_set_prov_entity_id"),
        Index("ix_calculation_result_set_pipeline_run_id", "pipeline_run_id"),
        Index(
            "ix_calculation_result_set_calculation_execution_id", "calculation_execution_id"
        ),
    )

    calculation_result_set_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_calculation_result_set_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_calculation_result_set_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_execution_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_execution')}.calculation_execution_id",
            name="fk_calculation_result_set_calculation_execution_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    result_set_status: Mapped[str] = mapped_column(
        CALCULATION_RESULT_SET_STATUS_T, nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_calculation_result_set_superseded_by_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_calculation_result_set_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    result_scope: Mapped[str | None] = mapped_column(RESULT_SCOPE_T, nullable=True)
    consolidation_type: Mapped[str | None] = mapped_column(CONSOLIDATION_TYPE_T, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_calculation_result_set_supersedes_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    correction_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationResultItemModel(Base):
    __tablename__ = _calc("calculation_result_item")
    __table_args__ = (
        Index(
            "ix_calculation_result_item_calculation_result_set_id",
            "calculation_result_set_id",
        ),
        Index("ix_calculation_result_item_result_type", "result_type"),
    )

    calculation_result_item_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    calculation_result_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_calculation_result_item_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    result_type: Mapped[str] = mapped_column(CALCULATION_RESULT_TYPE_T, nullable=False)
    result_name: Mapped[str] = mapped_column(String(256), nullable=False)
    result_value: Mapped[Decimal] = mapped_column(Numeric(38, 12), nullable=False)
    result_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationReviewModel(Base):
    __tablename__ = _calc("calculation_review")
    __table_args__ = (
        UniqueConstraint("prov_activity_id", name="uq_calculation_review_prov_activity_id"),
        Index("ix_calculation_review_pipeline_run_id", "pipeline_run_id"),
        Index(
            "ix_calculation_review_calculation_result_set_id", "calculation_result_set_id"
        ),
    )

    calculation_review_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_calculation_review_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_calculation_review_prov_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_result_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_calculation_review_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    reviewer_agent_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_calculation_review_reviewer_agent_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(CALCULATION_REVIEW_DECISION_T, nullable=False)
    review_comment: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_calculation_review_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ResultPublicationExecutionModel(Base):
    __tablename__ = _calc("result_publication_execution")
    __table_args__ = (
        UniqueConstraint(
            "prov_activity_id", name="uq_result_publication_execution_prov_activity_id"
        ),
        Index("ix_result_publication_execution_pipeline_run_id", "pipeline_run_id"),
    )

    result_publication_execution_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_result_publication_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_result_publication_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_result_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_result_publication_execution_calculation_result_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    calculation_review_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_review')}.calculation_review_id",
            name="fk_result_publication_execution_calculation_review_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    target_graph_name: Mapped[str] = mapped_column(String(256), nullable=False)
    ontology_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ontology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_status: Mapped[str] = mapped_column(
        RESULT_PUBLICATION_STATUS_T, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_result_publication_execution_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    publication_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ontology_resource_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    publication_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CalculationResultAggregationLinkModel(Base):
    __tablename__ = _calc("result_aggregation_link")
    __table_args__ = (
        Index(
            "ix_calculation_result_aggregation_link_parent",
            "parent_result_set_id",
        ),
        Index(
            "ix_calculation_result_aggregation_link_child",
            "child_result_set_id",
        ),
    )

    calculation_result_aggregation_link_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    parent_result_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_result_aggregation_link_parent_result_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    child_result_set_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_calc('calculation_result_set')}.calculation_result_set_id",
            name="fk_result_aggregation_link_child_result_set_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    aggregation_type: Mapped[str] = mapped_column(AGGREGATION_TYPE_T, nullable=False)
    parent_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_result_aggregation_link_parent_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    child_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_result_aggregation_link_child_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, server_default=text("'{}'")
    )
