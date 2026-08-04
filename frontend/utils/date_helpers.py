"""Helpers de data/hora."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Retorna datetime atual em ISO 8601 com timezone local."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def now_utc() -> datetime:
    """Retorna datetime UTC aware."""
    return datetime.now(timezone.utc)
