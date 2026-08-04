"""Helpers de hash para artefatos do protótipo.

Official evidence package / item hashes MUST use the blockchain-service
canonicalization (`json_canonical_v1`) via `services.direct_imports.sha256_hex`
or hashes already returned by the service.

There is **no** compact-JSON fallback for official hashes (RN-06 / RNF004).
Use ``ui_preview_hash`` only for mock/display data that never enters evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class CanonicalizationUnavailableError(RuntimeError):
    """Official canonicalization could not be loaded — fail closed."""


def sha256_file(path: str | Path) -> str:
    """Calcula SHA-256 hex de um arquivo (sem prefixo 0x — hash de arquivo bruto)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(content: bytes) -> str:
    """Calcula SHA-256 hex de bytes em memória (sem prefixo 0x)."""
    return hashlib.sha256(content).hexdigest()


def sha256_text(text: str) -> str:
    """Calcula SHA-256 hex de uma string (sem prefixo 0x)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(data: dict[str, Any]) -> str:
    """Hash oficial de dict via ``json_canonical_v1`` (prefixo ``0x``).

    Raises ``CanonicalizationUnavailableError`` if the blockchain-service
    implementation cannot be loaded. Never falls back to compact JSON.
    """
    return official_package_hash(data)


def official_package_hash(payload: dict[str, Any]) -> str:
    """Compute official evidence hash via blockchain-service canonicalization."""
    from services import direct_imports as di

    if di.sha256_hex is None:
        raise CanonicalizationUnavailableError(
            "blockchain-service sha256_hex unavailable for official hash "
            "(json_canonical_v1 required; no alternate algorithm)"
        )
    try:
        return di.sha256_hex(payload)
    except Exception as exc:
        raise CanonicalizationUnavailableError(
            f"official json_canonical_v1 hash failed: {type(exc).__name__}"
        ) from exc


def ui_preview_hash(data: dict[str, Any]) -> str:
    """Non-official compact JSON hash for mocks/UI previews only.

    Must never be used for evidence packages, publication hashes that feed
    blockchain, or integrity verification.
    """
    canonical = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return sha256_text(canonical)


def truncate_hash(value: str, length: int = 12) -> str:
    """Trunca hash para exibição."""
    if not value:
        return "—"
    if value.startswith("0x"):
        return value[: length + 2] + "…"
    return value[:length] + "…"
