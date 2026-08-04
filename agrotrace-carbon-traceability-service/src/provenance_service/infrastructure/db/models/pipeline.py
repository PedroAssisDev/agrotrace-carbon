"""Pipeline bounded-context tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from provenance_service.infrastructure.db.models.base import (
    PIPELINE_RUN_STATUS_T,
    RUN_TYPE_T,
    WRAPPER_EXECUTION_STATUS_T,
    Base,
    UUID_T,
)


def _pl(name: str) -> str:
    return f"pipeline_{name}"


def _pc(name: str) -> str:
    return f"prov_core_{name}"


def _rep(name: str) -> str:
    return f"reporting_{name}"


class PipelineRunModel(Base):
    __tablename__ = _pl("pipeline_run")
    __table_args__ = (
        UniqueConstraint("run_code", name="uq_pipeline_run_run_code"),
        UniqueConstraint("idempotency_key", name="uq_pipeline_run_idempotency_key"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_pipeline_run_finished_at_ge_started_at",
        ),
        Index("ix_pipeline_run_farm_period", "farm_reference", "reporting_period_reference"),
        Index("ix_pipeline_run_status_started_at", "run_status", "started_at"),
    )

    pipeline_run_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    run_code: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[UUID | None] = mapped_column(UUID_T, nullable=True)
    farm_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    reporting_period_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    run_status: Mapped[str] = mapped_column(PIPELINE_RUN_STATUS_T, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parent_pipeline_run_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_pipeline_run_parent_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    triggered_by_agent_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_pipeline_run_triggered_by_agent_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    run_type: Mapped[str | None] = mapped_column(RUN_TYPE_T, nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_pipeline_run_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    farm_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    project_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        server_default=text("'{}'"),
    )


class SourceArtifactModel(Base):
    __tablename__ = _pl("source_artifact")
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_source_artifact_idempotency_key"),
        UniqueConstraint("prov_entity_id", name="uq_source_artifact_prov_entity_id"),
        Index("ix_source_artifact_pipeline_run_id", "pipeline_run_id"),
        Index("ix_source_artifact_content_hash", "content_hash"),
    )

    source_artifact_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_source_artifact_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_source_artifact_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_layout_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_layout_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class SourceArtifactRevisionModel(Base):
    __tablename__ = _pl("source_artifact_revision")
    __table_args__ = (
        UniqueConstraint(
            "source_artifact_id",
            "revision_number",
            name="uq_source_artifact_revision_artifact_revision_number",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_source_artifact_revision_revision_number_ge_1",
        ),
        Index("ix_source_artifact_revision_source_artifact_id", "source_artifact_id"),
        Index(
            "uq_source_artifact_revision_current_per_artifact",
            "source_artifact_id",
            unique=True,
            sqlite_where=text("is_current = 1"),
        ),
    )

    source_artifact_revision_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    source_artifact_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('source_artifact')}.source_artifact_id",
            name="fk_source_artifact_revision_source_artifact_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    prov_entity_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_source_artifact_revision_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class WrapperDefinitionModel(Base):
    __tablename__ = _pl("wrapper_definition")
    __table_args__ = (
        UniqueConstraint(
            "wrapper_name",
            "wrapper_version",
            name="uq_wrapper_definition_wrapper_name_wrapper_version",
        ),
        Index("ix_wrapper_definition_layout", "source_layout_name", "source_layout_version"),
    )

    wrapper_definition_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    wrapper_name: Mapped[str] = mapped_column(String(128), nullable=False)
    wrapper_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_layout_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_layout_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wrapper_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_schema_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_schema_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class WrapperExecutionModel(Base):
    __tablename__ = _pl("wrapper_execution")
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_wrapper_execution_idempotency_key"),
        UniqueConstraint("prov_activity_id", name="uq_wrapper_execution_prov_activity_id"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_wrapper_execution_finished_at_ge_started_at",
        ),
        CheckConstraint("warning_count >= 0", name="ck_wrapper_execution_warning_count_ge_0"),
        CheckConstraint("error_count >= 0", name="ck_wrapper_execution_error_count_ge_0"),
        Index("ix_wrapper_execution_pipeline_run_id", "pipeline_run_id"),
    )

    wrapper_execution_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_wrapper_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_wrapper_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    wrapper_definition_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('wrapper_definition')}.wrapper_definition_id",
            name="fk_wrapper_execution_wrapper_definition_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    input_artifact_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('source_artifact')}.source_artifact_id",
            name="fk_wrapper_execution_input_artifact_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    input_source_artifact_revision_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('source_artifact_revision')}.source_artifact_revision_id",
            name="fk_wrapper_execution_input_source_artifact_revision_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    execution_status: Mapped[str] = mapped_column(WRAPPER_EXECUTION_STATUS_T, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    execution_log_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class NormalizedBatchModel(Base):
    __tablename__ = _pl("normalized_batch")
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_normalized_batch_idempotency_key"),
        UniqueConstraint("prov_entity_id", name="uq_normalized_batch_prov_entity_id"),
        CheckConstraint("record_count >= 0", name="ck_normalized_batch_record_count_ge_0"),
        Index("ix_normalized_batch_pipeline_run_id", "pipeline_run_id"),
        Index("ix_normalized_batch_wrapper_execution_id", "wrapper_execution_id"),
    )

    normalized_batch_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_normalized_batch_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_normalized_batch_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    wrapper_execution_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('wrapper_execution')}.wrapper_execution_id",
            name="fk_normalized_batch_wrapper_execution_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    batch_code: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )
