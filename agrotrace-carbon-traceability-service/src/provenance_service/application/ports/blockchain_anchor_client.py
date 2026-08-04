"""Outbound port for the blockchain anchoring service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AnchorReceipt:
    transaction_hash: str
    block_number: str | None
    chain_id: str | None
    submitted_at: datetime
    transport_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnchorStatus:
    confirmations: int
    confirmed: bool
    block_number: str | None
    transport_metadata: dict[str, Any] = field(default_factory=dict)


class BlockchainAnchorClient(Protocol):
    """Anchors a hash (or Merkle root) on a blockchain and queries confirmations."""

    def anchor_root(
        self,
        *,
        merkle_root: str,
        network: str,
        metadata: dict[str, Any] | None = None,
    ) -> AnchorReceipt: ...

    def get_confirmation_status(
        self,
        *,
        transaction_hash: str,
        network: str,
    ) -> AnchorStatus: ...
