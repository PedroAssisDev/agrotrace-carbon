from __future__ import annotations

from app.application.dto.commands import AnchorEvidencePackageCommand, SimulateAnchoringCommand
from app.application.dto.results import SimulateAnchoringResult
from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.constants import NETWORK_CODE_LOCAL_SIMULATED


class SimulateAnchoringUseCase:
    """Compatibility wrapper: delegates to AnchorEvidencePackageUseCase on local_simulated."""

    def __init__(self, uow: SqlAlchemyUnitOfWork, providers: ProvidersRegistry) -> None:
        self._inner = AnchorEvidencePackageUseCase(uow, providers)

    def execute(self, command: SimulateAnchoringCommand) -> SimulateAnchoringResult:
        network_code = command.network_code or NETWORK_CODE_LOCAL_SIMULATED
        result = self._inner.execute(
            AnchorEvidencePackageCommand(
                evidence_package_id=command.evidence_package_id,
                network_code=network_code,
            )
        )
        return SimulateAnchoringResult(
            evidence_package_id=result.evidence_package_id,
            transaction_hash=result.transaction_hash or "",
            block_number=result.block_number or 0,
            anchoring_status=result.anchoring_status,
        )
