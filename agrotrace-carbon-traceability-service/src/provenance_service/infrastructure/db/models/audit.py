"""Audit bounded-context tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
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
    ANCHOR_MODE_T,
    BLOCKCHAIN_ANCHOR_STATUS_T,
    HASH_ALGORITHM_T,
    HASH_SCOPE_T,
    HASH_SUBJECT_KIND_T,
    OUTBOX_STATUS_T,
    Base,
    UUID_T,
)


def _aud(name: str) -> str:
    return f"audit_{name}"


def _pl(name: str) -> str:
    return f"pipeline_{name}"


def _pc(name: str) -> str:
    return f"prov_core_{name}"


def _rep(name: str) -> str:
    return f"reporting_{name}"


class HashRecordModel(Base):
    __tablename__ = _aud("hash_record")
    __table_args__ = (
        UniqueConstraint(
            "subject_kind",
            "subject_id",
            "hash_algorithm",
            name="uq_hash_record_subject_kind_subject_id_hash_algorithm",
        ),
        Index("ix_hash_record_pipeline_run_id", "pipeline_run_id"),
        Index("ix_hash_record_subject_id", "subject_id"),
        Index("ix_hash_record_hash_value", "hash_value"),
    )

    hash_record_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_hash_record_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_hash_record_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    bundle_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_bundle')}.bundle_id",
            name="fk_hash_record_bundle_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    subject_kind: Mapped[str] = mapped_column(HASH_SUBJECT_KIND_T, nullable=False)
    subject_id: Mapped[UUID] = mapped_column(UUID_T, nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(HASH_ALGORITHM_T, nullable=False)
    hash_value: Mapped[str] = mapped_column(String(128), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    computed_by_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash_scope: Mapped[str | None] = mapped_column(HASH_SCOPE_T, nullable=True)
    canonicalization_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    canonical_payload_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    record_created_at: Mapped[datetime | None] = mapped_column(
        "created_at", DateTime(timezone=True), nullable=True
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class BlockchainAnchorModel(Base):
    __tablename__ = _aud("blockchain_anchor")
    __table_args__ = (
        Index("ix_blockchain_anchor_pipeline_run_id", "pipeline_run_id"),
        Index("ix_blockchain_anchor_hash_record_id", "hash_record_id"),
        Index("ix_blockchain_anchor_status", "anchor_status"),
    )

    blockchain_anchor_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_blockchain_anchor_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    hash_record_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_aud('hash_record')}.hash_record_id",
            name="fk_blockchain_anchor_hash_record_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    blockchain_network: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    block_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor_status: Mapped[str] = mapped_column(BLOCKCHAIN_ANCHOR_STATUS_T, nullable=False)
    merkle_root: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confirmations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    anchor_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor_mode: Mapped[str | None] = mapped_column(ANCHOR_MODE_T, nullable=True)
    evidence_package_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    package_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class OutboxEventModel(Base):
    __tablename__ = _aud("outbox_event")
    __table_args__ = (
        Index("ix_outbox_event_status_created_at", "status", "created_at"),
        Index("ix_outbox_event_aggregate", "aggregate_kind", "aggregate_id"),
        Index("ix_outbox_event_pipeline_run_id", "pipeline_run_id"),
        Index("ix_outbox_event_event_type", "event_type"),
    )

    outbox_event_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    aggregate_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(UUID_T, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(OUTBOX_STATUS_T, nullable=False)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_outbox_event_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    calculation_execution_id: Mapped[UUID | None] = mapped_column(UUID_T, nullable=True)
    calculation_result_set_id: Mapped[UUID | None] = mapped_column(UUID_T, nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_outbox_event_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    source_table: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_record_id: Mapped[UUID | None] = mapped_column(UUID_T, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AuditEventModel(Base):
    __tablename__ = _aud("audit_event")
    __table_args__ = (
        Index("ix_audit_event_subject", "subject_kind", "subject_id"),
        Index("ix_audit_event_recorded_at", "recorded_at"),
    )

    audit_event_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_agent_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_audit_event_actor_agent_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    subject_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(UUID_T, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
