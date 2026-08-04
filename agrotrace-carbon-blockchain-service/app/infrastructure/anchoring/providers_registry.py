from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.ports.blockchain_anchor_provider_port import BlockchainAnchorProviderPort
from app.infrastructure.anchoring.simulated_anchor_provider import SimulatedAnchorProvider
from app.shared.constants import (
    NETWORK_CODE_ANVIL_LOCAL,
    NETWORK_CODE_ETHEREUM_SEPOLIA,
    NETWORK_CODE_LOCAL_SIMULATED,
)
from app.shared.exceptions import ConfigurationError, NotFoundError

if TYPE_CHECKING:
    from app.shared.config import Settings


class ProvidersRegistry:
    """Lazy provider registry — never opens Web3 connections at import time."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._cache: dict[str, BlockchainAnchorProviderPort] = {}

    def _settings_or_default(self):
        if self._settings is not None:
            return self._settings
        from app.shared.config import get_settings

        return get_settings()

    def get(self, network_code: str) -> BlockchainAnchorProviderPort:
        if network_code in self._cache:
            return self._cache[network_code]

        if network_code == NETWORK_CODE_LOCAL_SIMULATED:
            provider: BlockchainAnchorProviderPort = SimulatedAnchorProvider()
            self._cache[network_code] = provider
            return provider

        if network_code == NETWORK_CODE_ANVIL_LOCAL:
            from app.infrastructure.anchoring.evm.evm_anchor_provider import EvmAnchorProvider

            cfg = self._settings_or_default().anvil_config()
            if not cfg.contract_address:
                raise ConfigurationError(
                    "anvil_local requires BLOCKCHAIN_ANVIL_CONTRACT_ADDRESS"
                )
            provider = EvmAnchorProvider(cfg)
            self._cache[network_code] = provider
            return provider

        if network_code == NETWORK_CODE_ETHEREUM_SEPOLIA:
            from app.infrastructure.anchoring.evm.evm_anchor_provider import EvmAnchorProvider

            settings = self._settings_or_default()
            if not settings.sepolia_ready():
                raise ConfigurationError(
                    "ethereum_sepolia requires RPC URL, private key, contract address "
                    "and chain_id=11155111 (values never logged)"
                )
            provider = EvmAnchorProvider(settings.sepolia_config())
            self._cache[network_code] = provider
            return provider

        raise NotFoundError(f"Unknown network_code: {network_code}")

    def register(self, network_code: str, provider: BlockchainAnchorProviderPort) -> None:
        self._cache[network_code] = provider
