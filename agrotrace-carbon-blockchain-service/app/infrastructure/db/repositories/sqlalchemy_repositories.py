from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.entities import (
    AnchorRequest,
    AnchoringAttempt,
    AuditLogEntry,
    BlockchainNetwork,
    BlockchainTransaction,
    EvidenceItem,
    EvidencePackage,
    HashRecord,
    VerificationLog,
)
from app.domain.ports.repositories_ports import (
    AnchorRequestRepositoryPort,
    AnchoringAttemptRepositoryPort,
    AuditLogRepositoryPort,
    BlockchainNetworkRepositoryPort,
    BlockchainTransactionRepositoryPort,
    EvidenceItemRepositoryPort,
    EvidencePackageRepositoryPort,
    HashRecordRepositoryPort,
    ObserverStateRepositoryPort,
    VerificationLogRepositoryPort,
)
from app.infrastructure.db.models import (
    AnchorRequestModel,
    AnchoringAttemptModel,
    AuditLogModel,
    BlockchainNetworkModel,
    BlockchainTransactionModel,
    EvidenceItemModel,
    EvidencePackageModel,
    HashRecordModel,
    ObserverStateModel,
    VerificationLogModel,
)
from app.shared.clock import utcnow
from app.shared.ids import new_id


def _dt(value: datetime) -> datetime:
    return value


def _map_anchor_request(model: AnchorRequestModel) -> AnchorRequest:
    return AnchorRequest(
        anchor_request_id=UUID(model.anchor_request_id),
        source_event_id=model.source_event_id,
        source_event_type=model.source_event_type,
        pipeline_run_id=UUID(model.pipeline_run_id) if model.pipeline_run_id else None,
        calculation_result_set_id=(
            UUID(model.calculation_result_set_id) if model.calculation_result_set_id else None
        ),
        reporting_period_id=(
            UUID(model.reporting_period_id) if model.reporting_period_id else None
        ),
        request_scope=model.request_scope,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        error_message=model.error_message,
    )


def _map_evidence_package(model: EvidencePackageModel) -> EvidencePackage:
    return EvidencePackage(
        evidence_package_id=UUID(model.evidence_package_id),
        anchor_request_id=UUID(model.anchor_request_id),
        package_type=model.package_type,
        package_version=model.package_version,
        period_start=model.period_start,
        period_end=model.period_end,
        period_granularity=model.period_granularity,
        project_id_hash=model.project_id_hash,
        farm_id_hash=model.farm_id_hash,
        management_unit_id_hash=model.management_unit_id_hash,
        canonical_payload_json=model.canonical_payload_json,
        package_hash=model.package_hash,
        merkle_root=model.merkle_root,
        metadata_hash=model.metadata_hash,
        public_summary_enabled=model.public_summary_enabled,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _map_evidence_item(model: EvidenceItemModel) -> EvidenceItem:
    return EvidenceItem(
        evidence_item_id=UUID(model.evidence_item_id),
        evidence_package_id=UUID(model.evidence_package_id),
        item_order=model.item_order,
        item_type=model.item_type,
        source_table=model.source_table,
        source_record_id=UUID(model.source_record_id) if model.source_record_id else None,
        source_event_id=model.source_event_id,
        source_hash_value=model.source_hash_value,
        canonical_payload_json=model.canonical_payload_json,
        item_hash=model.item_hash,
        created_at=model.created_at,
    )


class SqlAlchemyAnchorRequestRepository(AnchorRequestRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: AnchorRequest) -> None:
        self._session.add(
            AnchorRequestModel(
                anchor_request_id=str(entity.anchor_request_id),
                source_event_id=entity.source_event_id,
                source_event_type=entity.source_event_type,
                pipeline_run_id=str(entity.pipeline_run_id) if entity.pipeline_run_id else None,
                calculation_result_set_id=(
                    str(entity.calculation_result_set_id)
                    if entity.calculation_result_set_id
                    else None
                ),
                reporting_period_id=(
                    str(entity.reporting_period_id) if entity.reporting_period_id else None
                ),
                request_scope=entity.request_scope,
                status=entity.status,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
                error_message=entity.error_message,
            )
        )

    def get(self, anchor_request_id: UUID) -> AnchorRequest | None:
        model = self._session.get(AnchorRequestModel, str(anchor_request_id))
        return _map_anchor_request(model) if model else None

    def get_by_source_event_id(self, source_event_id: str) -> AnchorRequest | None:
        model = (
            self._session.query(AnchorRequestModel)
            .filter(AnchorRequestModel.source_event_id == source_event_id)
            .one_or_none()
        )
        return _map_anchor_request(model) if model else None

    def list_by_status(self, status: str, limit: int = 100) -> list[AnchorRequest]:
        rows = (
            self._session.query(AnchorRequestModel)
            .filter(AnchorRequestModel.status == status)
            .order_by(AnchorRequestModel.created_at.asc())
            .limit(limit)
            .all()
        )
        return [_map_anchor_request(row) for row in rows]

    def update(self, entity: AnchorRequest) -> None:
        model = self._session.get(AnchorRequestModel, str(entity.anchor_request_id))
        if model is None:
            raise KeyError(entity.anchor_request_id)
        model.status = entity.status
        model.updated_at = entity.updated_at
        model.error_message = entity.error_message


class SqlAlchemyEvidencePackageRepository(EvidencePackageRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: EvidencePackage) -> None:
        self._session.add(
            EvidencePackageModel(
                evidence_package_id=str(entity.evidence_package_id),
                anchor_request_id=str(entity.anchor_request_id),
                package_type=entity.package_type,
                package_version=entity.package_version,
                period_start=entity.period_start,
                period_end=entity.period_end,
                period_granularity=entity.period_granularity,
                project_id_hash=entity.project_id_hash,
                farm_id_hash=entity.farm_id_hash,
                management_unit_id_hash=entity.management_unit_id_hash,
                canonical_payload_json=entity.canonical_payload_json,
                package_hash=entity.package_hash,
                merkle_root=entity.merkle_root,
                metadata_hash=entity.metadata_hash,
                public_summary_enabled=entity.public_summary_enabled,
                status=entity.status,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    def get(self, evidence_package_id: UUID) -> EvidencePackage | None:
        model = self._session.get(EvidencePackageModel, str(evidence_package_id))
        return _map_evidence_package(model) if model else None

    def get_by_anchor_request(self, anchor_request_id: UUID) -> EvidencePackage | None:
        model = (
            self._session.query(EvidencePackageModel)
            .filter(EvidencePackageModel.anchor_request_id == str(anchor_request_id))
            .one_or_none()
        )
        return _map_evidence_package(model) if model else None

    def update(self, entity: EvidencePackage) -> None:
        model = self._session.get(EvidencePackageModel, str(entity.evidence_package_id))
        if model is None:
            raise KeyError(entity.evidence_package_id)
        model.canonical_payload_json = entity.canonical_payload_json
        model.package_hash = entity.package_hash
        model.merkle_root = entity.merkle_root
        model.metadata_hash = entity.metadata_hash
        model.public_summary_enabled = entity.public_summary_enabled
        model.status = entity.status
        model.updated_at = entity.updated_at


class SqlAlchemyEvidenceItemRepository(EvidenceItemRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: EvidenceItem) -> None:
        self._session.add(
            EvidenceItemModel(
                evidence_item_id=str(entity.evidence_item_id),
                evidence_package_id=str(entity.evidence_package_id),
                item_order=entity.item_order,
                item_type=entity.item_type,
                source_table=entity.source_table,
                source_record_id=str(entity.source_record_id) if entity.source_record_id else None,
                source_event_id=entity.source_event_id,
                source_hash_value=entity.source_hash_value,
                canonical_payload_json=entity.canonical_payload_json,
                item_hash=entity.item_hash,
                created_at=entity.created_at,
            )
        )

    def get(self, evidence_item_id: UUID) -> EvidenceItem | None:
        model = self._session.get(EvidenceItemModel, str(evidence_item_id))
        return _map_evidence_item(model) if model else None

    def list_by_package(self, evidence_package_id: UUID) -> list[EvidenceItem]:
        rows = (
            self._session.query(EvidenceItemModel)
            .filter(EvidenceItemModel.evidence_package_id == str(evidence_package_id))
            .order_by(EvidenceItemModel.item_order.asc())
            .all()
        )
        return [_map_evidence_item(row) for row in rows]

    def update(self, entity: EvidenceItem) -> None:
        model = self._session.get(EvidenceItemModel, str(entity.evidence_item_id))
        if model is None:
            raise KeyError(entity.evidence_item_id)
        model.canonical_payload_json = entity.canonical_payload_json
        model.item_hash = entity.item_hash


class SqlAlchemyHashRecordRepository(HashRecordRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: HashRecord) -> None:
        self._session.add(
            HashRecordModel(
                hash_record_id=str(entity.hash_record_id),
                subject_kind=entity.subject_kind,
                subject_id=str(entity.subject_id),
                hash_algorithm=entity.hash_algorithm,
                canonicalization_method=entity.canonicalization_method,
                hash_value=entity.hash_value,
                payload_ref=entity.payload_ref,
                created_at=entity.created_at,
            )
        )


class SqlAlchemyBlockchainNetworkRepository(BlockchainNetworkRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_code(self, network_code: str) -> BlockchainNetwork | None:
        model = (
            self._session.query(BlockchainNetworkModel)
            .filter(BlockchainNetworkModel.network_code == network_code)
            .one_or_none()
        )
        if model is None:
            return None
        return BlockchainNetwork(
            network_id=UUID(model.network_id),
            network_code=model.network_code,
            network_name=model.network_name,
            provider_type=model.provider_type,
            chain_id=model.chain_id,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def ensure_default_networks(self) -> None:
        existing = self.get_by_code("local_simulated")
        if existing:
            return
        now = utcnow()
        self._session.add(
            BlockchainNetworkModel(
                network_id=str(new_id()),
                network_code="local_simulated",
                network_name="Local Simulated Network",
                provider_type="simulated",
                chain_id=None,
                is_active=True,
                created_at=now,
            )
        )


class SqlAlchemyBlockchainTransactionRepository(BlockchainTransactionRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: BlockchainTransaction) -> None:
        self._session.add(
            BlockchainTransactionModel(
                blockchain_transaction_id=str(entity.blockchain_transaction_id),
                evidence_package_id=str(entity.evidence_package_id),
                network_id=str(entity.network_id),
                anchoring_mode=entity.anchoring_mode,
                anchoring_status=entity.anchoring_status,
                transaction_hash=entity.transaction_hash,
                block_number=entity.block_number,
                anchored_at=entity.anchored_at,
                request_payload_json=entity.request_payload_json,
                response_payload_json=entity.response_payload_json,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
        )

    def get_latest_for_package(self, evidence_package_id: UUID) -> BlockchainTransaction | None:
        model = (
            self._session.query(BlockchainTransactionModel)
            .filter(BlockchainTransactionModel.evidence_package_id == str(evidence_package_id))
            .order_by(BlockchainTransactionModel.created_at.desc())
            .first()
        )
        if model is None:
            return None
        return BlockchainTransaction(
            blockchain_transaction_id=UUID(model.blockchain_transaction_id),
            evidence_package_id=UUID(model.evidence_package_id),
            network_id=UUID(model.network_id),
            anchoring_mode=model.anchoring_mode,
            anchoring_status=model.anchoring_status,
            transaction_hash=model.transaction_hash,
            block_number=model.block_number,
            anchored_at=model.anchored_at,
            request_payload_json=model.request_payload_json,
            response_payload_json=model.response_payload_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyAnchoringAttemptRepository(AnchoringAttemptRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: AnchoringAttempt) -> None:
        self._session.add(
            AnchoringAttemptModel(
                anchoring_attempt_id=str(entity.anchoring_attempt_id),
                anchor_request_id=str(entity.anchor_request_id),
                evidence_package_id=str(entity.evidence_package_id),
                attempt_number=entity.attempt_number,
                status=entity.status,
                error_code=entity.error_code,
                error_message=entity.error_message,
                started_at=entity.started_at,
                ended_at=entity.ended_at,
            )
        )

    def update(self, entity: AnchoringAttempt) -> None:
        model = self._session.get(AnchoringAttemptModel, str(entity.anchoring_attempt_id))
        if model is None:
            raise KeyError(entity.anchoring_attempt_id)
        model.status = entity.status
        model.error_code = entity.error_code
        model.error_message = entity.error_message
        model.ended_at = entity.ended_at

    def count_for_request(self, anchor_request_id: UUID) -> int:
        return (
            self._session.query(AnchoringAttemptModel)
            .filter(AnchoringAttemptModel.anchor_request_id == str(anchor_request_id))
            .count()
        )

    def list_failed_requests(self, limit: int = 100) -> list[UUID]:
        rows = (
            self._session.query(AnchorRequestModel.anchor_request_id)
            .filter(AnchorRequestModel.status == "failed")
            .limit(limit)
            .all()
        )
        return [UUID(row[0]) for row in rows]


class SqlAlchemyVerificationLogRepository(VerificationLogRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: VerificationLog) -> None:
        self._session.add(
            VerificationLogModel(
                verification_log_id=str(entity.verification_log_id),
                evidence_package_id=str(entity.evidence_package_id),
                verification_type=entity.verification_type,
                expected_hash=entity.expected_hash,
                computed_hash=entity.computed_hash,
                is_valid=entity.is_valid,
                verified_at=entity.verified_at,
                details_json=entity.details_json,
            )
        )


class SqlAlchemyAuditLogRepository(AuditLogRepositoryPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: AuditLogEntry) -> None:
        self._session.add(
            AuditLogModel(
                audit_log_id=str(entity.audit_log_id),
                event_name=entity.event_name,
                entity_type=entity.entity_type,
                entity_id=entity.entity_id,
                correlation_id=entity.correlation_id,
                severity=entity.severity,
                message=entity.message,
                context_json=entity.context_json,
                created_at=entity.created_at,
            )
        )

    def list_for_entity(self, entity_type: str, entity_id: str) -> list[AuditLogEntry]:
        rows = (
            self._session.query(AuditLogModel)
            .filter(
                AuditLogModel.entity_type == entity_type,
                AuditLogModel.entity_id == entity_id,
            )
            .order_by(AuditLogModel.created_at.asc())
            .all()
        )
        return [
            AuditLogEntry(
                audit_log_id=UUID(row.audit_log_id),
                event_name=row.event_name,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                correlation_id=row.correlation_id,
                severity=row.severity,
                message=row.message,
                context_json=row.context_json,
                created_at=row.created_at,
            )
            for row in rows
        ]


class SqlAlchemyObserverStateRepository(ObserverStateRepositoryPort):
    WATERMARK_KEY = "outbox_watermark"

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_watermark(self) -> datetime | None:
        model = self._session.get(ObserverStateModel, self.WATERMARK_KEY)
        if model is None:
            return None
        return datetime.fromisoformat(model.state_value)

    def set_watermark(self, value: datetime) -> None:
        model = self._session.get(ObserverStateModel, self.WATERMARK_KEY)
        if model is None:
            self._session.add(
                ObserverStateModel(
                    state_key=self.WATERMARK_KEY,
                    state_value=value.isoformat(),
                    updated_at=utcnow(),
                )
            )
        else:
            model.state_value = value.isoformat()
            model.updated_at = utcnow()
