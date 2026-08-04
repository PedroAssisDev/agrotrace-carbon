"""Snapshots de linha para rastreabilidade e exportação de rejeitados."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def logical_row_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    """Copia campos lógicos (sem chaves internas `_`) com datas serializáveis."""
    out: dict[str, Any] = {}
    for k, v in row.items():
        if k.startswith("_"):
            continue
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, date):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
