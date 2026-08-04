"""Hashes para o servico save-file (auto-contido, sem dependencia do frontend)."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    """Calcula SHA-256 hex de um arquivo lendo em blocos."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(content: bytes) -> str:
    """Calcula SHA-256 hex de bytes em memoria."""
    return hashlib.sha256(content).hexdigest()
