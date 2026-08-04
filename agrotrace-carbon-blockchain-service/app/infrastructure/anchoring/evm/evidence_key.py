"""On-chain evidence key derivation."""

from __future__ import annotations

from uuid import UUID

from eth_utils import keccak


def evidence_package_id_to_key(evidence_package_id: UUID | str) -> bytes:
    """evidenceKey = keccak256(UTF-8(evidence_package_id))."""
    text = str(evidence_package_id)
    return keccak(text.encode("utf-8"))


def evidence_key_hex(evidence_package_id: UUID | str) -> str:
    return "0x" + evidence_package_id_to_key(evidence_package_id).hex()
