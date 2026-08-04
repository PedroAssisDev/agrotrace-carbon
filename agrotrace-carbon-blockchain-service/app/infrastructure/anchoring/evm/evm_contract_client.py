from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.contract import Contract
from web3.exceptions import TimeExhausted
from web3.middleware import ExtraDataToPOAMiddleware

from app.infrastructure.anchoring.evm.errors import (
    ChainIdMismatchError,
    ContractMissingError,
    DuplicateEvidenceError,
    GasEstimationError,
    InsufficientBalanceError,
    InvalidAbiError,
    InvalidAddressError,
    PrivateKeyInvalidError,
    PrivateKeyMissingError,
    ReceiptTimeoutError,
    RpcUnavailableError,
    TransactionRevertedError,
    WalletNotAuthorizedError,
)
from app.infrastructure.anchoring.abi_versioning import AbiVersionError, validate_abi_file
from app.infrastructure.anchoring.evm.evm_types import EvmNetworkConfig
from app.infrastructure.anchoring.evm.hash_conversion import hex_hash_to_bytes32

DEFAULT_ABI_PATH = (
    Path(__file__).resolve().parents[1] / "contracts" / "CarbonEvidenceRegistry.abi.json"
)


class EvmContractClient:
    """Lazy Web3 client for CarbonEvidenceRegistry."""

    def __init__(self, config: EvmNetworkConfig) -> None:
        self.config = config
        self._w3: Web3 | None = None
        self._account = None
        self._contract: Contract | None = None

    def connect(self) -> Web3:
        if self._w3 is not None:
            return self._w3
        if not self.config.rpc_url:
            raise RpcUnavailableError("RPC URL is not configured")
        w3 = Web3(
            Web3.HTTPProvider(
                self.config.rpc_url,
                request_kwargs={"timeout": self.config.request_timeout_seconds},
            )
        )
        try:
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        except Exception:
            pass
        if not w3.is_connected():
            raise RpcUnavailableError("RPC endpoint is unavailable")
        chain_id = int(w3.eth.chain_id)
        if chain_id != self.config.chain_id:
            raise ChainIdMismatchError(
                f"expected chain_id={self.config.chain_id}, got {chain_id}"
            )
        self._w3 = w3
        return w3

    def load_account(self):
        if self._account is not None:
            return self._account
        key = (self.config.private_key or "").strip()
        if not key:
            raise PrivateKeyMissingError("private key is not configured")
        key_hex = key if key.startswith("0x") else "0x" + key
        try:
            account = self.connect().eth.account.from_key(key_hex)
        except Exception as exc:
            raise PrivateKeyInvalidError("private key is invalid") from exc
        self._account = account
        return account

    def load_abi(self) -> list[dict[str, Any]]:
        path = self.config.abi_path or DEFAULT_ABI_PATH
        try:
            meta = validate_abi_file(
                path,
                expected_version=self.config.contract_version,
                expected_checksum=self.config.expected_abi_checksum,
            )
        except AbiVersionError as exc:
            raise InvalidAbiError(str(exc)) from exc
        return meta["abi"]

    def load_contract(self) -> Contract:
        if self._contract is not None:
            return self._contract
        w3 = self.connect()
        address = (self.config.contract_address or "").strip()
        if not address or not w3.is_address(address):
            raise InvalidAddressError("contract address is invalid")
        checksum = w3.to_checksum_address(address)
        code = w3.eth.get_code(checksum)
        if code is None or len(code) == 0:
            raise ContractMissingError("no bytecode at contract address")
        contract = w3.eth.contract(address=checksum, abi=self.load_abi())
        self._contract = contract
        return contract

    def ensure_authorized(self) -> None:
        contract = self.load_contract()
        account = self.load_account()
        owner = contract.functions.owner().call()
        if owner.lower() != account.address.lower():
            raise WalletNotAuthorizedError(
                "wallet address is not the contract owner/authorized submitter"
            )

    def evidence_exists(self, evidence_key: bytes) -> bool:
        return bool(self.load_contract().functions.evidenceExists(evidence_key).call())

    def get_evidence(self, evidence_key: bytes) -> tuple:
        return self.load_contract().functions.getEvidence(evidence_key).call()

    def submit_anchor(
        self,
        *,
        evidence_key: bytes,
        package_hash: str,
        merkle_root: str,
    ) -> dict[str, Any]:
        w3 = self.connect()
        account = self.load_account()
        contract = self.load_contract()
        self.ensure_authorized()

        package_bytes = hex_hash_to_bytes32(package_hash)
        merkle_bytes = hex_hash_to_bytes32(merkle_root)

        if self.evidence_exists(evidence_key):
            raise DuplicateEvidenceError("evidence already exists on-chain")

        balance = w3.eth.get_balance(account.address)
        if balance == 0:
            raise InsufficientBalanceError("wallet balance is zero")

        nonce = w3.eth.get_transaction_count(account.address, "pending")
        tx_base: dict[str, Any] = {
            "from": account.address,
            "nonce": nonce,
            "chainId": self.config.chain_id,
        }

        try:
            estimated = contract.functions.anchorEvidence(
                evidence_key, package_bytes, merkle_bytes
            ).estimate_gas({"from": account.address})
        except Exception as exc:
            raise GasEstimationError("gas estimation failed") from exc

        tx_base["gas"] = int(estimated * self.config.gas_limit_margin)

        try:
            latest = w3.eth.get_block("latest")
            base_fee = latest.get("baseFeePerGas")
            if base_fee is not None:
                max_priority = w3.to_wei(1, "gwei")
                tx_base["maxPriorityFeePerGas"] = max_priority
                tx_base["maxFeePerGas"] = int(base_fee) * 2 + max_priority
            else:
                tx_base["gasPrice"] = w3.eth.gas_price
        except Exception:
            tx_base["gasPrice"] = w3.eth.gas_price

        unsigned = contract.functions.anchorEvidence(
            evidence_key, package_bytes, merkle_bytes
        ).build_transaction(tx_base)

        signed = account.sign_transaction(unsigned)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw)
        tx_hash_hex = Web3.to_hex(tx_hash)

        try:
            receipt = w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=self.config.receipt_timeout_seconds
            )
        except TimeExhausted as exc:
            raise ReceiptTimeoutError(
                f"timed out waiting for receipt of {tx_hash_hex}"
            ) from exc

        status = int(receipt.get("status", 0))
        if status != 1:
            raise TransactionRevertedError(f"transaction reverted: {tx_hash_hex}")

        if self.config.confirmations > 1:
            import time

            target = int(receipt["blockNumber"]) + self.config.confirmations - 1
            while int(w3.eth.block_number) < target:
                time.sleep(0.2)

        onchain = self.get_evidence(evidence_key)
        return {
            "transaction_hash": tx_hash_hex,
            "block_number": int(receipt["blockNumber"]),
            "block_hash": Web3.to_hex(receipt["blockHash"]),
            "transaction_index": int(receipt["transactionIndex"]),
            "gas_used": int(receipt["gasUsed"]),
            "effective_gas_price": int(receipt.get("effectiveGasPrice") or 0),
            "from_address": account.address,
            "receipt_status": status,
            "contract_address": contract.address,
            "chain_id": self.config.chain_id,
            "network_code": self.config.network_code,
            "onchain_package_hash": "0x" + bytes(onchain[0]).hex(),
            "onchain_merkle_root": "0x" + bytes(onchain[1]).hex(),
            "onchain_anchored_at": int(onchain[2]),
            "onchain_submitter": onchain[3],
            "onchain_exists": bool(onchain[4]),
        }
