"""Helpers de hash para artefatos do protótipo."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    """Calcula SHA-256 hex de um arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """Calcula SHA-256 hex de uma string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(data: dict[str, Any]) -> str:
    """Calcula SHA-256 hex de um dict JSON canônico."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
    return sha256_text(canonical)


def truncate_hash(value: str, length: int = 12) -> str:
    """Trunca hash para exibição."""
    if not value:
        return "—"
    if value.startswith("0x"):
        return value[: length + 2] + "…"
    return value[:length] + "…"
