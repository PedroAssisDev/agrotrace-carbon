from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.shared.redact import redact_secret, sanitize_rpc_url


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
    contract_version: str | None = None
    expected_abi_checksum: str | None = None

    def is_configured(self) -> bool:
        return bool(self.rpc_url and self.private_key and self.contract_address)

    def __repr__(self) -> str:
        return (
            f"EvmNetworkConfig(network_code={self.network_code!r}, "
            f"chain_id={self.chain_id}, rpc_url={sanitize_rpc_url(self.rpc_url)!r}, "
            f"private_key={redact_secret(self.private_key)!r}, "
            f"contract_address={self.contract_address!r}, "
            f"contract_version={self.contract_version!r})"
        )
