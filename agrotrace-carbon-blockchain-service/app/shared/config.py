from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.anchoring.abi_versioning import resolve_abi_path
from app.infrastructure.anchoring.evm.evm_types import EvmNetworkConfig
from app.shared.constants import (
    NETWORK_CODE_ANVIL_LOCAL,
    NETWORK_CODE_ETHEREUM_SEPOLIA,
    NETWORK_CODE_LOCAL_SIMULATED,
)
from app.shared.redact import redact_secret, sanitize_mapping, sanitize_rpc_url


ROOT_DIR = Path(__file__).resolve().parents[2]

# Well-known Anvil account #0 — ONLY for local development / tests. Never use on Sepolia.
# Value is never logged via __repr__/safe_dict.
_ANVIL_DEFAULT_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)

DEFAULT_CONTRACT_VERSION = "1.0.0"


class Settings(BaseSettings):
    """Configuração tipada lida exclusivamente de variáveis BLOCKCHAIN_* / .env externo."""

    model_config = SettingsConfigDict(
        env_prefix="BLOCKCHAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default=f"sqlite:///{ROOT_DIR / 'data' / 'blockchain_service.db'}")
    provenance_database_url: str = Field(
        default=str(
            ROOT_DIR.parent / "agrotrace-carbon-traceability-service" / "data" / "provenance.db"
        )
    )
    environment: str = Field(default="local")
    service_name: str = Field(default="agrotrace-carbon-blockchain-service")
    observer_batch_size: int = Field(default=100)
    default_network_code: str = Field(default=NETWORK_CODE_LOCAL_SIMULATED)
    canonicalization_method: str = Field(default="json_canonical_v1")
    hash_algorithm: str = Field(default="sha256")

    # Contract / ABI versioning (RNF010)
    contract_name: str = Field(default="CarbonEvidenceRegistry")
    contract_version: str = Field(default=DEFAULT_CONTRACT_VERSION)
    abi_checksum_sha256: str = Field(default="")

    # Anvil local
    anvil_rpc_url: str = Field(default="http://127.0.0.1:8545")
    anvil_chain_id: int = Field(default=31337)
    anvil_private_key: str = Field(default=_ANVIL_DEFAULT_PRIVATE_KEY)
    anvil_contract_address: str = Field(default="")
    anvil_confirmations: int = Field(default=1)
    anvil_request_timeout_seconds: float = Field(default=30.0)
    anvil_receipt_timeout_seconds: float = Field(default=60.0)

    # Sepolia
    sepolia_rpc_url: str = Field(default="")
    sepolia_chain_id: int = Field(default=11155111)
    sepolia_private_key: str = Field(default="")
    sepolia_contract_address: str = Field(default="")
    sepolia_confirmations: int = Field(default=1)
    sepolia_request_timeout_seconds: float = Field(default=30.0)
    sepolia_receipt_timeout_seconds: float = Field(default=180.0)
    sepolia_explorer_base_url: str = Field(default="https://sepolia.etherscan.io")

    def __repr__(self) -> str:
        return f"Settings({self.safe_dict()!r})"

    def __str__(self) -> str:
        return self.__repr__()

    def safe_dict(self) -> dict:
        """Dict redigido — seguro para logs."""
        raw = {
            "environment": self.environment,
            "service_name": self.service_name,
            "default_network_code": self.default_network_code,
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "abi_checksum_sha256": self.abi_checksum_sha256 or "(unset)",
            "anvil_rpc_url": sanitize_rpc_url(self.anvil_rpc_url),
            "anvil_chain_id": self.anvil_chain_id,
            "anvil_private_key": redact_secret(self.anvil_private_key),
            "anvil_contract_address": self.anvil_contract_address or "(empty)",
            "sepolia_rpc_url": sanitize_rpc_url(self.sepolia_rpc_url),
            "sepolia_chain_id": self.sepolia_chain_id,
            "sepolia_private_key": redact_secret(self.sepolia_private_key),
            "sepolia_contract_address": self.sepolia_contract_address or "(empty)",
        }
        return sanitize_mapping(raw)

    def require_evm_ready(self, network: str = "sepolia") -> None:
        """Falha com mensagem segura se EVM estiver incompleto."""
        if network == "sepolia":
            cfg = self.sepolia_config()
            label = "Sepolia"
        else:
            cfg = self.anvil_config()
            label = "Anvil"
        missing: list[str] = []
        if not cfg.rpc_url:
            missing.append("rpc_url")
        if not cfg.private_key:
            missing.append("private_key")
        if not cfg.contract_address:
            missing.append("contract_address")
        if missing:
            raise ValueError(
                f"{label} EVM configuration incomplete: missing {', '.join(missing)}. "
                "Set BLOCKCHAIN_* environment variables (values never logged)."
            )

    def _abi_path(self) -> Path:
        return resolve_abi_path(contract_version=self.contract_version)

    def anvil_config(self) -> EvmNetworkConfig:
        return EvmNetworkConfig(
            network_code=NETWORK_CODE_ANVIL_LOCAL,
            chain_id=self.anvil_chain_id,
            rpc_url=self.anvil_rpc_url,
            private_key=self.anvil_private_key,
            contract_address=self.anvil_contract_address,
            confirmations=self.anvil_confirmations,
            request_timeout_seconds=self.anvil_request_timeout_seconds,
            receipt_timeout_seconds=self.anvil_receipt_timeout_seconds,
            explorer_base_url=None,
            abi_path=self._abi_path(),
            contract_version=self.contract_version,
            expected_abi_checksum=self.abi_checksum_sha256 or None,
        )

    def sepolia_config(self) -> EvmNetworkConfig:
        return EvmNetworkConfig(
            network_code=NETWORK_CODE_ETHEREUM_SEPOLIA,
            chain_id=self.sepolia_chain_id,
            rpc_url=self.sepolia_rpc_url,
            private_key=self.sepolia_private_key,
            contract_address=self.sepolia_contract_address,
            confirmations=self.sepolia_confirmations,
            request_timeout_seconds=self.sepolia_request_timeout_seconds,
            receipt_timeout_seconds=self.sepolia_receipt_timeout_seconds,
            explorer_base_url=self.sepolia_explorer_base_url,
            abi_path=self._abi_path(),
            contract_version=self.contract_version,
            expected_abi_checksum=self.abi_checksum_sha256 or None,
        )

    def sepolia_ready(self) -> bool:
        return self.sepolia_config().is_configured() and self.sepolia_chain_id == 11155111

    def is_simulated_default(self) -> bool:
        return self.default_network_code == NETWORK_CODE_LOCAL_SIMULATED


@lru_cache
def get_settings() -> Settings:
    return Settings()
