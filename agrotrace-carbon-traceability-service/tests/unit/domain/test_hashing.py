"""Tests for deterministic JSON canonicalization and hashing."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from provenance_service.domain.shared.enums import HashAlgorithm
from provenance_service.domain.shared.hashing import (
    canonicalize,
    compute_hash,
    compute_hash_hex,
)


def test_canonicalize_sorts_keys() -> None:
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonicalize(a) == canonicalize(b)
    assert canonicalize(a) == b'{"a":2,"b":1}'


def test_canonicalize_handles_nested_structures() -> None:
    payload = {"x": [{"k": 2, "j": 1}, {"a": True}]}
    assert canonicalize(payload) == b'{"x":[{"j":1,"k":2},{"a":true}]}'


def test_canonicalize_normalizes_uuid_datetime_decimal() -> None:
    payload = {
        "id": UUID("018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001"),
        "ts": datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc),
        "amount": Decimal("12.300"),
    }
    canonical = canonicalize(payload)
    assert b"018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001" in canonical
    assert b"2026-04-29T12:00:00+00:00" in canonical
    assert b'"amount":"12.3"' in canonical


def test_compute_hash_hex_is_deterministic() -> None:
    payload = {"name": "Acre Farm", "year": 2026}
    h1 = compute_hash_hex(payload)
    h2 = compute_hash_hex({"year": 2026, "name": "Acre Farm"})
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_returns_hash_value_object() -> None:
    h = compute_hash({"a": 1}, HashAlgorithm.SHA256)
    assert h.algorithm is HashAlgorithm.SHA256
    assert len(h.value) == 64


def test_canonicalize_rejects_nan_and_infinity() -> None:
    with pytest.raises(ValueError):
        canonicalize({"x": float("nan")})
    with pytest.raises(ValueError):
        canonicalize({"x": float("inf")})


def test_canonicalize_handles_set_deterministically() -> None:
    payload = {"tags": {"b", "a", "c"}}
    canonical = canonicalize(payload)
    assert canonical == b'{"tags":["a","b","c"]}'


def test_canonicalize_supports_sha3_256() -> None:
    digest = compute_hash_hex({"a": 1}, HashAlgorithm.SHA3_256)
    assert len(digest) == 64
    assert digest != compute_hash_hex({"a": 1}, HashAlgorithm.SHA256)


def test_canonicalize_rejects_unknown_types() -> None:
    class Custom: ...

    with pytest.raises(TypeError):
        canonicalize({"x": Custom()})
