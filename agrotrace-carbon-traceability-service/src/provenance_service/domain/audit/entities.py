"""Audit-context aggregates: hashes, blockchain anchors, outbox, audit events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import (
    BlockchainAnchorStatus,
    HashAlgorithm,
    HashSubjectKind,
    OutboxStatus,
)


@dataclass(slots=True)
class HashRecord:
    hash_record_id: UUID
    pipeline_run_id: UUID
    subject_kind: HashSubjectKind
    subject_id: UUID
    hash_algorithm: HashAlgorithm
    hash_value: str
    computed_at: datetime
    prov_entity_id: UUID | None = None
    bundle_id: UUID | None = None
    computed_by_version: str | None = None
    hash_scope: str | None = None
    canonicalization_method: str | None = None
    canonical_payload_hash: str | None = None
    canonical_payload_ref: str | None = None
    created_by_service: str | None = None
    record_created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BlockchainAnchor:
    blockchain_anchor_id: UUID
    pipeline_run_id: UUID
    hash_record_id: UUID
    blockchain_network: str
    anchor_status: BlockchainAnchorStatus
    chain_id: str | None = None
    transaction_hash: str | None = None
    block_number: str | None = None
    merkle_root: str | None = None
    confirmations: int | None = None
    anchored_at: datetime | None = None
    verification_uri: str | None = None
    anchor_provider: str | None = None
    anchor_mode: str | None = None
    evidence_package_external_id: str | None = None
    package_hash: str | None = None
    metadata_hash: str | None = None
    submitted_at: datetime | None = None
    confirmed_at: datetime | None = None
    failed_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OutboxEvent:
    outbox_event_id: UUID
    aggregate_kind: str
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    created_at: datetime
    status: OutboxStatus
    published_at: datetime | None = None
    processed_at: datetime | None = None
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


@dataclass(slots=True)
class AuditEvent:
    audit_event_id: UUID
    event_type: str
    subject_kind: str
    subject_id: UUID
    payload: dict[str, Any]
    recorded_at: datetime
    actor_agent_id: UUID | None = None
