from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

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


class AnchorRequestRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: AnchorRequest) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, anchor_request_id: UUID) -> AnchorRequest | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_source_event_id(self, source_event_id: str) -> AnchorRequest | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_status(self, status: str, limit: int = 100) -> list[AnchorRequest]:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: AnchorRequest) -> None:
        raise NotImplementedError


class EvidencePackageRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: EvidencePackage) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, evidence_package_id: UUID) -> EvidencePackage | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_anchor_request(self, anchor_request_id: UUID) -> EvidencePackage | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: EvidencePackage) -> None:
        raise NotImplementedError


class EvidenceItemRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: EvidenceItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, evidence_item_id: UUID) -> EvidenceItem | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_package(self, evidence_package_id: UUID) -> list[EvidenceItem]:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: EvidenceItem) -> None:
        raise NotImplementedError


class HashRecordRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: HashRecord) -> None:
        raise NotImplementedError


class BlockchainNetworkRepositoryPort(ABC):
    @abstractmethod
    def get_by_code(self, network_code: str) -> BlockchainNetwork | None:
        raise NotImplementedError

    @abstractmethod
    def ensure_default_networks(self) -> None:
        raise NotImplementedError


class BlockchainTransactionRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: BlockchainTransaction) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_for_package(self, evidence_package_id: UUID) -> BlockchainTransaction | None:
        raise NotImplementedError


class AnchoringAttemptRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: AnchoringAttempt) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: AnchoringAttempt) -> None:
        raise NotImplementedError

    @abstractmethod
    def count_for_request(self, anchor_request_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_failed_requests(self, limit: int = 100) -> list[UUID]:
        raise NotImplementedError


class VerificationLogRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: VerificationLog) -> None:
        raise NotImplementedError


class AuditLogRepositoryPort(ABC):
    @abstractmethod
    def add(self, entity: AuditLogEntry) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_for_entity(self, entity_type: str, entity_id: str) -> list[AuditLogEntry]:
        raise NotImplementedError


class UnitOfWorkPort(ABC):
    anchor_requests: AnchorRequestRepositoryPort
    evidence_packages: EvidencePackageRepositoryPort
    evidence_items: EvidenceItemRepositoryPort
    hash_records: HashRecordRepositoryPort
    blockchain_networks: BlockchainNetworkRepositoryPort
    blockchain_transactions: BlockchainTransactionRepositoryPort
    anchoring_attempts: AnchoringAttemptRepositoryPort
    verification_logs: VerificationLogRepositoryPort
    audit_logs: AuditLogRepositoryPort

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        """Optional flush hook for implementations that expose SQLAlchemy session."""
        return None

    def __enter__(self) -> UnitOfWorkPort:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc:
            self.rollback()
        else:
            self.commit()
        self.close()


class ObserverStateRepositoryPort(ABC):
    @abstractmethod
    def get_watermark(self) -> datetime | None:
        raise NotImplementedError

    @abstractmethod
    def set_watermark(self, value: datetime) -> None:
        raise NotImplementedError
