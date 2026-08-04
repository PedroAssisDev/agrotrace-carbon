"""Envelope padronizado para retornos de adapters (incremental)."""

from __future__ import annotations

from typing import Any


def ok(data: dict | None = None, mode: str = "real", **extra: Any) -> dict[str, Any]:
    """Retorno de sucesso com compatibilidade source/mode."""
    payload = dict(data or {})
    payload.setdefault("mode", mode)
    payload.setdefault("source", mode)
    payload.update(extra)
    return payload


def fail(
    message: str,
    mode: str = "mock",
    fallback_reason: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Retorno de falha/fallback explícito."""
    out: dict[str, Any] = {
        "mode": mode,
        "source": mode,
        "error": message,
        "success": False,
    }
    if fallback_reason:
        out["fallback_reason"] = fallback_reason
    out.update(extra)
    return out


def decorate_mock(base: dict, reason: str | None = None) -> dict[str, Any]:
    """Marca dict mock com mode/source e motivo opcional."""
    out = dict(base)
    out["mode"] = "mock"
    out["source"] = "mock"
    if reason:
        out["fallback_reason"] = reason
    return out
