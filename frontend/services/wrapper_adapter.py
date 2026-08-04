"""Adapter para o serviço de wrappers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import config
from config import LAYOUT_OPTIONS, NORMALIZED_DIR
from services import direct_imports as di
from services.result_helpers import decorate_mock
from services.mock_data import mock_wrapper_result
from utils.hash_helpers import sha256_dict

logger = logging.getLogger("agrotrace.wrapper")


def _resolve_layout(layout_name: str) -> str:
    if layout_name in LAYOUT_OPTIONS:
        return LAYOUT_OPTIONS[layout_name]
    if ":" in layout_name:
        return layout_name
    return f"{layout_name}:v1"


def _mock(raw_file_path: str, layout_name: str, period: str, reason: str | None = None) -> dict[str, Any]:
    return decorate_mock(mock_wrapper_result(raw_file_path, _resolve_layout(layout_name), period), reason)


def run_wrapper(raw_file_path: str, layout_name: str, period: str, *, year: int | None = None) -> dict[str, Any]:
    """Executa wrapper real se disponível; caso contrário retorna mock."""
    if config.USE_MOCK_DATA or not config.USE_DIRECT_FUNCTION_CALLS or di.process_file is None:
        return _mock(raw_file_path, layout_name, period)

    try:
        layout_id = _resolve_layout(layout_name)
        kwargs: dict[str, Any] = {}
        if year is not None:
            kwargs["year"] = year
        elif layout_name == "annual" and period and len(str(period)) == 4 and str(period).isdigit():
            kwargs["year"] = int(period)
        result = di.process_file(raw_file_path, layout_id, **kwargs)
        status = getattr(result.processing_status, "value", str(result.processing_status))
        normalized = result.normalized_payload or []
        meta = result.metadata or {}
        rejected = result.rejected_records or []

        out_path = NORMALIZED_DIR / f"{Path(raw_file_path).stem}_normalized.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        logger.debug(
            "[PIPE] wrapper real layout=%s rows_valid=%d rows_rejected=%d period=%s",
            result.layout_id,
            len(normalized),
            len(rejected),
            period,
        )

        return {
            "source": "real",
            "mode": "real",
            "layout_id": result.layout_id,
            "layout_version": result.layout_version,
            "processing_status": status,
            "rows_read": meta.get("rows_read", len(normalized) + len(rejected)),
            "rows_valid": len(normalized),
            "rows_rejected": len(rejected),
            "columns_expected": list((result.canonical_projection or {}).keys())[:20],
            "columns_found": list(normalized[0].keys()) if normalized else [],
            "errors": [r.get("error", str(r)) for r in rejected[:10]],
            "warnings": meta.get("warnings", []),
            "normalized_payload": normalized[:500],
            "canonical_projection": result.canonical_projection or {},
            "normalized_file": str(out_path),
            "content_hash": sha256_dict({"rows": len(normalized), "layout": layout_id}),
            "provenance": {
                "checksum": getattr(result.provenance, "checksum", None) if result.provenance else None,
            },
        }
    except Exception as exc:
        logger.warning("Wrapper real falhou: %s", exc)
        if not config.ALLOW_MOCK_FALLBACK:
            raise
        return _mock(raw_file_path, layout_name, period, reason=str(exc))
