"""HTTP DTOs for the ``audit`` bounded context."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from provenance_service.domain.shared.enums import (
    AnchorMode,
    BlockchainAnchorStatus,
    HashAlgorithm,
    HashScope,
    HashSubjectKind,
    OutboxStatus,
)
from provenance_service.interfaces.api.schemas.common import (
    ReadApiBaseModel,
    WriteApiBaseModel,
)


# ----------------- hash_record -----------------


class RegisterHashRecordRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    subject_kind: HashSubjectKind
    subject_id: UUID
    hash_value: str = Field(min_length=4, max_length=256)
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    prov_entity_id: UUID | None = None
    bundle_id: UUID | None = None
    computed_at: datetime | None = None
    computed_by_version: str | None = None


class HashRecordResponse(ReadApiBaseModel):
    hash_record_id: UUID
    pipeline_run_id: UUID
    prov_entity_id: UUID | None
    bundle_id: UUID | None
    subject_kind: HashSubjectKind
    subject_id: UUID
    hash_algorithm: HashAlgorithm
    hash_value: str
    computed_at: datetime
    computed_by_version: str | None
    hash_scope: HashScope | None = None
    canonicalization_method: str | None = None
    canonical_payload_hash: str | None = None
    canonical_payload_ref: str | None = None
    created_by_service: str | None = None
    record_created_at: datetime | None = Field(default=None, serialization_alias="created_at")
    metadata: dict[str, Any]


# ----------------- blockchain_anchor -----------------


class RegisterBlockchainAnchorRequest(WriteApiBaseModel):
    pipeline_run_id: UUID
    hash_record_id: UUID
    blockchain_network: str = Field(min_length=1, max_length=64)
    anchor_status: BlockchainAnchorStatus = BlockchainAnchorStatus.PENDING
    chain_id: str | None = None
    transaction_hash: str | None = None
    block_number: str | None = None
    merkle_root: str | None = None
    confirmations: int | None = Field(default=None, ge=0)
    anchored_at: datetime | None = None
    verification_uri: str | None = None
    anchor_provider: str | None = None
    anchor_mode: AnchorMode | None = None
    evidence_package_external_id: str | None = None
    package_hash: str | None = None
    metadata_hash: str | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    failed_reason: str | None = None


class BlockchainAnchorResponse(ReadApiBaseModel):
    blockchain_anchor_id: UUID
    pipeline_run_id: UUID
    hash_record_id: UUID
    blockchain_network: str
    chain_id: str | None
    transaction_hash: str | None
    block_number: str | None
    anchor_status: BlockchainAnchorStatus
    merkle_root: str | None
    confirmations: int | None
    anchored_at: datetime | None
    verification_uri: str | None
    anchor_provider: str | None = None
    anchor_mode: AnchorMode | None = None
    evidence_package_external_id: str | None = None
    package_hash: str | None = None
    metadata_hash: str | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    failed_reason: str | None = None
    metadata: dict[str, Any]


# ----------------- audit verify -----------------


class HashCheckResultResponse(ReadApiBaseModel):
    subject_kind: str
    subject_id: UUID
    expected_hash: str
    actual_hash: str | None
    matches: bool
    verification_mode: str
    mirror_hash: str | None = None
    detail: str | None = None


class IntegrityReportResponse(ReadApiBaseModel):
    bundle_id: UUID
    pipeline_run_id: UUID
    is_valid: bool
    checks: list[HashCheckResultResponse]
    missing_subjects: list[UUID]
    unsupported_subjects: list[UUID] = []


class OutboxEventResponse(ReadApiBaseModel):
    outbox_event_id: UUID
    aggregate_kind: str
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    published_at: datetime | None = None
    processed_at: datetime | None = None
    status: OutboxStatus
    pipeline_run_id: UUID | None = None
    calculation_execution_id: UUID | None = None
    calculation_result_set_id: UUID | None = None
    reporting_period_id: UUID | None = None
    source_table: str | None = None
    source_record_id: UUID | None = None
    error_message: str | None = None
    retry_count: int = 0
    locked_at: datetime | None = None
    locked_by: str | None = None


class OutboxEventListResponse(ReadApiBaseModel):
    items: list[OutboxEventResponse]
    total: int
    limit: int
    offset: int
