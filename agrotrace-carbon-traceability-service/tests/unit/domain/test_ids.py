"""Sanity tests for UUID v7 generation."""

from __future__ import annotations

import time
from uuid import UUID

from provenance_service.domain.shared.ids import new_uuid7


def test_new_uuid7_returns_uuid() -> None:
    uid = new_uuid7()
    assert isinstance(uid, UUID)


def test_new_uuid7_is_unique() -> None:
    ids = {new_uuid7() for _ in range(1000)}
    assert len(ids) == 1000


def test_new_uuid7_is_monotonic_when_uuid_utils_available() -> None:
    try:
        import uuid_utils  # noqa: F401
    except ImportError:
        return  # fallback path, monotonia not guaranteed

    a = new_uuid7()
    time.sleep(0.001)
    b = new_uuid7()
    assert a.bytes < b.bytes
