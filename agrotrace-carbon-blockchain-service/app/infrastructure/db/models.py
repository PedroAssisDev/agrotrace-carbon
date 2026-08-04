from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ObserverStateModel(Base):
    __tablename__ = "observer_state"

    state_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnchorRequestModel(Base):
    __tablename__ = "anchor_request"

    anchor_request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(36))
    calculation_result_set_id: Mapped[str | None] = mapped_column(String(36))
    reporting_period_id: Mapped[str | None] = mapped_column(String(36))
    request_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class EvidencePackageModel(Base):
    __tablename__ = "evidence_package"

    evidence_package_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    anchor_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("anchor_request.anchor_request_id"), nullable=False
    )
    package_type: Mapped[str] = mapped_column(String(64), nullable=False)
    package_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0.0")
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    period_granularity: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id_hash: Mapped[str | None] = mapped_column(String(128))
    farm_id_hash: Mapped[str | None] = mapped_column(String(128))
    management_unit_id_hash: Mapped[str | None] = mapped_column(String(128))
    canonical_payload_json: Mapped[str | None] = mapped_column(Text)
    package_hash: Mapped[str | None] = mapped_column(String(128))
    merkle_root: Mapped[str | None] = mapped_column(String(128))
    metadata_hash: Mapped[str | None] = mapped_column(String(128))
    public_summary_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceItemModel(Base):
    __tablename__ = "evidence_item"

    evidence_item_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_package.evidence_package_id"), nullable=False
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_table: Mapped[str | None] = mapped_column(String(128))
    source_record_id: Mapped[str | None] = mapped_column(String(36))
    source_event_id: Mapped[str | None] = mapped_column(String(64))
    source_hash_value: Mapped[str | None] = mapped_column(String(128))
    canonical_payload_json: Mapped[str | None] = mapped_column(Text)
    item_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HashRecordModel(Base):
    __tablename__ = "hash_record"

    hash_record_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(String(16), nullable=False)
    canonicalization_method: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_value: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_ref: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BlockchainNetworkModel(Base):
    __tablename__ = "blockchain_network"

    network_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    network_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    network_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_id: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BlockchainTransactionModel(Base):
    __tablename__ = "blockchain_transaction"

    blockchain_transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_package.evidence_package_id"), nullable=False
    )
    network_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("blockchain_network.network_id"), nullable=False
    )
    anchoring_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    anchoring_status: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_hash: Mapped[str | None] = mapped_column(String(128))
    block_number: Mapped[int | None] = mapped_column(Integer)
    anchored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_payload_json: Mapped[str | None] = mapped_column(Text)
    response_payload_json: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnchoringAttemptModel(Base):
    __tablename__ = "anchoring_attempt"

    anchoring_attempt_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    anchor_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("anchor_request.anchor_request_id"), nullable=False
    )
    evidence_package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_package.evidence_package_id"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationLogModel(Base):
    __tablename__ = "verification_log"

    verification_log_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_package.evidence_package_id"), nullable=False
    )
    verification_type: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_hash: Mapped[str | None] = mapped_column(String(128))
    computed_hash: Mapped[str | None] = mapped_column(String(128))
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text)


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    audit_log_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
