"""Validação estrutural de manifestos de exportação (governança mínima)."""

from __future__ import annotations

from typing import Any

MANIFEST_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "run_id",
        "layout_id",
        "processing_status",
        "source_uri",
        "field_separator",
        "encoding",
        "paths",
    }
)


def validate_export_manifest(manifest: dict[str, Any]) -> list[str]:
    """Valida chaves mínimas e tipos básicos.

    Retorna lista de mensagens de erro (vazia se OK).
    """
    errors: list[str] = []
    for key in MANIFEST_REQUIRED_KEYS:
        if key not in manifest:
            errors.append(f"manifest em falta: {key!r}")
    paths = manifest.get("paths")
    if paths is not None and not isinstance(paths, dict):
        errors.append("paths deve ser um objeto (dict)")
    if "field_separator" in manifest and not isinstance(manifest.get("field_separator"), str):
        errors.append("field_separator deve ser str")
    return errors
