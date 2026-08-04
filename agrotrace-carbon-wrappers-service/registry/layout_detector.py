"""
Deteção heurística de layout a partir do cabeçalho do ficheiro e metadados declarativos.

Usa `physical.delimiter` e `schema` de cada layout registado. Para layouts
`snake_case_headers`, compara cabeçalhos normalizados com `to_snake_case`.
"""

from __future__ import annotations

from pathlib import Path

from ..core.field_mapping import (
    header_set_from_line,
    score_alias_layout,
    score_snake_case_layout,
)
from .file_registry import LayoutRegistry, default_registry


def _layout_detection_threshold(layout_doc: dict, *, default: float) -> float:
    det = layout_doc.get("detection") or {}
    v = det.get("min_score")
    if v is None:
        return default
    return float(v)


def _detection_priority(layout_doc: dict) -> int:
    det = layout_doc.get("detection") or {}
    return int(det.get("priority", 0))


class LayoutDetectionError(RuntimeError):
    """Nenhum layout registado explica o cabeçalho do ficheiro com o limiar configurado."""

    def __init__(self, message: str, *, source_path: str):
        super().__init__(message)
        self.source_path = source_path


def detect_layout_id(
    source_path: Path | str,
    *,
    registry: LayoutRegistry | None = None,
    encoding: str = "utf-8",
    default_min_score: float = 1.0,
) -> str | None:
    """
    Lê a primeira linha não vazia do ficheiro e escolhe o layout com maior score.

    - Layouts com `schema.mode == snake_case_headers`: todos os `schema.required`
      devem aparecer como cabeçalho (após to_snake_case).
    - Demais layouts: cada campo `required: true` deve ter pelo menos um alias presente
      no cabeçalho (tokens normalizados).

    Retorna ``None`` se nenhum layout atingir o limiar declarado ou global.
    """
    reg = registry or default_registry()
    p = Path(source_path)
    if not p.is_file():
        return None

    raw = p.read_text(encoding=encoding)
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0]

    best_id: str | None = None
    best_score = -1.0
    best_priority = -10**9

    for lid in reg.list_layout_ids():
        doc = reg.get(lid)
        physical = doc.get("physical") or {}
        delim = str(physical.get("delimiter", ","))
        header_tokens = header_set_from_line(first, delim)
        schema = doc.get("schema") or {}
        if schema.get("mode") == "snake_case_headers":
            score = score_snake_case_layout(doc, header_tokens)
        else:
            score = score_alias_layout(doc, header_tokens)
        threshold = _layout_detection_threshold(doc, default=default_min_score)
        pri = _detection_priority(doc)
        if score >= threshold:
            if score > best_score or (score == best_score and pri > best_priority):
                best_score = score
                best_priority = pri
                best_id = lid

    return best_id
