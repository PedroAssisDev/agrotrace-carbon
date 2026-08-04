from __future__ import annotations

from app.application.dto.commands import QueryAnchoredEvidenceCommand
from app.application.dto.results import QueryAnchoredEvidenceResult
from app.domain.ports.blockchain_anchor_provider_port import (
    AnchorQueryRequest,
    BlockchainAnchorQueryPort,
)
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.exceptions import NotFoundError


class QueryAnchoredEvidenceUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, providers: ProvidersRegistry) -> None:
        self._uow = uow
        self._providers = providers
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: QueryAnchoredEvidenceCommand) -> QueryAnchoredEvidenceResult:
        package = self._uow.evidence_packages.get(command.evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")

        provider = self._providers.get(command.network_code)
        if not isinstance(provider, BlockchainAnchorQueryPort):
            network = self._uow.blockchain_networks.get_by_code(command.network_code)
            return QueryAnchoredEvidenceResult(
                found=False,
                evidence_key=None,
                package_hash=None,
                merkle_root=None,
                anchored_at=None,
                submitter=None,
                network_code=command.network_code,
                chain_id=int(network.chain_id) if network and network.chain_id else None,
                contract_address=None,
            )

        result = provider.query(
            AnchorQueryRequest(
                evidence_package_id=command.evidence_package_id,
                package_hash=package.package_hash,
                merkle_root=package.merkle_root,
            )
        )
        self._audit.info(
            event_name="ONCHAIN_QUERY_COMPLETED",
            entity_type="evidence_package",
            entity_id=str(command.evidence_package_id),
            message="On-chain query completed",
            context={
                "network_code": command.network_code,
                "found": result.found,
                "contract_address": result.contract_address,
            },
        )
        return QueryAnchoredEvidenceResult(
            found=result.found,
            evidence_key=result.evidence_key,
            package_hash=result.package_hash,
            merkle_root=result.merkle_root,
            anchored_at=str(result.anchored_at) if result.anchored_at is not None else None,
            submitter=result.submitter,
            network_code=result.network_code,
            chain_id=result.chain_id,
            contract_address=result.contract_address,
        )
