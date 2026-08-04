"""
Vista estável de um layout carregado do YAML — catálogo / governança.

O documento completo permanece no registry; esta classe expõe só metadados
usados pelo núcleo e por ferramentas de extensão.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LayoutDefinition:
    """Metadados do layout (ex.: layout_id ``intraday:v1`` com rótulo ``IntradayLayoutV1``)."""

    layout_id: str
    layout_family: str
    version: str
    status: str
    catalog_display_name: str | None = None

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> LayoutDefinition:
        display = doc.get("catalog_display_name")
        return cls(
            layout_id=str(doc["layout_id"]),
            layout_family=str(doc.get("layout_family") or ""),
            version=str(doc.get("version", "1.0")),
            status=str(doc.get("status", "active")),
            catalog_display_name=str(display).strip() if display else None,
        )
