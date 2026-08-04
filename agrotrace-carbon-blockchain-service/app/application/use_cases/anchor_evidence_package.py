from __future__ import annotations

import json

from app.application.dto.commands import AnchorEvidencePackageCommand
from app.application.dto.results import AnchorEvidencePackageResult
from app.domain.entities import AnchoringAttempt, BlockchainTransaction
from app.domain.ports.blockchain_anchor_provider_port import AnchorSubmitRequest
from app.domain.services.canonical_json_service import to_canonical_json
from app.domain.services.final_publication_gate import require_final_publication_event
from app.domain.services.idempotency_service import build_idempotency_key
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
from app.shared.constants import (
    NETWORK_CODE_LOCAL_SIMULATED,
    SCHEMA_VERSION_ANCHOR_PAYLOAD,
)
from app.shared.exceptions import AnchoringProviderError, InvalidStateError, NotFoundError
from app.shared.ids import new_id

_REUSABLE_STATUSES = frozenset(
    {
        AnchoringStatus.SIMULATED.value,
        AnchoringStatus.CONFIRMED.value,
        AnchoringStatus.SUBMITTED.value,
        AnchoringStatus.PENDING.value,
    }
)


class AnchorEvidencePackageUseCase:
    """General anchoring use case for simulated and EVM providers."""

    def __init__(self, uow: SqlAlchemyUnitOfWork, providers: ProvidersRegistry) -> None:
        self._uow = uow
        self._providers = providers
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: AnchorEvidencePackageCommand) -> AnchorEvidencePackageResult:
        package = self._uow.evidence_packages.get(command.evidence_package_id)
        if package is None:
            raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")
        if not package.package_hash or not package.merkle_root:
            raise InvalidStateError("Evidence package must be hashed before anchoring")

        request = self._uow.anchor_requests.get(package.anchor_request_id)
        if request is None:
            raise NotFoundError(f"Anchor request not found: {package.anchor_request_id}")
        require_final_publication_event(
            request.source_event_type, context="anchor_evidence_package"
        )

        network = self._uow.blockchain_networks.get_by_code(command.network_code)
        if network is None:
            raise NotFoundError(f"Network not found: {command.network_code}")

        provider = self._providers.get(command.network_code)
        idempotency_key = build_idempotency_key(command.network_code, package.package_hash)

        self._audit.info(
            event_name="ANCHORING_REQUESTED",
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Anchoring requested",
            correlation_id=request.source_event_id,
            context={
                "network_code": command.network_code,
                "chain_id": network.chain_id,
                "idempotency_key": idempotency_key,
            },
        )

        existing = self._uow.blockchain_transactions.get_by_idempotency_key(idempotency_key)
        if existing and existing.anchoring_status in _REUSABLE_STATUSES:
            self._audit.info(
                event_name="ANCHORING_REUSED_IDEMPOTENTLY",
                entity_type="evidence_package",
                entity_id=str(package.evidence_package_id),
                message="Reused existing anchoring transaction",
                correlation_id=request.source_event_id,
                context={
                    "network_code": command.network_code,
                    "transaction_hash": existing.transaction_hash,
                    "anchoring_status": existing.anchoring_status,
                },
            )
            return self._result_from_existing(
                package=package,
                network_code=command.network_code,
                chain_id=int(network.chain_id) if network.chain_id else None,
                tx=existing,
                idempotent_reuse=True,
            )

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
        # Persist pending attempt before long-running provider.submit so later
        # update() can resolve the row (session.get after add without flush fails).
        self._uow.flush()

        is_simulated = command.network_code == NETWORK_CODE_LOCAL_SIMULATED
        anchoring_mode = AnchoringMode.SIMULATED.value if is_simulated else AnchoringMode.REAL.value
        anchor_payload = {
            "anchoring_mode": anchoring_mode,
            "anchoring_status": (
                AnchoringStatus.SIMULATED.value if is_simulated else AnchoringStatus.PENDING.value
            ),
            "merkle_root": package.merkle_root,
            "metadata_hash": package.metadata_hash,
            "network": {
                "network_code": network.network_code,
                "chain_id": network.chain_id,
                "provider_type": network.provider_type,
            },
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

        try:
            submit_result = provider.submit(
                AnchorSubmitRequest(
                    evidence_package_id=package.evidence_package_id,
                    package_hash=package.package_hash,
                    merkle_root=package.merkle_root,
                    metadata_hash=package.metadata_hash or "",
                    anchor_payload_json=to_canonical_json(anchor_payload),
                )
            )
        except Exception as exc:
            now = utcnow()
            attempt.status = AttemptStatus.FAILED.value
            attempt.error_code = type(exc).__name__
            attempt.error_message = str(exc)[:500]
            attempt.ended_at = now
            self._uow.anchoring_attempts.update(attempt)
            self._audit.error(
                event_name="ANCHORING_FAILED",
                entity_type="evidence_package",
                entity_id=str(package.evidence_package_id),
                message="Anchoring provider failed",
                correlation_id=request.source_event_id,
                context={"error": str(exc)[:500], "network_code": command.network_code},
            )
            raise AnchoringProviderError(str(exc)) from exc

        now = utcnow()
        response_payload = dict(submit_result.response_payload or {})
        response_payload.setdefault("idempotency_key", idempotency_key)
        tx = BlockchainTransaction(
            blockchain_transaction_id=new_id(),
            evidence_package_id=package.evidence_package_id,
            network_id=network.network_id,
            anchoring_mode=anchoring_mode,
            anchoring_status=submit_result.anchoring_status,
            transaction_hash=submit_result.transaction_hash,
            block_number=submit_result.block_number,
            anchored_at=submit_result.anchored_at,
            request_payload_json=to_canonical_json(anchor_payload),
            response_payload_json=json.dumps(response_payload),
            created_at=now,
            updated_at=now,
            idempotency_key=idempotency_key,
        )
        self._uow.blockchain_transactions.add(tx)

        if submit_result.anchoring_status == AnchoringStatus.SIMULATED.value:
            attempt.status = AttemptStatus.SIMULATED.value
            event_name = "ANCHORING_SIMULATED"
        elif submit_result.anchoring_status == AnchoringStatus.CONFIRMED.value:
            attempt.status = AttemptStatus.CONFIRMED.value
            event_name = "ANCHORING_CONFIRMED"
        elif submit_result.anchoring_status == AnchoringStatus.REVERTED.value:
            attempt.status = AttemptStatus.REVERTED.value
            event_name = "ANCHORING_REVERTED"
        elif submit_result.anchoring_status == AnchoringStatus.TIMEOUT.value:
            attempt.status = AttemptStatus.TIMEOUT.value
            event_name = "ANCHORING_TIMEOUT"
        else:
            attempt.status = AttemptStatus.SUBMITTED.value
            event_name = "ANCHORING_SUBMITTED"

        attempt.ended_at = now
        self._uow.anchoring_attempts.update(attempt)

        package.status = EvidencePackageStatus.ANCHORED.value
        package.updated_at = now
        self._uow.evidence_packages.update(package)

        request.status = AnchorRequestStatus.ANCHORED.value
        request.updated_at = now
        self._uow.anchor_requests.update(request)

        self._audit.info(
            event_name=event_name,
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Anchoring completed",
            correlation_id=request.source_event_id,
            context={
                "transaction_hash": submit_result.transaction_hash,
                "block_number": submit_result.block_number,
                "anchored_at": format_instant(submit_result.anchored_at),
                "network_code": command.network_code,
                "chain_id": network.chain_id,
                "contract_address": response_payload.get("contract_address"),
            },
        )

        return AnchorEvidencePackageResult(
            evidence_package_id=package.evidence_package_id,
            network_code=command.network_code,
            chain_id=int(network.chain_id) if network.chain_id else None,
            contract_address=response_payload.get("contract_address"),
            evidence_key=response_payload.get("evidence_key"),
            package_hash=package.package_hash,
            merkle_root=package.merkle_root,
            transaction_hash=submit_result.transaction_hash,
            block_number=submit_result.block_number,
            anchoring_status=submit_result.anchoring_status,
            receipt_status=response_payload.get("receipt_status"),
            gas_used=response_payload.get("gas_used"),
            effective_gas_price=response_payload.get("effective_gas_price"),
            explorer_url=response_payload.get("explorer_url"),
            idempotent_reuse=False,
            anchoring_mode=anchoring_mode,
            provider_response=response_payload,
        )

    def _result_from_existing(
        self,
        *,
        package,
        network_code: str,
        chain_id: int | None,
        tx: BlockchainTransaction,
        idempotent_reuse: bool,
    ) -> AnchorEvidencePackageResult:
        payload: dict = {}
        if tx.response_payload_json:
            try:
                payload = json.loads(tx.response_payload_json)
            except json.JSONDecodeError:
                payload = {}
        return AnchorEvidencePackageResult(
            evidence_package_id=package.evidence_package_id,
            network_code=network_code,
            chain_id=chain_id,
            contract_address=payload.get("contract_address"),
            evidence_key=payload.get("evidence_key"),
            package_hash=package.package_hash or "",
            merkle_root=package.merkle_root or "",
            transaction_hash=tx.transaction_hash,
            block_number=tx.block_number,
            anchoring_status=tx.anchoring_status,
            receipt_status=payload.get("receipt_status"),
            gas_used=payload.get("gas_used"),
            effective_gas_price=payload.get("effective_gas_price"),
            explorer_url=payload.get("explorer_url"),
            idempotent_reuse=idempotent_reuse,
            anchoring_mode=tx.anchoring_mode,
            provider_response=payload,
        )
