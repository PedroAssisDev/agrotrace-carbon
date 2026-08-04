"""
Mapeamento canônico — projeção configurável (layout → vocabulário canônico intermediário).
"""

from __future__ import annotations

from typing import Any


class CanonicalMappingEngine:
    def project_record(self, record: dict[str, Any], projections: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for p in projections:
            logical = p.get("logical")
            target = p.get("target")
            if not logical or not target:
                continue
            if logical in record and not str(logical).startswith("_"):
                out[target] = record[logical]
        return out

    def project_batch(
        self,
        records: list[dict[str, Any]],
        projections: list[dict[str, Any]],
        *,
        layout_family: str | None = None,
        layout_id: str | None = None,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "projections": [self.project_record(r, projections) for r in records],
        }
        if layout_family is not None:
            out["layout_family"] = layout_family
        if layout_id is not None:
            out["layout_id"] = layout_id
        return out
