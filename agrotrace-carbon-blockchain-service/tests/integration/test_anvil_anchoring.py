from __future__ import annotations

import json
import socket
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest
from web3 import Web3

from app.application.dto.commands import AnchorEvidencePackageCommand
from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase
from app.domain.ports.blockchain_anchor_provider_port import (
    AnchorQueryRequest,
    AnchorSubmitRequest,
)
from app.infrastructure.anchoring.evm.errors import DuplicateEvidenceError
from app.infrastructure.anchoring.evm.evidence_key import evidence_key_hex, evidence_package_id_to_key
from app.infrastructure.anchoring.evm.evm_anchor_provider import EvmAnchorProvider
from app.infrastructure.anchoring.evm.hash_conversion import hex_hash_to_bytes32
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.shared.config import Settings
from app.shared.constants import NETWORK_CODE_ANVIL_LOCAL

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"
ANVIL_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ANVIL_ACCOUNT = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_rpc(url: str, timeout: float = 30.0) -> Web3:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 2}))
            if w3.is_connected():
                _ = w3.eth.chain_id
                return w3
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(0.2)
    raise RuntimeError(f"Anvil RPC did not become ready: {last_err}")


def _deploy_registry(rpc_url: str) -> str:
    """Deploy via Web3 using Foundry artifact bytecode (more reliable than forge create JSON)."""
    artifact = (
        CONTRACTS_DIR / "out" / "CarbonEvidenceRegistry.sol" / "CarbonEvidenceRegistry.json"
    )
    if not artifact.exists():
        forge = Path.home() / ".foundry" / "bin" / "forge.exe"
        forge_bin = str(forge) if forge.exists() else "forge"
        subprocess.run([forge_bin, "build"], cwd=str(CONTRACTS_DIR), check=True)

    data = json.loads(artifact.read_text(encoding="utf-8"))
    abi = data["abi"]
    bytecode = data["bytecode"]["object"]
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    account = w3.eth.account.from_key(ANVIL_KEY)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor(ANVIL_ACCOUNT).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "chainId": 31337,
            "gas": 2_000_000,
            "maxFeePerGas": w3.to_wei(2, "gwei"),
            "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        }
    )
    signed = account.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    address = receipt["contractAddress"]
    if not address:
        raise RuntimeError("contract deployment returned empty address")
    return Web3.to_checksum_address(address)


@pytest.fixture(scope="module")
def anvil_env():
    port = _free_port()
    rpc_url = f"http://127.0.0.1:{port}"
    anvil = Path.home() / ".foundry" / "bin" / "anvil.exe"
    anvil_bin = str(anvil) if anvil.exists() else "anvil"
    proc = subprocess.Popen(
        [anvil_bin, "--host", "127.0.0.1", "--port", str(port), "--chain-id", "31337"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_rpc(rpc_url)
        contract = _deploy_registry(rpc_url)
        yield {"rpc_url": rpc_url, "contract": contract, "port": port}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.blockchain_local
def test_hash_conversion_and_evidence_key() -> None:
    digest = "ab" * 32
    assert hex_hash_to_bytes32("0x" + digest) == bytes.fromhex(digest)
    key = evidence_package_id_to_key("11111111-1111-1111-1111-111111111111")
    assert len(key) == 32
    assert evidence_key_hex("11111111-1111-1111-1111-111111111111").startswith("0x")


@pytest.mark.blockchain_local
def test_anvil_anchor_query_and_idempotency(anvil_env, uow_factory, tmp_path) -> None:
    from tests.integration.test_e2e_flow import _build_package, _create_provenance_schema, _seed_provenance

    provenance_db = tmp_path / "provenance.db"
    _create_provenance_schema(provenance_db)
    _seed_provenance(provenance_db)
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'blockchain.db'}",
        provenance_database_url=str(provenance_db),
        anvil_rpc_url=anvil_env["rpc_url"],
        anvil_contract_address=anvil_env["contract"],
        anvil_private_key=ANVIL_KEY,
        anvil_chain_id=31337,
    )
    uow, build = _build_package(settings, uow_factory)
    package = uow.evidence_packages.get(build.evidence_package_id)
    assert package and package.package_hash and package.merkle_root

    cfg = settings.anvil_config()
    provider = EvmAnchorProvider(cfg)
    registry = ProvidersRegistry(settings)
    registry.register(NETWORK_CODE_ANVIL_LOCAL, provider)

    first = AnchorEvidencePackageUseCase(uow, registry).execute(
        AnchorEvidencePackageCommand(
            evidence_package_id=build.evidence_package_id,
            network_code=NETWORK_CODE_ANVIL_LOCAL,
        )
    )
    assert first.idempotent_reuse is False
    assert first.transaction_hash and first.transaction_hash.startswith("0x")
    assert first.block_number and first.block_number > 0
    assert first.anchoring_status == "confirmed"
    assert first.receipt_status == 1

    query = provider.query(
        AnchorQueryRequest(evidence_package_id=build.evidence_package_id)
    )
    assert query.found is True
    assert query.package_hash.lower() == package.package_hash.lower()
    assert query.merkle_root.lower() == package.merkle_root.lower()

    second = AnchorEvidencePackageUseCase(uow, registry).execute(
        AnchorEvidencePackageCommand(
            evidence_package_id=build.evidence_package_id,
            network_code=NETWORK_CODE_ANVIL_LOCAL,
        )
    )
    assert second.idempotent_reuse is True
    assert second.transaction_hash == first.transaction_hash

    # Direct provider duplicate should revert if forced with a new package id conceptually:
    # submit again with same evidence key via provider raises DuplicateEvidenceError
    with pytest.raises(DuplicateEvidenceError):
        provider.submit(
            AnchorSubmitRequest(
                evidence_package_id=build.evidence_package_id,
                package_hash=package.package_hash,
                merkle_root=package.merkle_root,
                metadata_hash=package.metadata_hash or "",
                anchor_payload_json="{}",
            )
        )
    uow.commit()
    uow.close()


@pytest.mark.blockchain_local
def test_same_package_different_networks_have_different_idempotency_keys() -> None:
    from app.domain.services.idempotency_service import build_idempotency_key

    package_hash = "0x" + "11" * 32
    assert build_idempotency_key("local_simulated", package_hash) != build_idempotency_key(
        "anvil_local", package_hash
    )
