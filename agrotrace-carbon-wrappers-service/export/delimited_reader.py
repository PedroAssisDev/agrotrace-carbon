"""
Leitura de texto delimitado com separador multi-caractere (espelho de DelimitedSerializer).

Regras alinhadas à escrita em delimited.py: aspas duplas opcionais, "" como escape
dentro de campo citado, separador literal só fora de aspas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def split_physical_lines(text: str, quote_char: str = '"') -> list[str]:
    """Divide o texto em linhas físicas sem partir conteúdo dentro de aspas."""
    lines: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(text)
    in_quotes = False
    q = quote_char

    while i < n:
        c = text[i]
        if in_quotes:
            if i + 1 < n and c == q and text[i + 1] == q:
                buf.append(q)
                i += 2
                continue
            if c == q:
                in_quotes = False
            buf.append(c)
            i += 1
            continue
        if c == q:
            in_quotes = True
            buf.append(c)
            i += 1
            continue
        if c == "\n":
            lines.append("".join(buf))
            buf = []
            i += 1
            continue
        if c == "\r":
            if i + 1 < n and text[i + 1] == "\n":
                lines.append("".join(buf))
                buf = []
                i += 2
                continue
            lines.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    lines.append("".join(buf))
    return lines


def split_delimited_line(line: str, field_separator: str, quote_char: str = '"') -> list[str]:
    """Divide uma linha em campos usando separador multi-caractere."""
    fields: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(line)
    in_quotes = False
    sep = field_separator
    q = quote_char

    while i < n:
        if in_quotes:
            if i + 1 < n and line[i] == q and line[i + 1] == q:
                buf.append(q)
                i += 2
                continue
            if line[i] == q:
                in_quotes = False
                i += 1
                continue
            buf.append(line[i])
            i += 1
            continue
        if line.startswith(sep, i):
            fields.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        if line[i] == q:
            in_quotes = True
            i += 1
            continue
        buf.append(line[i])
        i += 1
    fields.append("".join(buf))
    return fields


def _maybe_parse_cell(raw: str, *, deserialize_json: bool) -> Any:
    s = raw
    if not deserialize_json:
        return s
    t = s.strip()
    if len(t) >= 2 and t[0] in "[{":
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return s
    return s


def read_delimited_table(
    text: str,
    *,
    field_separator: str = ";_;",
    quote_char: str = '"',
    deserialize_json_cells: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Lê tabela completa: primeira linha = cabeçalhos, restantes = registos.

    Retorna (colunas, linhas como dicts).
    """
    lines = split_physical_lines(text, quote_char=quote_char)
    non_empty = [ln for ln in lines if ln.strip() != ""]
    if not non_empty:
        return [], []

    header_fields = split_delimited_line(non_empty[0], field_separator, quote_char)
    columns = [h.strip() for h in header_fields]
    rows: list[dict[str, Any]] = []

    for ln in non_empty[1:]:
        cells = split_delimited_line(ln, field_separator, quote_char)
        if len(cells) < len(columns):
            cells.extend([""] * (len(columns) - len(cells)))
        elif len(cells) > len(columns):
            cells = cells[: len(columns)]
        row = {
            columns[i]: _maybe_parse_cell(cells[i], deserialize_json=deserialize_json_cells)
            for i in range(len(columns))
        }
        rows.append(row)
    return columns, rows


def read_delimited_file(
    path: Path | str,
    *,
    encoding: str = "utf-8",
    field_separator: str = ";_;",
    quote_char: str = '"',
    deserialize_json_cells: bool = True,
) -> tuple[list[str], list[dict[str, Any]]]:
    p = Path(path)
    text = p.read_text(encoding=encoding)
    return read_delimited_table(
        text,
        field_separator=field_separator,
        quote_char=quote_char,
        deserialize_json_cells=deserialize_json_cells,
    )
