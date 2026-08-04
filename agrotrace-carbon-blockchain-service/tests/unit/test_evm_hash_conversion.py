from __future__ import annotations

from app.infrastructure.anchoring.evm.hash_conversion import bytes32_to_hex, hex_hash_to_bytes32
from app.infrastructure.anchoring.evm.evidence_key import evidence_package_id_to_key
from app.shared.config import Settings


def test_hex_to_bytes32_roundtrip() -> None:
    value = "0x" + "a1" * 32
    raw = hex_hash_to_bytes32(value)
    assert len(raw) == 32
    assert bytes32_to_hex(raw) == value


def test_does_not_rehash_hex_string() -> None:
    # Direct decode must equal bytes.fromhex of stripped value
    hex_body = "ff" * 32
    assert hex_hash_to_bytes32("0x" + hex_body) == bytes.fromhex(hex_body)


def test_evidence_key_is_32_bytes() -> None:
    key = evidence_package_id_to_key("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert isinstance(key, (bytes, bytearray))
    assert len(key) == 32


def test_sepolia_defaults_not_ready_without_secrets() -> None:
    settings = Settings(
        sepolia_rpc_url="",
        sepolia_private_key="",
        sepolia_contract_address="",
    )
    assert settings.sepolia_ready() is False
    assert settings.sepolia_chain_id == 11155111
