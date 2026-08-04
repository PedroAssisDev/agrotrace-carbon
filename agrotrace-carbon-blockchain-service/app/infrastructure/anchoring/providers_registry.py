from __future__ import annotations

from app.domain.ports.blockchain_anchor_provider_port import BlockchainAnchorProviderPort
from app.infrastructure.anchoring.simulated_anchor_provider import SimulatedAnchorProvider


class ProvidersRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BlockchainAnchorProviderPort] = {
            "local_simulated": SimulatedAnchorProvider(),
        }

    def get(self, network_code: str) -> BlockchainAnchorProviderPort:
        provider = self._providers.get(network_code)
        if provider is None:
            raise KeyError(f"No provider registered for network_code={network_code}")
        return provider
