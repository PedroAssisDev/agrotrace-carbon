"""Mapeamento de variáveis de entrada para fórmulas de cálculo (via ontologia)."""

from __future__ import annotations

from typing import Any

from services.ontology_extraction_service import (
    extract_ontology_variables,
    find_ontology_variable,
    origin_label,
)
from services.ontology_indicator_registry import (
    ONTOLOGY_TO_CALC_OVERRIDE,
    get_formula_requirements,
    ontology_class_for,
    ontology_var_aliases,
)
from utils.date_helpers import now_iso


def get_required_variables(formula_id: str) -> list[dict[str, str]]:
    return get_formula_requirements(formula_id)


def extract_normalized_variables(cycle: dict) -> list[dict]:
    """Compat: retorna pool ontológico (substitui leitura direta do normalizado)."""
    return extract_ontology_variables(cycle)


def resolve_input_variables(cycle: dict, required: list[dict]) -> tuple[list[dict], list[dict]]:
    """Resolve variáveis ontológicas encontradas vs ausentes."""
    pool = extract_ontology_variables(cycle)
    found: list[dict] = []
    missing: list[dict] = []

    for req in required:
        ov = req.get("ontology_var") or req.get("variable")
        matched = find_ontology_variable(pool, str(ov))

        if matched:
            found.append({
                **matched,
                "variable": ov,
                "ontology_var": ov,
                "expected_unit": req.get("expected_unit"),
                "ontology_class": matched.get("ontology_class") or ontology_class_for(str(ov)),
                "origin_label": origin_label(matched.get("origin")),
            })
        else:
            missing.append({
                **req,
                "variable": ov,
                "ontology_var": ov,
                "value_used": 0,
                "ontology_class": req.get("ontology_class") or ontology_class_for(str(ov)),
            })

    return found, missing


def list_compatible_alternatives(
    cycle: dict,
    expected_var: str,
    expected_unit: str | None = None,
) -> list[dict]:
    """Lista alternativas compatíveis da mesma classe ontológica."""
    pool = extract_ontology_variables(cycle)
    target_class = ontology_class_for(expected_var)
    alternatives: list[dict] = []

    for v in pool:
        ov = v.get("ontology_var") or v.get("variable")
        if not ov or ov == expected_var:
            continue
        vclass = v.get("ontology_class") or ontology_class_for(str(ov))
        if vclass != target_class:
            continue
        if expected_unit and v.get("unit") and expected_unit != "—":
            if v.get("unit") != expected_unit and target_class not in ("HerdVariable",):
                continue
        alternatives.append({
            "variable": ov,
            "ontology_var": ov,
            "value": v.get("value"),
            "unit": v.get("unit"),
            "origin": v.get("origin"),
            "origin_label": origin_label(v.get("origin")),
            "ontology_class": vclass,
            "compatible": True,
        })

    if not alternatives:
        for alias in ontology_var_aliases(expected_var):
            if alias == expected_var:
                continue
            alt = find_ontology_variable(pool, alias)
            if alt:
                alternatives.append({
                    "variable": alias,
                    "ontology_var": alias,
                    "value": alt.get("value"),
                    "unit": alt.get("unit"),
                    "origin": alt.get("origin"),
                    "origin_label": origin_label(alt.get("origin")),
                    "ontology_class": alt.get("ontology_class"),
                    "compatible": True,
                })

    return alternatives


def build_input_overrides(cycle: dict, swap: dict, *, ontology_var: str | None = None) -> dict[str, Any]:
    """Prepara input_overrides a partir de troca de variável ontológica."""
    overrides = dict((cycle.get("calculation_params") or {}).get("input_overrides") or {})
    target_ov = ontology_var or swap.get("ontology_var") or swap.get("target_variable")
    source_var = swap.get("source_variable")
    value = swap.get("value")

    spec = ONTOLOGY_TO_CALC_OVERRIDE.get(str(target_ov), {})
    kind = spec.get("kind")

    if kind == "headcount":
        hc = dict(overrides.get("headcounts_by_category") or {})
        hc[spec.get("calc_key", target_ov)] = float(value or 0)
        overrides["headcounts_by_category"] = hc
    elif kind == "milk_liters":
        overrides["milk_liters"] = float(value or 0)
    elif kind == "nitrogen_applied_kg":
        overrides["nitrogen_applied_kg"] = float(value or 0)
    elif kind == "energy":
        energy = dict(overrides.get("energy_consumption_by_vector") or {})
        energy[spec.get("calc_key", "Diesel")] = float(value or 0)
        overrides["energy_consumption_by_vector"] = energy
    elif kind == "body_weight":
        bw = dict(overrides.get("body_weight_kg_by_category") or {})
        bw[spec.get("calc_key", "Lactating_Cows")] = float(value or 0)
        overrides["body_weight_kg_by_category"] = bw

    overrides["_last_swap"] = {
        "ontology_var": target_ov,
        "target_variable": target_ov,
        "source_variable": source_var,
        "value": value,
        "applied_at": swap.get("applied_at") or now_iso(),
    }
    return overrides


def build_unit_rows(item: dict) -> list[dict]:
    """Linhas para tabela de unidades do item."""
    rows = []
    for iv in item.get("input_variables") or []:
        rows.append({
            "variavel": iv.get("ontology_var") or iv.get("variable"),
            "classe": iv.get("ontology_class", "—"),
            "valor": iv.get("value"),
            "unidade_entrada": iv.get("unit"),
            "unidade_esperada": iv.get("expected_unit", iv.get("unit")),
            "unidade_exibida": iv.get("unit"),
            "origem": iv.get("origin_label") or origin_label(iv.get("origin")),
        })
    rows.append({
        "variavel": "Resultado",
        "classe": "—",
        "valor": item.get("display_value") or item.get("result_value"),
        "unidade_entrada": item.get("result_unit"),
        "unidade_esperada": item.get("display_unit") or item.get("result_unit"),
        "unidade_exibida": item.get("display_unit") or item.get("result_unit"),
        "origem": "cálculo",
    })
    return rows
