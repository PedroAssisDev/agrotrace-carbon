from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.domain.ports.repositories_ports import UnitOfWorkPort
from app.infrastructure.db.repositories.sqlalchemy_repositories import (
    SqlAlchemyAnchorRequestRepository,
    SqlAlchemyAnchoringAttemptRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyBlockchainNetworkRepository,
    SqlAlchemyBlockchainTransactionRepository,
    SqlAlchemyEvidenceItemRepository,
    SqlAlchemyEvidencePackageRepository,
    SqlAlchemyHashRecordRepository,
    SqlAlchemyObserverStateRepository,
    SqlAlchemyVerificationLogRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session = session_factory()
        self.anchor_requests = SqlAlchemyAnchorRequestRepository(self._session)
        self.evidence_packages = SqlAlchemyEvidencePackageRepository(self._session)
        self.evidence_items = SqlAlchemyEvidenceItemRepository(self._session)
        self.hash_records = SqlAlchemyHashRecordRepository(self._session)
        self.blockchain_networks = SqlAlchemyBlockchainNetworkRepository(self._session)
        self.blockchain_transactions = SqlAlchemyBlockchainTransactionRepository(self._session)
        self.anchoring_attempts = SqlAlchemyAnchoringAttemptRepository(self._session)
        self.verification_logs = SqlAlchemyVerificationLogRepository(self._session)
        self.audit_logs = SqlAlchemyAuditLogRepository(self._session)
        self.observer_state = SqlAlchemyObserverStateRepository(self._session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()

    def flush(self) -> None:
        self._session.flush()
