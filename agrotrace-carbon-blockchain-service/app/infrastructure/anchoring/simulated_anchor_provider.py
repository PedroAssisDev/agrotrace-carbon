from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from app.domain.ports.blockchain_anchor_provider_port import (
    AnchorSubmitRequest,
    AnchorSubmitResult,
    BlockchainAnchorProviderPort,
)


class SimulatedAnchorProvider(BlockchainAnchorProviderPort):
    @property
    def network_code(self) -> str:
        return "local_simulated"

    @property
    def provider_type(self) -> str:
        return "simulated"

    def submit(self, request: AnchorSubmitRequest) -> AnchorSubmitResult:
        seed = f"{request.evidence_package_id}:{request.package_hash}:{request.merkle_root}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        block_seed = hashlib.sha256(f"block:{seed}".encode("utf-8")).hexdigest()
        anchored_at = datetime.now(UTC)
        return AnchorSubmitResult(
            transaction_hash=f"0x{digest}",
            block_number=int(block_seed[:8], 16),
            anchored_at=anchored_at,
            anchoring_status="simulated",
            response_payload={
                "provider": self.provider_type,
                "network_code": self.network_code,
                "simulated": True,
            },
        )
