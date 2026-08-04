from __future__ import annotations

from app.domain.services.sha256_service import sha256_hex


def test_official_hash_matches_service_api() -> None:
    """Frontend must use the same official hash function as the service."""
    payload = {"b": 2, "a": 1, "nested": {"z": True, "n": None}}
    first = sha256_hex(payload)
    second = sha256_hex({"nested": {"n": None, "z": True}, "a": 1, "b": 2})
    assert first == second
    assert first.startswith("0x")
    assert len(first) == 66
