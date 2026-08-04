"""Helpers de hash para artefatos do protótipo.

Official evidence package / item hashes MUST use the blockchain-service
canonicalization (`json_canonical_v1`) via `services.direct_imports.sha256_hex`
or hashes already returned by the service.

Local helpers below are for UI artifact convenience (files/text) and must not
diverge from the official strategy when computing evidence hashes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    """Calcula SHA-256 hex de um arquivo (sem prefixo 0x — hash de arquivo bruto)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Calcula SHA-256 hex de uma string (sem prefixo 0x)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(data: dict[str, Any]) -> str:
    """Hash de dict para UI.

    Prefers the official blockchain-service `sha256_hex` (0x-prefixed,
    json_canonical_v1). Falls back to a local compact JSON hash only when the
    service is unavailable — that fallback is NOT an official evidence hash.
    """
    try:
        from services import direct_imports as di

        if di.sha256_hex is not None:
            return di.sha256_hex(data)
    except Exception as exc:
        import logging

        logging.getLogger("agrotrace.hash").warning(
            "[FAIL] hash.official_unavailable error=%s — using local UI fallback",
            exc,
        )
    # Fallback UI-only (not official evidence canonicalization)
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return sha256_text(canonical)


def official_package_hash(payload: dict[str, Any]) -> str:
    """Compute official evidence hash via blockchain-service canonicalization."""
    from services import direct_imports as di

    if di.sha256_hex is None:
        raise RuntimeError("blockchain-service sha256_hex unavailable for official hash")
    return di.sha256_hex(payload)


def truncate_hash(value: str, length: int = 12) -> str:
    """Trunca hash para exibição."""
    if not value:
        return "—"
    if value.startswith("0x"):
        return value[: length + 2] + "…"
    return value[:length] + "…"
