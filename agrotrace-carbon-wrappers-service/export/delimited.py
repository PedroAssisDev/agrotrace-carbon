"""
Serialização tabular com separador multi-caractere (;_;).

O módulo csv da stdlib Python usa delimitador de um caractere; aqui a regra é
RFC-4180-like com separador customizado e aspas duplas para escape.
"""

from __future__ import annotations

import json
from typing import Any, Iterable


def default_cell_serializer(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


class DelimitedSerializer:
    """Estratégia de exportação: campos separados por `field_separator` (ex.: ;_;)."""

    def __init__(
        self,
        field_separator: str = ";_;",
        quote_char: str = '"',
        cell_serializer: Any = default_cell_serializer,
    ):
        self.field_separator = field_separator
        self.quote_char = quote_char
        self._cell = cell_serializer

    def escape_field(self, raw: str) -> str:
        q = self.quote_char
        sep = self.field_separator
        if sep in raw or q in raw or "\n" in raw or "\r" in raw:
            return q + raw.replace(q, q + q) + q
        return raw

    def format_row(self, values: Iterable[str]) -> str:
        return self.field_separator.join(self.escape_field(v) for v in values)

    def write_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
    ) -> str:
        if not rows:
            cols: list[str] = columns or []
            if not cols:
                return ""
            header = self.format_row(cols)
            return header + "\n"

        cols = columns or sorted({k for r in rows for k in r.keys()})
        lines = [self.format_row(str(c) for c in cols)]
        for r in rows:
            lines.append(self.format_row(self._cell(r.get(c)) for c in cols))
        return "\n".join(lines) + "\n"


class DelimitedExportStrategy:
    """Compatibilidade: use ``DelimitedSerializer`` diretamente."""

    def __init__(self, field_separator: str = ";_;"):
        from ..core.deprecation import warn_secondary_api

        warn_secondary_api("DelimitedExportStrategy", "DelimitedSerializer")
        self._serializer = DelimitedSerializer(field_separator=field_separator)

    def render(self, rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
        return self._serializer.write_table(rows, columns)
