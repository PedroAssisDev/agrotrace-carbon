"""
Mapeamento de cabeçalhos e linhas brutas — lógica compartilhada entre pipeline e detector.

Centraliza aliases, snake_case e scoring de detecção para evitar divergência entre módulos.
"""

from __future__ import annotations

from typing import Any


def to_snake_case(name: str) -> str:
    s = name.strip().replace(" ", "_").replace("-", "_")
    return "_".join(w.lower() for w in s.split("_") if w)


def normalize_header_token(name: str) -> str:
    return to_snake_case(name.strip().strip('"'))


def header_set_from_line(line: str, delimiter: str) -> set[str]:
    parts = [p.strip().strip('"') for p in line.split(delimiter)]
    return {normalize_header_token(p) for p in parts if p}


def map_schema_fields(raw: dict[str, Any], fields_spec: list[dict[str, Any]]) -> dict[str, Any]:
    """Mapeia linha bruta para nomes lógicos usando aliases de cada campo do schema."""
    out: dict[str, Any] = {}
    for spec in fields_spec:
        logical = spec["logical"]
        aliases = spec.get("aliases") or [logical]
        val = None
        for a in aliases:
            if a in raw and raw[a] is not None and str(raw[a]).strip() != "":
                val = raw[a]
                break
        out[logical] = val
    return out


def map_raw_row_to_logical(raw: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Mapeia uma linha física para chaves lógicas conforme o modo do schema."""
    mode = schema.get("mode")
    if mode == "snake_case_headers":
        return {to_snake_case(k): v for k, v in raw.items()}
    fields = schema.get("fields") or []
    return map_schema_fields(raw, fields)


def required_header_tokens_alias_schema(layout_doc: dict[str, Any]) -> list[set[str]]:
    """Por cada campo obrigatório, conjunto de tokens de cabeçalho aceites (normalizados)."""
    schema = layout_doc.get("schema") or {}
    fields = schema.get("fields") or []
    out: list[set[str]] = []
    for spec in fields:
        if not spec.get("required"):
            continue
        aliases = list(spec.get("aliases") or [])
        logical = spec.get("logical")
        if logical:
            aliases.append(logical)
        out.append({normalize_header_token(a) for a in aliases})
    return out


def score_alias_layout(layout_doc: dict[str, Any], header_tokens: set[str]) -> float:
    required_groups = required_header_tokens_alias_schema(layout_doc)
    if not required_groups:
        return 0.0
    matched = 0
    for group in required_groups:
        if header_tokens & group:
            matched += 1
        else:
            return 0.0
    return matched / len(required_groups)


def score_snake_case_layout(layout_doc: dict[str, Any], header_tokens: set[str]) -> float:
    schema = layout_doc.get("schema") or {}
    required = schema.get("required") or []
    if not required:
        return 0.0
    req_set = set(required)
    matched = sum(1 for r in req_set if r in header_tokens)
    if matched < len(req_set):
        return 0.0
    det = layout_doc.get("detection") or {}
    min_cols = int(det.get("min_column_count", 0))
    if min_cols and len(header_tokens) < min_cols:
        return 0.0
    return matched / len(req_set)
