"""Same payload must always produce the same hash, across instances and orders."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from provenance_service.domain.shared.hashing import compute_hash_hex


def test_canonical_form_is_order_independent() -> None:
    a = {"a": 1, "b": [{"x": 1, "y": 2}, {"y": 4, "x": 3}]}
    b = {"b": [{"y": 2, "x": 1}, {"x": 3, "y": 4}], "a": 1}
    assert compute_hash_hex(a) == compute_hash_hex(b)


def test_decimal_representation_is_canonical() -> None:
    a = {"v": Decimal("1.20")}
    b = {"v": Decimal("1.2")}
    assert compute_hash_hex(a) == compute_hash_hex(b)


def test_datetime_uuid_normalization() -> None:
    payload = {
        "ts": datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
        "id": UUID("018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001"),
    }
    payload_again = {
        "id": UUID("018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001"),
        "ts": datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
    }
    assert compute_hash_hex(payload) == compute_hash_hex(payload_again)
