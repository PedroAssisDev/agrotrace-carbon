"""
Harmonização declarativa — passos YAML aplicados após normalização.
"""

from __future__ import annotations

from typing import Any


def strip_whitespace_strings(record: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    out = dict(record)
    if fields:
        for f in fields:
            v = out.get(f)
            if isinstance(v, str):
                out[f] = v.strip()
        return out
    for k, v in list(out.items()):
        if k.startswith("_"):
            continue
        if isinstance(v, str):
            out[k] = v.strip()
    return out


def apply_layout_harmonization(layout_doc: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Aplica passos simples de harmonização declarados no layout.

    Atualmente suporta somente `strip_whitespace_strings`.
    """
    spec = layout_doc.get("harmonization")
    if not isinstance(spec, dict):
        return record
    steps = spec.get("steps")
    if not isinstance(steps, list):
        return record

    out = record
    for step in steps:
        if not isinstance(step, dict):
            continue
        ref = step.get("ref")
        if ref != "strip_whitespace_strings":
            continue
        fields = step.get("fields")
        if fields is not None and not isinstance(fields, list):
            fields = None
        out = strip_whitespace_strings(out, fields)
    return out
