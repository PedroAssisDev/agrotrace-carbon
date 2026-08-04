"""Modelos de dominio do servico save-file."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RetrievedOriginal:
    """Resultado da recuperacao do artefato bruto original (RF002)."""

    content: bytes
    original_filename: str
    content_type: str
    size: int
    uploaded_at: str
    cycle_id: str | None
    artifact_id: str | None
    registered_sha256: str
    recomputed_sha256: str
    verification_status: str
    property_id: str | None = None
    reporting_period: str | None = None
    file_extension: str | None = None
    source_system: str | None = None

    def to_safe_dict(self, *, include_content: bool = False) -> dict[str, Any]:
        """DTO serializavel sem caminhos absolutos."""
        data = asdict(self)
        if not include_content:
            data.pop("content", None)
        return data
