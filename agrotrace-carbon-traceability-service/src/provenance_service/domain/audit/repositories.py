"""Repository protocols for the audit context."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from provenance_service.domain.audit.entities import (
    AuditEvent,
    BlockchainAnchor,
    HashRecord,
    OutboxEvent,
)


class HashRecordRepository(Protocol):
    def add(self, hash_record: HashRecord) -> None: ...
    def get(self, hash_record_id: UUID) -> HashRecord | None: ...
    def find_by_subject(
        self, subject_kind: str, subject_id: UUID, hash_algorithm: str
    ) -> HashRecord | None: ...
    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[HashRecord]: ...


class BlockchainAnchorRepository(Protocol):
    def add(self, anchor: BlockchainAnchor) -> None: ...
    def get(self, blockchain_anchor_id: UUID) -> BlockchainAnchor | None: ...
    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[BlockchainAnchor]: ...
    def find_by_evidence_package_external_id(
        self,
        evidence_package_external_id: str,
        *,
        pipeline_run_id: UUID | None = None,
    ) -> BlockchainAnchor | None: ...
    def update_status(
        self,
        blockchain_anchor_id: UUID,
        *,
        anchor_status: str,
        transaction_hash: str | None = None,
        block_number: str | None = None,
        confirmations: int | None = None,
        anchored_at: object | None = None,
        chain_id: str | None = None,
        verification_uri: str | None = None,
        confirmed_at: object | None = None,
        failed_reason: str | None = None,
        metadata: dict | None = None,
    ) -> None: ...


class OutboxRepository(Protocol):
    def add(self, event: OutboxEvent) -> None: ...
    def list_pending(self, limit: int) -> list[OutboxEvent]: ...
    def list_filtered(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        aggregate_kind: str | None = None,
    ) -> tuple[list[OutboxEvent], int]: ...
    def mark_published(self, outbox_event_id: UUID) -> None: ...
    def mark_failed(self, outbox_event_id: UUID, *, reason: str) -> None: ...


class AuditEventRepository(Protocol):
    def add(self, event: AuditEvent) -> None: ...
    def list_for_subject(self, subject_kind: str, subject_id: UUID) -> list[AuditEvent]: ...
