"""Unit tests for pure helpers in validar_sepolia_interativo.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import validar_sepolia_interativo as script


def test_sanitize_rpc_url_masks_alchemy_token() -> None:
    url = "https://eth-sepolia.g.alchemy.com/v2/alch_REALTOKEN_SHOULD_HIDE"
    sanitized = script.sanitize_rpc_url(url)
    assert "REALTOKEN" not in sanitized
    assert "********" in sanitized
    assert "eth-sepolia.g.alchemy.com" in sanitized


def test_sanitize_rpc_url_empty() -> None:
    assert script.sanitize_rpc_url(None) == "(ausente)"
    assert script.sanitize_rpc_url("") == "(ausente)"


def test_redact_secret() -> None:
    assert script.redact_secret(None) == "(vazio)"
    assert script.redact_secret("abc") == "********"
    assert "****" in script.redact_secret("0123456789abcdef")


def test_sanitize_mapping_hides_private_key_and_rpc() -> None:
    data = {
        "BLOCKCHAIN_SEPOLIA_PRIVATE_KEY": "0x" + "ab" * 32,
        "BLOCKCHAIN_SEPOLIA_RPC_URL": "https://eth-sepolia.g.alchemy.com/v2/secrettoken123",
        "wallet": "0x1111111111111111111111111111111111111111",
        "nested": {"API_KEY": "xyz", "ok": 1},
    }
    clean = script.sanitize_mapping(data)
    assert clean["BLOCKCHAIN_SEPOLIA_PRIVATE_KEY"] == "********"
    assert "secrettoken123" not in clean["BLOCKCHAIN_SEPOLIA_RPC_URL"]
    assert clean["wallet"].startswith("0x")
    assert clean["nested"]["API_KEY"] == "********"
    assert clean["nested"]["ok"] == 1


def test_is_valid_eth_address() -> None:
    assert script.is_valid_eth_address("0x0000000000000000000000000000000000000001")
    assert not script.is_valid_eth_address("0x123")
    assert not script.is_valid_eth_address("not-an-address")
    assert not script.is_valid_eth_address("")


def test_is_valid_hash_32() -> None:
    good = "0x" + "ab" * 32
    assert script.is_valid_hash_32(good)
    assert script.is_valid_hash_32("ab" * 32)
    assert not script.is_valid_hash_32("0xabc")
    assert not script.is_valid_hash_32(None)


def test_private_key_has_32_bytes() -> None:
    assert script.private_key_has_32_bytes("0x" + "11" * 32)
    assert script.private_key_has_32_bytes("22" * 32)
    assert not script.private_key_has_32_bytes("0x1234")
    assert not script.private_key_has_32_bytes("zzzz")


def test_safe_serialize_and_write_evidence(tmp_path: Path) -> None:
    payload = {
        "PRIVATE_KEY": "secret",
        "rpc": "https://eth-sepolia.g.alchemy.com/v2/token123",
        "ok": True,
    }
    path = script.write_evidence(tmp_path, "sample.json", payload, "PASSOU")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["status"] == "PASSOU"
    assert "timestamp" in loaded
    assert loaded["PRIVATE_KEY"] == "********"
    assert "token123" not in json.dumps(loaded)


def test_aguardar_enter_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "sair")
    with pytest.raises(script.UserAbortedError):
        script.aguardar_enter("prompt: ")


def test_aguardar_enter_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    script.aguardar_enter("prompt: ")


def test_parse_args_defaults() -> None:
    args = script.parse_args([])
    assert args.package_id is None
    assert args.query_only is False
    assert args.resume_transaction is None


def test_parse_args_flags() -> None:
    args = script.parse_args(
        [
            "--package-id",
            "11111111-1111-1111-1111-111111111111",
            "--query-only",
            "--resume-transaction",
            "0x" + "aa" * 32,
            "--create-sample-package",
        ]
    )
    assert args.package_id == "11111111-1111-1111-1111-111111111111"
    assert args.query_only is True
    assert args.resume_transaction.startswith("0x")
    assert args.create_sample_package is True


def test_parse_args_create_sample_default_false() -> None:
    args = script.parse_args([])
    assert args.create_sample_package is False
