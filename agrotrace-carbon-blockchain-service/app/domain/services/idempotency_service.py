"""Deterministic idempotency keys for anchoring submissions."""

from __future__ import annotations

import hashlib


def build_idempotency_key(network_code: str, package_hash: str) -> str:
    """Return SHA-256 hex (0x-prefixed) of ``network_code:package_hash``."""
    material = f"{network_code}:{package_hash}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return f"0x{digest}"
