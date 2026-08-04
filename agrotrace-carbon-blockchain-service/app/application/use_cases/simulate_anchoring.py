from __future__ import annotations

import json

from app.application.dto.commands import SimulateAnchoringCommand
from app.application.dto.results import SimulateAnchoringResult
from app.domain.entities import AnchoringAttempt, BlockchainTransaction
from app.domain.ports.blockchain_anchor_provider_port import AnchorSubmitRequest
from app.domain.services.canonical_json_service import to_canonical_json
from app.domain.value_objects.statuses import (
    AnchorRequestStatus,
    AnchoringMode,
    AnchoringStatus,
    AttemptStatus,
    EvidencePackageStatus,
)
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.shared.clock import format_instant, utcnow
from app.shared.constants import SCHEMA_VERSION_ANCHOR_PAYLOAD
from app.shared.exceptions import InvalidStateError, NotFoundError
from app.shared.ids import new_id


class SimulateAnchoringUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, providers: ProvidersRegistry) -> None:
        self._uow = uow
        self._providers = providers
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: SimulateAnchoringCommand) -> SimulateAnchoringResult:
        package = self._uow.evidence_packages.get(command.evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")
        if not package.package_hash or not package.merkle_root:
            raise InvalidStateError("Evidence package must be hashed before anchoring")

        provider = self._providers.get(command.network_code)
        network = self._uow.blockchain_networks.get_by_code(command.network_code)
        if network is None:
            raise NotFoundError(f"Network not found: {command.network_code}")

        request = self._uow.anchor_requests.get(package.anchor_request_id)
        if request is None:
            raise NotFoundError(f"Anchor request not found: {package.anchor_request_id}")

        attempt_number = self._uow.anchoring_attempts.count_for_request(request.anchor_request_id) + 1
        started_at = utcnow()
        attempt = AnchoringAttempt(
            anchoring_attempt_id=new_id(),
            anchor_request_id=request.anchor_request_id,
            evidence_package_id=package.evidence_package_id,
            attempt_number=attempt_number,
            status=AttemptStatus.STARTED.value,
            error_code=None,
            error_message=None,
            started_at=started_at,
            ended_at=None,
        )
        self._uow.anchoring_attempts.add(attempt)

        anchor_payload = {
            "anchoring_mode": "local_simulated",
            "anchoring_status": AnchoringStatus.SIMULATED.value,
            "merkle_root": package.merkle_root,
            "metadata_hash": package.metadata_hash,
            "network": None,
            "package_id_hash": package.package_hash,
            "package_type": package.package_type,
            "period_end": package.period_end,
            "period_granularity": package.period_granularity,
            "period_start": package.period_start,
            "public_summary_enabled": package.public_summary_enabled,
            "schema_version": SCHEMA_VERSION_ANCHOR_PAYLOAD,
        }
        if package.public_summary_enabled:
            anchor_payload["public_result"] = {
                "result_type": "gross_emission",
                "scale": 1000,
                "total_emission_scaled": 0,
                "unit": "kgCO2e",
            }

        submit_result = provider.submit(
            AnchorSubmitRequest(
                evidence_package_id=package.evidence_package_id,
                package_hash=package.package_hash,
                merkle_root=package.merkle_root,
                metadata_hash=package.metadata_hash or "",
                anchor_payload_json=to_canonical_json(anchor_payload),
            )
        )

        now = utcnow()
        tx = BlockchainTransaction(
            blockchain_transaction_id=new_id(),
            evidence_package_id=package.evidence_package_id,
            network_id=network.network_id,
            anchoring_mode=AnchoringMode.SIMULATED.value,
            anchoring_status=submit_result.anchoring_status,
            transaction_hash=submit_result.transaction_hash,
            block_number=submit_result.block_number,
            anchored_at=submit_result.anchored_at,
            request_payload_json=to_canonical_json(anchor_payload),
            response_payload_json=json.dumps(submit_result.response_payload),
            created_at=now,
            updated_at=now,
        )
        self._uow.blockchain_transactions.add(tx)

        attempt.status = AttemptStatus.SIMULATED.value
        attempt.ended_at = now
        self._uow.anchoring_attempts.update(attempt)

        package.status = EvidencePackageStatus.ANCHORED.value
        package.updated_at = now
        self._uow.evidence_packages.update(package)

        request.status = AnchorRequestStatus.ANCHORED.value
        request.updated_at = now
        self._uow.anchor_requests.update(request)

        self._audit.info(
            event_name="ANCHORING_SIMULATED",
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Simulated anchoring completed",
            correlation_id=request.source_event_id,
            context={
                "transaction_hash": submit_result.transaction_hash,
                "block_number": submit_result.block_number,
                "anchored_at": format_instant(submit_result.anchored_at),
            },
        )

        return SimulateAnchoringResult(
            evidence_package_id=package.evidence_package_id,
            transaction_hash=submit_result.transaction_hash,
            block_number=submit_result.block_number,
            anchoring_status=submit_result.anchoring_status,
        )
