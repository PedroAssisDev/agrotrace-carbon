"""Inferência de parâmetros a partir da origem (ex.: ano no nome do ficheiro)."""

from __future__ import annotations

import re
from pathlib import Path


def infer_year_from_source_uri(source_uri: str) -> int | None:
    """Extrai um ano plausível (2000–2100) do nome do ficheiro na URI."""
    path = source_uri.replace("file://", "").strip("/")
    match = re.search(r"(\d{4})", Path(path).name)
    if match:
        y = int(match.group(1))
        if 2000 <= y <= 2100:
            return y
    return None
