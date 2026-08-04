"""Deterministic hashing of arbitrary JSON-compatible payloads.

The contract: given the same logical content, two callers running on different
machines, in different orders of dict keys, with different number formatting,
must always produce the exact same hash.

Implementation: JSON canonicalization following the spirit of RFC 8785
(sorted keys, no insignificant whitespace, no NaN/Infinity, consistent number
representation), then SHA-256 (or SHA3-256) over the resulting UTF-8 bytes.

We deliberately keep this module dependency-free.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from provenance_service.domain.shared.enums import HashAlgorithm
from provenance_service.domain.shared.types import Hash


def _normalize(value: Any) -> Any:
    """Map non-JSON-native types to deterministic JSON-friendly forms."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN and Infinity are not allowed in canonical JSON")
        # Avoid platform-specific repr by going through Decimal -> str -> float roundtrip
        # only when needed; the JSON encoder below handles ordinary floats deterministically.
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite Decimal cannot be canonicalized")
        return format(value.normalize(), "f")
    if isinstance(value, str):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, set):
        return [_normalize(v) for v in sorted(value, key=repr)]
    raise TypeError(f"Type {type(value).__name__!r} is not canonicalizable")


def canonicalize(payload: Any) -> bytes:
    """Return the canonical UTF-8 byte representation of ``payload``.

    Output: minified JSON with sorted dict keys, no insignificant whitespace,
    ``ensure_ascii=False`` so unicode is preserved verbatim.
    """
    normalized = _normalize(payload)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_hash_hex(payload: Any, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
    """Compute a hex digest of ``payload`` using the requested algorithm."""
    canonical = canonicalize(payload)
    hasher = _hasher(algorithm)
    hasher.update(canonical)
    return hasher.hexdigest()


def compute_hash(payload: Any, algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> Hash:
    """Compute a :class:`Hash` value object for ``payload``."""
    return Hash(algorithm=algorithm, value=compute_hash_hex(payload, algorithm))


def _hasher(algorithm: HashAlgorithm) -> "hashlib._Hash":  # type: ignore[name-defined]
    if algorithm is HashAlgorithm.SHA256:
        return hashlib.sha256()
    if algorithm is HashAlgorithm.SHA3_256:
        return hashlib.sha3_256()
    raise ValueError(f"Unsupported hash algorithm: {algorithm!r}")  # pragma: no cover
