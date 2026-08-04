from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.anchoring.evm.evm_types import EvmNetworkConfig
from app.shared.constants import (
    NETWORK_CODE_ANVIL_LOCAL,
    NETWORK_CODE_ETHEREUM_SEPOLIA,
    NETWORK_CODE_LOCAL_SIMULATED,
)


ROOT_DIR = Path(__file__).resolve().parents[2]

# Well-known Anvil account #0 — ONLY for local development / tests. Never use on Sepolia.
_ANVIL_DEFAULT_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)


class Settings(BaseSettings):
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
        )

    def sepolia_ready(self) -> bool:
        return self.sepolia_config().is_configured() and self.sepolia_chain_id == 11155111


@lru_cache
def get_settings() -> Settings:
    return Settings()
