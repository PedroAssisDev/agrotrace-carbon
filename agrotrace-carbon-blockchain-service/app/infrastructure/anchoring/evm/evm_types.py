from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvmNetworkConfig:
    network_code: str
    chain_id: int
    rpc_url: str
    private_key: str
    contract_address: str
    confirmations: int = 1
    request_timeout_seconds: float = 30.0
    receipt_timeout_seconds: float = 120.0
    gas_limit_margin: float = 1.2
    explorer_base_url: str | None = None
    abi_path: Path | None = None

    def is_configured(self) -> bool:
        return bool(self.rpc_url and self.private_key and self.contract_address)
