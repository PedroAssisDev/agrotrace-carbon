from __future__ import annotations

import hashlib

from app.domain.services.canonical_json_service import (
    DEFAULT_CANONICALIZATION_METHOD,
    to_canonical_json_for,
)
from app.domain.value_objects.canonical_payload import CanonicalPayload
from app.shared.constants import CANONICALIZATION_METHOD_V1, HASH_ALGORITHM_SHA256


def sha256_hex(payload: dict | str, *, prefix: str = "0x", method: str | None = None) -> str:
    """Official SHA-256 over canonical JSON (or raw string already canonical).

    When ``payload`` is a dict, uses the versioned registry (``method`` or default).
    """
    if isinstance(payload, dict):
        data = to_canonical_json_for(method, payload).encode("utf-8")
    else:
        data = payload.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    return f"{prefix}{digest}"


def hash_canonical_payload(payload: CanonicalPayload) -> str:
    body = {"schema_version": payload.schema_version, **payload.payload}
    return sha256_hex(body, method=DEFAULT_CANONICALIZATION_METHOD)


def hash_bytes(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(left + right).digest()


def normalize_hash_to_bytes(hash_value: str) -> bytes:
    cleaned = hash_value.lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return bytes.fromhex(cleaned)
