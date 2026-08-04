"""Time helpers. Always tz-aware UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return current time as a tz-aware UTC datetime."""
    return datetime.now(tz=UTC)
