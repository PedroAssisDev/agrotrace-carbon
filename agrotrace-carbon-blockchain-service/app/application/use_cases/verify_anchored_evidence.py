from __future__ import annotations

import json
from dataclasses import asdict

from app.application.dto.commands import (
    QueryAnchoredEvidenceCommand,
    VerifyAnchoredEvidenceCommand,
    VerifyEvidencePackageCommand,
)
from app.application.dto.results import VerifyAnchoredEvidenceResult
from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase
from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
from app.domain.entities import VerificationLog
from app.domain.value_objects.statuses import VerificationType
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.clock import utcnow
from app.shared.exceptions import NotFoundError
from app.shared.ids import new_id


class VerifyAnchoredEvidenceUseCase:
    """Combine off-chain integrity with on-chain hash comparison."""

    def __init__(self, uow: SqlAlchemyUnitOfWork, providers: ProvidersRegistry) -> None:
        self._uow = uow
        self._providers = providers
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: VerifyAnchoredEvidenceCommand) -> VerifyAnchoredEvidenceResult:
        package = self._uow.evidence_packages.get(command.evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")

        offchain = VerifyEvidencePackageUseCase(self._uow).execute(
            VerifyEvidencePackageCommand(evidence_package_id=command.evidence_package_id)
        )
        query = QueryAnchoredEvidenceUseCase(self._uow, self._providers).execute(
            QueryAnchoredEvidenceCommand(
                evidence_package_id=command.evidence_package_id,
                network_code=command.network_code,
            )
        )

        network = self._uow.blockchain_networks.get_by_code(command.network_code)
        network_match = network is not None and network.network_code == command.network_code
        contract_match = bool(query.contract_address)
        package_hash_match = bool(
            query.found
            and package.package_hash
            and query.package_hash
            and query.package_hash.lower() == package.package_hash.lower()
        )
        merkle_root_match = bool(
            query.found
            and package.merkle_root
            and query.merkle_root
            and query.merkle_root.lower() == package.merkle_root.lower()
        )

        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.ONCHAIN_PACKAGE_HASH.value,
                expected_hash=package.package_hash,
                computed_hash=query.package_hash,
                is_valid=package_hash_match,
                verified_at=utcnow(),
                details_json=json.dumps({"network_code": command.network_code}),
            )
        )
        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.ONCHAIN_MERKLE_ROOT.value,
                expected_hash=package.merkle_root,
                computed_hash=query.merkle_root,
                is_valid=merkle_root_match,
                verified_at=utcnow(),
                details_json=None,
            )
        )

        overall = (
            offchain.is_valid
            and query.found
            and package_hash_match
            and merkle_root_match
            and network_match
            and contract_match
        )
        self._uow.verification_logs.add(
            VerificationLog(
                verification_log_id=new_id(),
                evidence_package_id=package.evidence_package_id,
                verification_type=VerificationType.FULL_ONCHAIN.value,
                expected_hash=package.package_hash,
                computed_hash=query.package_hash,
                is_valid=overall,
                verified_at=utcnow(),
                details_json=json.dumps(
                    {
                        "offchain_valid": offchain.is_valid,
                        "onchain_found": query.found,
                        "package_hash_match": package_hash_match,
                        "merkle_root_match": merkle_root_match,
                    }
                ),
            )
        )

        event = (
            "ONCHAIN_VERIFICATION_SUCCEEDED" if overall else "ONCHAIN_VERIFICATION_FAILED"
        )
        self._audit.info(
            event_name=event,
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Combined off-chain/on-chain verification completed",
            context={"overall_valid": overall, "network_code": command.network_code},
        )

        return VerifyAnchoredEvidenceResult(
            evidence_package_id=package.evidence_package_id,
            offchain_valid=offchain.is_valid,
            onchain_found=query.found,
            package_hash_match=package_hash_match,
            merkle_root_match=merkle_root_match,
            network_match=network_match,
            contract_match=contract_match,
            overall_valid=overall,
            details={"offchain": offchain.details, "query": asdict(query)},
        )
