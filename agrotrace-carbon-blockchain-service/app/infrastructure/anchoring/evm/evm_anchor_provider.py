from __future__ import annotations

from datetime import UTC, datetime

from app.domain.ports.blockchain_anchor_provider_port import (
    AnchorQueryRequest,
    AnchorQueryResult,
    AnchorSubmitRequest,
    AnchorSubmitResult,
    BlockchainAnchorProviderPort,
    BlockchainAnchorQueryPort,
)
from app.domain.value_objects.statuses import AnchoringStatus
from app.infrastructure.anchoring.evm.errors import OnchainMismatchError
from app.infrastructure.anchoring.evm.evidence_key import (
    evidence_key_hex,
    evidence_package_id_to_key,
)
from app.infrastructure.anchoring.evm.evm_contract_client import EvmContractClient
from app.infrastructure.anchoring.evm.evm_types import EvmNetworkConfig
from app.infrastructure.anchoring.evm.hash_conversion import bytes32_to_hex


class EvmAnchorProvider(BlockchainAnchorProviderPort, BlockchainAnchorQueryPort):
    """Generic EVM anchor provider used for Anvil and Sepolia."""

    def __init__(self, config: EvmNetworkConfig) -> None:
        self._config = config
        self._client = EvmContractClient(config)

    @property
    def network_code(self) -> str:
        return self._config.network_code

    @property
    def provider_type(self) -> str:
        return "evm"

    @property
    def chain_id(self) -> int:
        return self._config.chain_id

    @property
    def contract_address(self) -> str:
        return self._config.contract_address

    def submit(self, request: AnchorSubmitRequest) -> AnchorSubmitResult:
        evidence_key = evidence_package_id_to_key(request.evidence_package_id)
        result = self._client.submit_anchor(
            evidence_key=evidence_key,
            package_hash=request.package_hash,
            merkle_root=request.merkle_root,
        )

        if result["onchain_package_hash"].lower() != request.package_hash.lower():
            raise OnchainMismatchError("on-chain packageHash does not match local hash")
        if result["onchain_merkle_root"].lower() != request.merkle_root.lower():
            raise OnchainMismatchError("on-chain merkleRoot does not match local root")

        explorer_url = None
        if self._config.explorer_base_url:
            explorer_url = (
                f"{self._config.explorer_base_url.rstrip('/')}/tx/{result['transaction_hash']}"
            )

        response_payload = {
            **result,
            "evidence_key": evidence_key_hex(request.evidence_package_id),
            "package_hash": request.package_hash,
            "merkle_root": request.merkle_root,
            "confirmations": self._config.confirmations,
            "explorer_url": explorer_url,
            "simulated": False,
            "provider": self.provider_type,
        }

        return AnchorSubmitResult(
            transaction_hash=result["transaction_hash"],
            block_number=result["block_number"],
            anchored_at=datetime.fromtimestamp(result["onchain_anchored_at"], tz=UTC),
            anchoring_status=AnchoringStatus.CONFIRMED.value,
            response_payload=response_payload,
        )

    def query(self, request: AnchorQueryRequest) -> AnchorQueryResult:
        evidence_key = evidence_package_id_to_key(request.evidence_package_id)
        package_hash, merkle_root, anchored_at, submitter, exists = self._client.get_evidence(
            evidence_key
        )
        return AnchorQueryResult(
            found=bool(exists),
            evidence_key=evidence_key_hex(request.evidence_package_id),
            package_hash=bytes32_to_hex(bytes(package_hash)) if exists else None,
            merkle_root=bytes32_to_hex(bytes(merkle_root)) if exists else None,
            anchored_at=int(anchored_at) if exists else None,
            submitter=submitter if exists else None,
            network_code=self.network_code,
            chain_id=self.chain_id,
            contract_address=self.contract_address,
        )
