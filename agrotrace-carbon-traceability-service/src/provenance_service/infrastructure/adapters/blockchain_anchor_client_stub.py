"""No-op blockchain anchor client (returns deterministic synthetic receipts)."""

from __future__ import annotations

import hashlib
from typing import Any

from provenance_service.application.ports import (
    AnchorReceipt,
    AnchorStatus,
    BlockchainAnchorClient,
)
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.observability import get_logger


class StubBlockchainAnchorClient(BlockchainAnchorClient):
    def __init__(self) -> None:
        self._log = get_logger("adapter.blockchain_anchor")

    def anchor_root(
        self,
        *,
        merkle_root: str,
        network: str,
        metadata: dict[str, Any] | None = None,
    ) -> AnchorReceipt:
        tx_hash = "0x" + hashlib.sha256(f"{network}|{merkle_root}".encode("utf-8")).hexdigest()
        self._log.info(
            "blockchain.anchor_stub",
            network=network,
            merkle_root=merkle_root,
            tx_hash=tx_hash,
        )
        return AnchorReceipt(
            transaction_hash=tx_hash,
            block_number=None,
            chain_id=None,
            submitted_at=utcnow(),
            transport_metadata={"adapter": "stub", "network": network},
        )

    def get_confirmation_status(
        self,
        *,
        transaction_hash: str,
        network: str,
    ) -> AnchorStatus:
        self._log.info(
            "blockchain.confirmations_stub",
            network=network,
            transaction_hash=transaction_hash,
        )
        return AnchorStatus(
            confirmations=0,
            confirmed=False,
            block_number=None,
            transport_metadata={"adapter": "stub"},
        )
