from __future__ import annotations

import hashlib

from app.domain.services.canonical_json_service import to_canonical_json
from app.domain.value_objects.canonical_payload import CanonicalPayload
from app.shared.constants import CANONICALIZATION_METHOD_V1, HASH_ALGORITHM_SHA256


def sha256_hex(payload: dict | str, *, prefix: str = "0x") -> str:
    if isinstance(payload, dict):
        data = to_canonical_json(payload).encode("utf-8")
    else:
        data = payload.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    return f"{prefix}{digest}"


def hash_canonical_payload(payload: CanonicalPayload) -> str:
    body = {"schema_version": payload.schema_version, **payload.payload}
    return sha256_hex(body)


def hash_bytes(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(left + right).digest()


def normalize_hash_to_bytes(hash_value: str) -> bytes:
    cleaned = hash_value.lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return bytes.fromhex(cleaned)
