from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class AnchorRequest:
    anchor_request_id: UUID
    source_event_id: str
    source_event_type: str
    pipeline_run_id: UUID | None
    calculation_result_set_id: UUID | None
    reporting_period_id: UUID | None
    request_scope: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


@dataclass(slots=True)
class EvidencePackage:
    evidence_package_id: UUID
    anchor_request_id: UUID
    package_type: str
    package_version: str
    period_start: str
    period_end: str
    period_granularity: str
    project_id_hash: str | None
    farm_id_hash: str | None
    management_unit_id_hash: str | None
    canonical_payload_json: str | None
    package_hash: str | None
    merkle_root: str | None
    metadata_hash: str | None
    public_summary_enabled: bool
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class EvidenceItem:
    evidence_item_id: UUID
    evidence_package_id: UUID
    item_order: int
    item_type: str
    source_table: str | None
    source_record_id: UUID | None
    source_event_id: str | None
    source_hash_value: str | None
    canonical_payload_json: str | None
    item_hash: str | None
    created_at: datetime


@dataclass(slots=True)
class HashRecord:
    hash_record_id: UUID
    subject_kind: str
    subject_id: UUID
    hash_algorithm: str
    canonicalization_method: str
    hash_value: str
    payload_ref: str | None
    created_at: datetime


@dataclass(slots=True)
class BlockchainNetwork:
    network_id: UUID
    network_code: str
    network_name: str
    provider_type: str
    chain_id: str | None
    is_active: bool
    created_at: datetime


@dataclass(slots=True)
class BlockchainTransaction:
    blockchain_transaction_id: UUID
    evidence_package_id: UUID
    network_id: UUID
    anchoring_mode: str
    anchoring_status: str
    transaction_hash: str | None
    block_number: int | None
    anchored_at: datetime | None
    request_payload_json: str | None
    response_payload_json: str | None
    created_at: datetime
    updated_at: datetime
    idempotency_key: str | None = None


@dataclass(slots=True)
class AnchoringAttempt:
    anchoring_attempt_id: UUID
    anchor_request_id: UUID
    evidence_package_id: UUID
    attempt_number: int
    status: str
    error_code: str | None
    error_message: str | None
    started_at: datetime
    ended_at: datetime | None


@dataclass(slots=True)
class VerificationLog:
    verification_log_id: UUID
    evidence_package_id: UUID
    verification_type: str
    expected_hash: str | None
    computed_hash: str | None
    is_valid: bool
    verified_at: datetime
    details_json: str | None


@dataclass(slots=True)
class AuditLogEntry:
    audit_log_id: UUID
    event_name: str
    entity_type: str
    entity_id: str
    correlation_id: str | None
    severity: str
    message: str
    context_json: str | None
    created_at: datetime
