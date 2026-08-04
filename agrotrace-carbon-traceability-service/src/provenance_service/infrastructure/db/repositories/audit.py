"""SQLAlchemy implementations of the audit-context repositories."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from provenance_service.domain.audit.entities import (
    AuditEvent,
    BlockchainAnchor,
    HashRecord,
    OutboxEvent,
)
from provenance_service.domain.shared.enums import OutboxStatus
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.db.models.audit import (
    AuditEventModel,
    BlockchainAnchorModel,
    HashRecordModel,
    OutboxEventModel,
)
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemyHashRecordRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, hash_record: HashRecord) -> None:
        self._session.add(M.to_hash_record_model(hash_record))

    def get(self, hash_record_id: UUID) -> HashRecord | None:
        m = get_model_or_pending(self._session, HashRecordModel, "hash_record_id", hash_record_id)
        return M.from_hash_record_model(m) if m else None

    def find_by_subject(
        self, subject_kind: str, subject_id: UUID, hash_algorithm: str
    ) -> HashRecord | None:
        m = self._session.scalar(
            select(HashRecordModel).where(
                HashRecordModel.subject_kind == subject_kind,
                HashRecordModel.subject_id == subject_id,
                HashRecordModel.hash_algorithm == hash_algorithm,
            )
        )
        return M.from_hash_record_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[HashRecord]:
        rows = self._session.scalars(
            select(HashRecordModel).where(
                HashRecordModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_hash_record_model(m) for m in rows]


class SqlAlchemyBlockchainAnchorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, anchor: BlockchainAnchor) -> None:
        self._session.add(M.to_blockchain_anchor_model(anchor))

    def get(self, blockchain_anchor_id: UUID) -> BlockchainAnchor | None:
        m = get_model_or_pending(
            self._session, BlockchainAnchorModel, "blockchain_anchor_id", blockchain_anchor_id
        )
        return M.from_blockchain_anchor_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[BlockchainAnchor]:
        rows = self._session.scalars(
            select(BlockchainAnchorModel).where(
                BlockchainAnchorModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_blockchain_anchor_model(m) for m in rows]

    def update_status(
        self,
        blockchain_anchor_id: UUID,
        *,
        anchor_status: str,
        transaction_hash: str | None = None,
        block_number: str | None = None,
        confirmations: int | None = None,
        anchored_at: datetime | None = None,
    ) -> None:
        # blockchain_anchor is intentionally NOT in the append-only list (it has a
        # lifecycle: pending -> submitted -> confirmed/failed). It is not protected by
        # the append-only trigger, so a regular UPDATE is allowed.
        values: dict[str, object] = {"anchor_status": anchor_status}
        if transaction_hash is not None:
            values["transaction_hash"] = transaction_hash
        if block_number is not None:
            values["block_number"] = block_number
        if confirmations is not None:
            values["confirmations"] = confirmations
        if anchored_at is not None:
            values["anchored_at"] = anchored_at
        stmt = (
            update(BlockchainAnchorModel)
            .where(BlockchainAnchorModel.blockchain_anchor_id == blockchain_anchor_id)
            .values(**values)
        )
        self._session.execute(stmt)


class SqlAlchemyOutboxRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: OutboxEvent) -> None:
        self._session.add(M.to_outbox_event_model(event))

    def list_pending(self, limit: int) -> list[OutboxEvent]:
        rows = self._session.scalars(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == OutboxStatus.PENDING.value)
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
        ).all()
        return [M.from_outbox_event_model(m) for m in rows]

    def list_filtered(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        aggregate_kind: str | None = None,
        event_type: str | None = None,
    ) -> tuple[list[OutboxEvent], int]:
        filters = []
        if status:
            filters.append(OutboxEventModel.status == status)
        if aggregate_kind:
            filters.append(OutboxEventModel.aggregate_kind == aggregate_kind)
        if event_type:
            filters.append(OutboxEventModel.event_type == event_type)

        total_stmt = select(func.count()).select_from(OutboxEventModel)
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = int(self._session.scalar(total_stmt) or 0)

        stmt = (
            select(OutboxEventModel)
            .order_by(OutboxEventModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if filters:
            stmt = stmt.where(*filters)
        rows = self._session.scalars(stmt).all()
        return [M.from_outbox_event_model(m) for m in rows], total

    def mark_published(self, outbox_event_id: UUID) -> None:
        stmt = (
            update(OutboxEventModel)
            .where(OutboxEventModel.outbox_event_id == outbox_event_id)
            .values(status=OutboxStatus.PUBLISHED.value, published_at=utcnow())
        )
        self._session.execute(stmt)

    def mark_failed(self, outbox_event_id: UUID, *, reason: str) -> None:
        from provenance_service.domain.shared.ids import new_uuid7

        stmt = (
            update(OutboxEventModel)
            .where(OutboxEventModel.outbox_event_id == outbox_event_id)
            .values(status=OutboxStatus.FAILED.value)
        )
        self._session.execute(stmt)
        self._session.add(
            AuditEventModel(
                audit_event_id=new_uuid7(),
                event_type="outbox.failed",
                actor_agent_id=None,
                subject_kind="outbox_event",
                subject_id=outbox_event_id,
                payload={"reason": reason},
                recorded_at=utcnow(),
            )
        )


class SqlAlchemyAuditEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: AuditEvent) -> None:
        self._session.add(M.to_audit_event_model(event))

    def list_for_subject(self, subject_kind: str, subject_id: UUID) -> list[AuditEvent]:
        rows = self._session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.subject_kind == subject_kind,
                AuditEventModel.subject_id == subject_id,
            )
        ).all()
        return [M.from_audit_event_model(m) for m in rows]
