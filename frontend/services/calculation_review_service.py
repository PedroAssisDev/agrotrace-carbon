"""Serviço de revisão de cálculos por arquivo/ciclo."""

from __future__ import annotations

import uuid
from typing import Any

from services.calculation_view_service import build_subcalculations
from utils.date_helpers import now_iso
from utils.formatting import format_co2e, format_co2e_t, format_number
from utils.hash_helpers import sha256_dict, truncate_hash

# Itens obrigatórios de revisão (formula_id -> subcalculation id)
# Intensidade é derivada do total — não exige aprovação humana separada.
REVIEW_EXCLUDED_FORMULA_IDS = frozenset({"intensity_co2e_per_liter"})

MANDATORY_FORMULAS: list[dict[str, str]] = [
    {"formula_id": "enteric_fermentation_ch4", "sub_id": "enteric", "name": "Fermentação entérica — CH₄", "gas": "CH4", "category": "Emissões", "source": "Fermentação entérica"},
    {"formula_id": "manure_management_ch4", "sub_id": "manure", "name": "Manejo de dejetos — CH₄", "gas": "CH4", "category": "Emissões", "source": "Manejo de dejetos"},
    {"formula_id": "fertilizer_n2o", "sub_id": "fertilizer", "name": "Fertilizantes — N₂O", "gas": "N2O", "category": "Emissões", "source": "Fertilizantes"},
    {"formula_id": "energy_co2", "sub_id": "energy", "name": "Energia — CO₂", "gas": "CO2", "category": "Emissões", "source": "Energia"},
    {"formula_id": "total_ghg_co2e", "sub_id": "total", "name": "Total GEE — CO₂e", "gas": "CO2e", "category": "Total", "source": "Agregado"},
]

APPROVED_STATUSES = {
    "APPROVED", "APPROVED_WITH_ZERO", "APPROVED_WITH_MANUAL_ADJUSTMENT",
}
DECIDED_STATUSES = APPROVED_STATUSES | {"REJECTED", "CORRECTION_REQUESTED", "NOT_APPLICABLE"}
PENDING_STATUSES = {"AWAITING_REVIEW", "COM_ZERO_ASSUMIDO", "ADJUSTMENT_PENDING_RECALCULATION"}


def _default_item_methodology(cycle: dict) -> str:
    from services.calculation_factor_mapping_service import get_default_factor_methodology
    return get_default_factor_methodology(cycle)


def stable_item_id(formula_id: str) -> str:
    """ID estável por fórmula — evita mismatch entre layout e callbacks."""
    return f"CI-{formula_id}"


def _display_for_result(result_kg: float | None, unit: str, gas: str) -> tuple[float | None, str]:
    """Formata valor/unidade para exibição (conversão visual kg CO2e -> t CO2e)."""
    if result_kg is None:
        return None, unit
    if gas == "CO2e" and unit == "kg CO2e" and result_kg >= 1000:
        return round(result_kg / 1000, 4), "t CO₂e"
    return result_kg, unit


def _sub_by_id(cycle: dict) -> dict[str, dict]:
    subs = build_subcalculations(cycle)
    return {s.get("id"): s for s in subs if s.get("id")}


def _detect_missing_and_zeros(cycle: dict, formula_id: str, sub: dict | None) -> tuple[list[dict], list[dict]]:
    """Detecta variáveis ausentes e zeros assumidos para um item."""
    from services.calculation_input_mapping_service import (
        get_required_variables,
        resolve_input_variables,
    )

    required = get_required_variables(formula_id)
    found, missing = resolve_input_variables(cycle, required)
    zero_assumptions: list[dict] = []
    for m in missing:
        zero_assumptions.append({
            "variable": m.get("variable"),
            "expected_unit": m.get("expected_unit"),
            "value_used": 0,
            "reason": "dado não encontrado no arquivo importado",
            "status": "requires_confirmation",
            "confirmed": False,
        })
    # Zero explícito quando resultado é 0 mas havia missing
    if sub and (sub.get("result_kg") or 0) == 0 and missing:
        pass  # already in zero_assumptions
    return found, zero_assumptions


def _item_status_from_zeros(zero_assumptions: list[dict], existing_status: str | None) -> str:
    if existing_status and existing_status not in ("AWAITING_REVIEW", "COM_ZERO_ASSUMIDO"):
        return existing_status
    unconfirmed = [z for z in zero_assumptions if not z.get("confirmed")]
    if unconfirmed:
        return "COM_ZERO_ASSUMIDO"
    return existing_status or "AWAITING_REVIEW"


def _build_review_item(
    cycle: dict,
    spec: dict[str, str],
    sub: dict | None,
    existing: dict | None = None,
) -> dict[str, Any]:
    """Constrói um item de revisão a partir de subcálculo."""
    calc = cycle.get("calculation") or {}
    result_kg = sub.get("result_kg") if sub else 0.0
    unit = (sub or {}).get("unit", "—")
    gas = spec["gas"]
    display_val, display_unit = _display_for_result(result_kg, unit, gas)

    from services.calculation_input_mapping_service import get_required_variables, resolve_input_variables

    required = get_required_variables(spec["formula_id"])
    input_vars, missing_vars = resolve_input_variables(cycle, required)
    zero_assumptions = []
    for m in missing_vars:
        zero_assumptions.append({
            "variable": m.get("variable"),
            "expected_unit": m.get("expected_unit"),
            "value_used": 0,
            "reason": "dado não encontrado no arquivo importado",
            "status": "requires_confirmation",
            "confirmed": False,
        })

    item_id = (existing or {}).get("calculation_item_id") or stable_item_id(spec["formula_id"])
    status = _item_status_from_zeros(zero_assumptions, (existing or {}).get("status"))

    if result_kg == 0 and not sub and not missing_vars:
        status = "NOT_APPLICABLE" if not existing else (existing.get("status") or "NOT_APPLICABLE")

    item = {
        "calculation_item_id": item_id,
        "formula_id": spec["formula_id"],
        "sub_id": spec["sub_id"],
        "formula_name": spec["name"],
        "category": spec["category"],
        "gas": gas,
        "source": spec["source"],
        "result_value": result_kg,
        "result_unit": unit,
        "display_value": display_val,
        "display_unit": display_unit,
        "co2e_kg": (sub or {}).get("co2e_kg"),
        "required_variables": required,
        "input_variables": input_vars,
        "missing_variables": missing_vars,
        "zero_assumptions": (existing or {}).get("zero_assumptions") or zero_assumptions,
        "manual_adjustments": (existing or {}).get("manual_adjustments") or [],
        "status": status,
        "review_decision": (existing or {}).get("review_decision"),
        "reviewed_by": (existing or {}).get("reviewed_by"),
        "reviewed_at": (existing or {}).get("reviewed_at"),
        "justification": (existing or {}).get("justification"),
        "factor_methodology": (existing or {}).get("factor_methodology") or {
            "default": _default_item_methodology(cycle),
            "applied": None,
        },
        "result_hash": sha256_dict({
            "formula_id": spec["formula_id"],
            "result_kg": result_kg,
            "unit": unit,
        })[:16],
        "formula": (sub or {}).get("formula", "—"),
    }
    return item


def _compute_summary(items: list[dict]) -> dict[str, int]:
    summary = {
        "total_items": len(items),
        "approved_items": 0,
        "pending_items": 0,
        "rejected_items": 0,
        "items_with_zero": 0,
        "items_with_manual_adjustment": 0,
        "correction_requested": 0,
    }
    for it in items:
        st = it.get("status", "AWAITING_REVIEW")
        if st in APPROVED_STATUSES:
            summary["approved_items"] += 1
        elif st in ("REJECTED",):
            summary["rejected_items"] += 1
        elif st == "CORRECTION_REQUESTED":
            summary["correction_requested"] += 1
        elif st in PENDING_STATUSES or st == "AWAITING_REVIEW":
            summary["pending_items"] += 1
        if it.get("zero_assumptions"):
            summary["items_with_zero"] += 1
        if it.get("manual_adjustments"):
            summary["items_with_manual_adjustment"] += 1
    return summary


def build_calculation_review(cycle: dict, *, preserve_decisions: bool = True) -> dict[str, Any]:
    """Cria ou atualiza calculation_review a partir do resultado preliminar."""
    if not cycle.get("cycle_id") or not cycle.get("calculation"):
        return {}

    existing_review = cycle.get("calculation_review") or {}
    existing_items = {}
    if preserve_decisions and existing_review.get("items"):
        existing_items = {it.get("formula_id"): it for it in existing_review["items"]}

    subs = _sub_by_id(cycle)
    items: list[dict] = []
    for spec in MANDATORY_FORMULAS:
        sub = subs.get(spec["sub_id"])
        prev = existing_items.get(spec["formula_id"])
        items.append(_build_review_item(cycle, spec, sub, prev))

    raw = cycle.get("raw_file") or {}
    review = {
        "file_review_id": existing_review.get("file_review_id") or f"FR-{uuid.uuid4().hex[:10].upper()}",
        "cycle_id": cycle.get("cycle_id"),
        "raw_file_hash": raw.get("sha256") or existing_review.get("raw_file_hash"),
        "status": existing_review.get("status") or "AWAITING_REVIEW",
        "items": items,
        "summary": _compute_summary(items),
        "updated_at": now_iso(),
    }
    return review


def ensure_calculation_review(cycle: dict) -> dict:
    """Garante que o ciclo tenha calculation_review; retorna ciclo atualizado."""
    if not cycle.get("calculation"):
        return cycle
    review = build_calculation_review(cycle)
    if review:
        cycle["calculation_review"] = review
    return cycle


def list_review_items(cycle: dict) -> list[dict]:
    review = cycle.get("calculation_review") or build_calculation_review(cycle)
    items = review.get("items") or []
    return [it for it in items if it.get("formula_id") not in REVIEW_EXCLUDED_FORMULA_IDS]


def get_review_item(cycle: dict, item_id: str | None, *, formula_id: str | None = None) -> dict | None:
    if not item_id and not formula_id:
        return None
    items = list_review_items(cycle)
    if item_id:
        for it in items:
            if it.get("calculation_item_id") == item_id:
                return it
    if formula_id:
        for it in items:
            if it.get("formula_id") == formula_id:
                return it
    return None


def get_review_item_by_formula(cycle: dict, formula_id: str) -> dict | None:
    for it in list_review_items(cycle):
        if it.get("formula_id") == formula_id:
            return it
    return None


def build_review_summary_cards(cycle: dict) -> dict[str, Any]:
    """Resumo para cards da UI."""
    review = cycle.get("calculation_review") or build_calculation_review(cycle)
    s = review.get("summary") or {}
    return {
        "total": s.get("total_items", 0),
        "approved": s.get("approved_items", 0),
        "pending": s.get("pending_items", 0),
        "with_zero": s.get("items_with_zero", 0),
        "manual_adjustments": s.get("items_with_manual_adjustment", 0),
        "rejected": s.get("rejected_items", 0),
        "correction": s.get("correction_requested", 0),
    }


def resolve_file_review_status(cycle: dict) -> str:
    review = cycle.get("calculation_review") or {}
    if review.get("status") in ("APPROVED", "APPROVED_WITH_ZERO_ASSUMPTIONS", "APPROVED_WITH_MANUAL_ADJUSTMENTS", "REJECTED"):
        return review["status"]
    items = review.get("items") or list_review_items(cycle)
    if not items:
        return "AWAITING_REVIEW"
    if any(it.get("status") == "REJECTED" for it in items):
        return "HAS_REJECTED"
    if any(it.get("status") == "CORRECTION_REQUESTED" for it in items):
        return "CORRECTION_REQUESTED"
    if all(it.get("status") in DECIDED_STATUSES for it in items):
        return "READY_FOR_FINAL"
    return "AWAITING_REVIEW"


def format_item_result_display(item: dict) -> str:
    """Formata resultado para tabela."""
    val = item.get("display_value")
    unit = item.get("display_unit") or item.get("result_unit", "")
    if val is None:
        return "—"
    if unit == "t CO₂e":
        return format_co2e_t(val * 1000) if val else "—"
    if "CO2e" in unit or "CO₂e" in unit:
        return format_co2e(val)
    return f"{format_number(val)} {unit}".strip()


def build_file_summary(cycle: dict) -> dict[str, Any]:
    """Resumo do arquivo para card."""
    raw = cycle.get("raw_file") or {}
    wrapper = cycle.get("wrapper") or {}
    calc = cycle.get("calculation") or {}
    mode = calc.get("mode") or calc.get("source") or "—"
    if cycle.get("demo_mode"):
        mode = "mock"

    ont = cycle.get("ontology") or {}
    canon_vars = ont.get("canonical_variables") or []

    return {
        "filename": raw.get("original_filename") or cycle.get("cycle_id", "—"),
        "farm": cycle.get("property_name", "—"),
        "period": cycle.get("reporting_period", "—"),
        "layout": wrapper.get("layout_id") or cycle.get("layout_id", "—"),
        "hash_short": truncate_hash(raw.get("sha256") or "", 12),
        "hash_full": raw.get("sha256"),
        "pipeline_status": cycle.get("current_status", "—"),
        "review_status": resolve_file_review_status(cycle),
        "data_mode": mode,
        "rows_read": wrapper.get("rows_read", 0),
        "rows_valid": wrapper.get("rows_valid", 0),
        "rows_rejected": wrapper.get("rows_rejected", 0),
        "warnings_count": len(cycle.get("warnings") or []),
        "ontology_version": ont.get("ontology_version", "—"),
        "ontology_hash_short": truncate_hash(ont.get("ontology_hash") or "", 12),
        "ontology_hash_full": ont.get("ontology_hash"),
        "ontology_entities": ont.get("entities_created", 0),
        "canonical_var_count": len(canon_vars),
        "ontology_status": ont.get("publication_status", "—"),
    }


def build_review_table_rows(cycle: dict) -> list[dict]:
    """Linhas para tabela de cálculos revisáveis."""
    rows = []
    for it in list_review_items(cycle):
        zeros = len(it.get("zero_assumptions") or [])
        missing = len(it.get("missing_variables") or [])
        rows.append({
            "calculation_item_id": it.get("calculation_item_id"),
            "formula_id": it.get("formula_id"),
            "calculo": it.get("formula_name"),
            "resultado": format_item_result_display(it),
            "unidade": it.get("display_unit") or it.get("result_unit"),
            "variaveis": len(it.get("input_variables") or []),
            "zeros": zeros or missing,
            "status": it.get("status", "AWAITING_REVIEW"),
        })
    return rows


def build_file_select_rows(cycles: list[dict]) -> list[dict]:
    """Linhas para seletor de arquivo/ciclo."""
    from services.cycle_status_service import resolve_managerial_status

    rows = []
    for c in cycles:
        if not c.get("calculation"):
            continue
        review = c.get("calculation_review") or build_calculation_review(c)
        s = review.get("summary") or {}
        raw = c.get("raw_file") or {}
        st = resolve_managerial_status(c)
        rows.append({
            "cycle_id": c.get("cycle_id"),
            "arquivo": raw.get("original_filename") or c.get("cycle_id"),
            "fazenda": c.get("property_name"),
            "periodo": c.get("reporting_period"),
            "layout": (c.get("wrapper") or {}).get("layout_id", "—"),
            "hash": truncate_hash(raw.get("sha256") or "", 8),
            "pipeline_status": st.label,
            "review_status": resolve_file_review_status(c),
            "total_calculos": s.get("total_items", 0),
            "aprovados": s.get("approved_items", 0),
            "pendentes": s.get("pending_items", 0),
            "com_zero": s.get("items_with_zero", 0),
        })
    return rows
