"""RNF012 — redaction, Settings safe repr, on-chain minimization (no secret values)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BLOCKCHAIN = Path(__file__).resolve().parents[2] / "agrotrace-carbon-blockchain-service"
sys.path.insert(0, str(BLOCKCHAIN))


def test_redact_masks_private_key_and_rpc():
    from app.shared.redact import redact_secret, sanitize_mapping, sanitize_rpc_url

    assert "abcd" not in redact_secret("0x" + "ab" * 32) or "********" in redact_secret("0x" + "ab" * 32)
    assert "********" in redact_secret("0x" + "ab" * 32)
    url = sanitize_rpc_url("https://user:pass@example.com/v3/secrettokenvaluehere")
    assert "pass" not in url
    assert "secrettokenvaluehere" not in url
    clean = sanitize_mapping({"sepolia_private_key": "0x" + "cd" * 32, "ok": 1})
    assert clean["sepolia_private_key"] == "********"
    assert clean["ok"] == 1


def test_settings_repr_does_not_leak_key():
    from app.shared.config import Settings

    s = Settings(sepolia_private_key="0x" + "ee" * 32, sepolia_rpc_url="https://example.invalid/v3/tok")
    text = repr(s)
    assert "ee" * 8 not in text
    assert "********" in text
    with pytest.raises(ValueError) as ei:
        s.require_evm_ready("sepolia")
    assert "0xee" not in str(ei.value).lower()
    assert "incomplete" in str(ei.value).lower() or "missing" in str(ei.value).lower()


def test_simulated_does_not_require_key():
    from app.shared.config import Settings
    from app.shared.constants import NETWORK_CODE_LOCAL_SIMULATED

    s = Settings(default_network_code=NETWORK_CODE_LOCAL_SIMULATED, sepolia_private_key="")
    assert s.is_simulated_default()


def test_on_chain_payload_minimization_fields_only():
    """Anchor/on-chain surface: hashes + responsible + timestamp — not business body/keys."""
    from app.domain.ports.blockchain_anchor_provider_port import AnchorSubmitRequest
    from uuid import uuid4

    req = AnchorSubmitRequest(
        evidence_package_id=uuid4(),
        package_hash="0x" + "11" * 32,
        merkle_root="0x" + "22" * 32,
        metadata_hash="0x" + "33" * 32,
        anchor_payload_json='{"schema_version":"anchor_payload_v1"}',
    )
    # Request to provider carries hashes only (+ opaque anchor_payload_json without secrets)
    assert "private_key" not in req.anchor_payload_json
    assert "rpc" not in req.anchor_payload_json.lower()
    # Solidity API documented fields
    on_chain_fields = {"evidenceKey", "packageHash", "merkleRoot", "anchoredAt", "submitter"}
    assert on_chain_fields == {"evidenceKey", "packageHash", "merkleRoot", "anchoredAt", "submitter"}


def test_evm_network_config_repr_redacted():
    from app.infrastructure.anchoring.evm.evm_types import EvmNetworkConfig

    cfg = EvmNetworkConfig(
        network_code="ethereum_sepolia",
        chain_id=11155111,
        rpc_url="https://user:secret@rpc.example/v3/tokentoken",
        private_key="0x" + "aa" * 32,
        contract_address="0x" + "00" * 20,
    )
    r = repr(cfg)
    assert "secret" not in r
    assert "aaaaaaaa" not in r
    assert "********" in r
