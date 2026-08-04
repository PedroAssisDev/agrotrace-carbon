"""Tabelas de fatores e parâmetros para a tela de Cálculos de Emissão."""

from __future__ import annotations

from typing import Any

from services.calculation_view_service import build_calculation_parameters, build_factor_tables

_STATUS_LABELS = {
    "FOUND": "Importado",
    "DEFAULT_ASSUMED": "Default",
    "MISSING_ZERO": "Ausente (zero)",
    "fallback_defaults": "Fallback",
    "empty_inputs": "Sem entradas",
    "normalized_data": "Dado real",
    "mock": "Simulado",
    "real": "Real",
    "manual": "Edição manual",
}


def _status_label(status: str | None) -> str:
    if not status:
        return "—"
    return _STATUS_LABELS.get(status, status)


def build_factor_view(cycle: dict) -> dict[str, Any]:
    """Monta blocos de fatores com origem e metodologia."""
    calc = cycle.get("calculation") or {}
    if not calc:
        return {"blocks": [], "has_factors": False, "methodology": None, "legacy_schema": True}

    params = build_calculation_parameters(cycle)
    blocks = build_factor_tables(cycle)
    input_resolution = calc.get("input_resolution") or (calc.get("inputs") or {}).get("input_resolution") or []
    resolution_by_slot = {r.get("slot"): r for r in input_resolution if isinstance(r, dict)}

    enriched_blocks: list[dict[str, Any]] = []
    for block in blocks:
        rows = []
        for row in block.get("rows") or []:
            slot = row.get("key") or row.get("label")
            res = resolution_by_slot.get(slot) or {}
            rows.append({
                **row,
                "parametro": row.get("label") or row.get("key"),
                "valor": row.get("value"),
                "origem": _status_label(res.get("status") or calc.get("data_source") or calc.get("mode")),
                "unidade": res.get("unit", "—"),
                "is_default": res.get("status") in {"DEFAULT_ASSUMED", "MISSING_ZERO"},
            })
        enriched_blocks.append({
            "group": block.get("group"),
            "title": block.get("title"),
            "rows": rows,
        })

    temporal_block = {
        "group": "temporal",
        "title": "Temporalidade",
        "rows": [
            {
                "parametro": "Escopo temporal",
                "valor": (params.get("temporal") or {}).get("scope", "—"),
                "origem": "Pipeline",
                "unidade": "—",
                "is_default": False,
            },
            {
                "parametro": "Dias no período",
                "valor": (params.get("temporal") or {}).get("days_in_period", "—"),
                "origem": "Pipeline",
                "unidade": "dias",
                "is_default": False,
            },
            {
                "parametro": "Prorratação automática",
                "valor": "Sim" if (params.get("temporal") or {}).get("auto_prorate_factors") else "Não",
                "origem": "Pipeline",
                "unidade": "—",
                "is_default": False,
            },
        ],
    }
    if params.get("temporal"):
        enriched_blocks.append(temporal_block)

    has_factors = bool(enriched_blocks) or bool(calc.get("factors_used"))
    legacy = not calc.get("factors_used") and not calc.get("inputs")

    return {
        "blocks": enriched_blocks,
        "has_factors": has_factors,
        "methodology": params.get("methodology"),
        "method_code": params.get("method_code"),
        "method_version": params.get("method_version"),
        "calculation_version": params.get("calculation_version"),
        "legacy_schema": legacy,
        "data_source": calc.get("data_source") or calc.get("source"),
        "mode": calc.get("mode"),
    }


def build_input_resolution_table(cycle: dict) -> list[dict[str, Any]]:
    """Tabela de resolução de entradas (encontrado/ausente/default)."""
    calc = cycle.get("calculation") or {}
    rows = calc.get("input_resolution") or (calc.get("inputs") or {}).get("input_resolution") or []
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out.append({
            "slot": r.get("slot"),
            "variavel": r.get("variable"),
            "valor": r.get("value"),
            "unidade": r.get("unit"),
            "status": r.get("status"),
            "origem": _status_label(r.get("status") or r.get("source")),
            "is_default": r.get("status") in {"DEFAULT_ASSUMED", "MISSING_ZERO"},
        })
    return out
