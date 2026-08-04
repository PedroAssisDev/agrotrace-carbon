"""Leitura de CSV parametrizada pelo layout físico."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def read_csv_rows(
    source_uri: str,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> list[dict[str, Any]]:
    path = source_uri.replace("file://", "").lstrip("/")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fonte não encontrada: {p}")
    with open(p, "r", encoding=encoding, newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))
