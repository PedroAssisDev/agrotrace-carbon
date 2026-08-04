"""RF010 — Correção e atualização de resultados preliminares.

Ciclo acadêmico: revisão → solicitação de correção → alteração → recálculo →
nova versão preliminar → nova revisão.

Correção e recálculo são eventos (append-only), não estados permanentes.
Versões anteriores permanecem imutáveis e consultáveis.
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any

from services.calculation_factor_mapping_service import get_factor_groups_for_formula
from services.calculation_review_service import build_calculation_review, get_review_item
from utils.date_helpers import now_iso

logger = logging.getLogger("agrotrace.correction")


class CorrectionNotAllowedError(ValueError):
    """Correção bloqueada (ex.: resultado já publicado)."""


def _is_published(cycle: dict) -> bool:
    pub = cycle.get("publication") or {}
    if pub.get("status") in {"PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED"}:
        return True
    if pub.get("publication_id") and pub.get("ontology_hash"):
        return True
    step = (cycle.get("steps") or {}).get("publication") or {}
    return step.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"}


def _snapshot_totals(cycle: dict) -> dict[str, Any]:
    calc = cycle.get("calculation") or {}
    flat = calc.get("flat") or {}
    subs = calc.get("subcalculations") or []
    by_formula: dict[str, Any] = {}
    if isinstance(subs, dict):
        items = subs.items()
    else:
        items = (
            (s.get("id") or s.get("formula_id") or f"sub_{i}", s)
            for i, s in enumerate(subs)
            if isinstance(s, dict)
        )
    for key, sub in items:
        if not isinstance(sub, dict):
            continue
        by_formula[str(key)] = {
            "value": sub.get("value") or sub.get("result_kg") or sub.get("total") or sub.get("co2e_kg"),
            "unit": sub.get("unit") or "kg",
            "co2e_kg": sub.get("co2e_kg") or sub.get("co2e_total_kg"),
        }
    flat_keys = (
        "ch4_enteric_kg",
        "ch4_manure_kg",
        "n2o_fertilizer_kg",
        "co2_energy_kg",
        "co2e_total_kg",
    )
    return {
        "co2e_total_kg": calc.get("co2e_total_kg") or flat.get("co2e_total_kg"),
        "preliminary_hash": calc.get("preliminary_hash"),
        "by_formula": by_formula,
        "flat": {k: flat.get(k) for k in flat_keys},
    }


def _ensure_v1(cycle: dict) -> dict:
    """Sintetiza versão v1 a partir do cálculo atual se ainda não houver histórico."""
    versions = list(cycle.get("result_versions") or [])
    if versions:
        return cycle
    calc = cycle.get("calculation")
    if not calc:
        return cycle
    cycle_id = cycle.get("cycle_id") or "cycle"
    v1 = {
        "version_id": f"{cycle_id}-v1",
        "version_number": 1,
        "calculation_result_set_id": cycle.get("calculation_result_set_id"),
        "calculation_execution_id": cycle.get("calculation_execution_id"),
        "prov_entity_id": None,
        "status": "preliminary",
        "supersedes": None,
        "correction_id": None,
        "created_at": (calc.get("computed_at") or now_iso()),
        "totals": _snapshot_totals(cycle),
        "changes": None,
        "calculation_snapshot": {
            "co2e_total_kg": calc.get("co2e_total_kg"),
            "preliminary_hash": calc.get("preliminary_hash"),
            "factors_used": copy.deepcopy(calc.get("factors_used") or {}),
            "flat": copy.deepcopy(calc.get("flat") or {}),
        },
    }
    cycle["result_versions"] = [v1]
    cycle["active_result_version_id"] = v1["version_id"]
    return cycle


def list_result_versions(cycle: dict) -> list[dict[str, Any]]:
    cycle = _ensure_v1(dict(cycle))
    return list(cycle.get("result_versions") or [])


def get_active_version(cycle: dict) -> dict[str, Any] | None:
    versions = list_result_versions(cycle)
    active_id = cycle.get("active_result_version_id")
    if active_id:
        for v in versions:
            if v.get("version_id") == active_id:
                return v
    for v in reversed(versions):
        if v.get("status") != "superseded":
            return v
    return versions[-1] if versions else None


def compare_versions(cycle: dict, version_a: str, version_b: str) -> dict[str, Any]:
    versions = {v["version_id"]: v for v in list_result_versions(cycle)}
    a = versions.get(version_a) or {}
    b = versions.get(version_b) or {}
    ta = (a.get("totals") or {}).get("by_formula") or {}
    tb = (b.get("totals") or {}).get("by_formula") or {}
    keys = sorted(set(ta) | set(tb))
    rows = []
    for k in keys:
        va = (ta.get(k) or {}).get("co2e_kg") or (ta.get(k) or {}).get("value")
        vb = (tb.get(k) or {}).get("co2e_kg") or (tb.get(k) or {}).get("value")
        rows.append({"formula": k, "previous": va, "new": vb, "changed": va != vb})
    return {
        "version_a": version_a,
        "version_b": version_b,
        "previous_total": (a.get("totals") or {}).get("co2e_total_kg"),
        "new_total": (b.get("totals") or {}).get("co2e_total_kg"),
        "rows": rows,
        "previous_hash": (a.get("totals") or {}).get("preliminary_hash"),
        "new_hash": (b.get("totals") or {}).get("preliminary_hash"),
    }


def correctable_fields_for_item(cycle: dict, item_id: str | None = None, formula_id: str | None = None) -> list[dict[str, str]]:
    """Lista campos que podem ser corrigidos para o item/fórmula."""
    item = None
    if item_id or formula_id:
        item = get_review_item(cycle, item_id, formula_id=formula_id)
    fid = (item or {}).get("formula_id") or formula_id or ""
    fields: list[dict[str, str]] = []
    for group in get_factor_groups_for_formula(fid):
        fields.append({"kind": "factor_group", "field": group, "label": f"Fatores: {group}"})
    fields.append({"kind": "activity_data", "field": "normalized_inputs", "label": "Dados de atividade (variáveis)"})
    fields.append({"kind": "parameter", "field": "calculation_params", "label": "Parâmetros de cálculo"})
    return fields


def open_correction_request(
    cycle: dict,
    *,
    target: dict[str, Any] | None = None,
    item_id: str | None = None,
    reviewer: str,
    justification: str,
    correctable_fields: list[dict] | None = None,
) -> dict:
    """Registra solicitação de correção (evento append-only) e marca o item."""
    if not (justification or "").strip():
        raise ValueError("Justificativa obrigatória para solicitar correção.")
    if not (reviewer or "").strip():
        raise ValueError("Autor (revisor) obrigatório para solicitar correção.")
    if _is_published(cycle):
        raise CorrectionNotAllowedError(
            "Resultado já publicado: abra um novo ciclo ou procedimento explícito "
            "para correção. Não é permitido alterar versão publicada in-place."
        )

    from services.calculation_review_service import build_calculation_review
    from services.review_provenance_service import (
        emit_calculation_item_correction_requested,
        emit_calculation_item_reviewed,
    )

    cycle = _ensure_v1(dict(cycle))
    target = dict(target or {})
    if item_id:
        target.setdefault("item_id", item_id)
    item = get_review_item(cycle, target.get("item_id"), formula_id=target.get("formula_id"))
    if item:
        target.setdefault("formula_id", item.get("formula_id"))
        target.setdefault("calculation_item_id", item.get("calculation_item_id"))
    target.setdefault("calculation", "emission_calculation")

    fields = correctable_fields or correctable_fields_for_item(
        cycle, target.get("item_id"), target.get("formula_id")
    )
    active = get_active_version(cycle)
    correction_id = f"CORR-{uuid.uuid4().hex[:12]}"
    correction = {
        "correction_id": correction_id,
        "requested_at": now_iso(),
        "requested_by": reviewer,
        "justification": justification.strip(),
        "target": target,
        "correctable_fields": fields,
        "status": "open",
        "source_version_id": (active or {}).get("version_id"),
        "source_result_set_id": cycle.get("calculation_result_set_id")
        or (active or {}).get("calculation_result_set_id"),
        "applied_at": None,
        "applied_by": None,
        "resulting_version_id": None,
    }
    corrections = list(cycle.get("corrections") or [])
    corrections.append(correction)
    cycle["corrections"] = corrections

    # Marca item sem chamar request_correction (evita recursão)
    tid = target.get("item_id") or target.get("calculation_item_id")
    if tid:
        review = cycle.get("calculation_review") or build_calculation_review(cycle)
        for it in review.get("items") or []:
            if it.get("calculation_item_id") == tid:
                it.update({
                    "status": "CORRECTION_REQUESTED",
                    "review_decision": "CORRECTION_REQUESTED",
                    "reviewed_by": reviewer,
                    "reviewed_at": now_iso(),
                    "justification": justification.strip(),
                })
                break
        from services.calculation_review_service import _compute_summary

        review["summary"] = _compute_summary(review.get("items") or [])
        review["updated_at"] = now_iso()
        cycle["calculation_review"] = review
        emit_calculation_item_correction_requested(cycle, tid, reviewer, justification.strip())
        emit_calculation_item_reviewed(cycle, tid, "CORRECTION_REQUESTED", reviewer)

    try:
        from services import provenance_adapter as prov

        mirror = prov.record_correction_request(cycle, correction)
        correction["provenance"] = mirror
        cycle["corrections"][-1] = correction
    except Exception as exc:
        logger.warning("Espelho de solicitação de correção falhou: %s", exc)

    return cycle


def _find_correction(cycle: dict, correction_id: str) -> dict:
    for c in cycle.get("corrections") or []:
        if c.get("correction_id") == correction_id:
            return c
    raise ValueError(f"Solicitação de correção não encontrada: {correction_id}")


def apply_correction_and_recalculate(
    cycle: dict,
    correction_id: str,
    *,
    changes: dict[str, Any],
    reviewer: str,
) -> dict:
    """Aplica alteração (fator/dado), recalcula, cria nova versão preliminar e reabre revisão."""
    if _is_published(cycle):
        raise CorrectionNotAllowedError(
            "Resultado já publicado: correção in-place bloqueada. Abra um novo ciclo."
        )
    if not (reviewer or "").strip():
        raise ValueError("Autor obrigatório para aplicar correção.")

    cycle = _ensure_v1(dict(cycle))
    correction = _find_correction(cycle, correction_id)
    if correction.get("status") == "applied":
        raise ValueError(f"Correção {correction_id} já foi aplicada.")

    previous_version = get_active_version(cycle)
    previous_totals = copy.deepcopy((previous_version or {}).get("totals") or _snapshot_totals(cycle))
    previous_result_set_id = cycle.get("calculation_result_set_id") or (
        previous_version or {}
    ).get("calculation_result_set_id")

    item_id = (correction.get("target") or {}).get("item_id") or (
        correction.get("target") or {}
    ).get("calculation_item_id")
    change_kind = (changes.get("kind") or "factor_edit").strip()

    cycle["_pending_correction"] = {
        "correction_id": correction_id,
        "supersedes_id": previous_result_set_id,
        "correction_reason": correction.get("justification"),
        "previous_version_id": (previous_version or {}).get("version_id"),
        "previous_totals": previous_totals,
        "changes": changes,
        "reviewer": reviewer,
    }

    from services.calculation_approval_service import apply_factor_edits, apply_variable_swap

    if change_kind == "variable_swap":
        cycle = apply_variable_swap(
            cycle,
            item_id,
            target_variable=changes["target_variable"],
            source_variable=changes.get("source_variable") or changes["target_variable"],
            value=float(changes["value"]),
            reviewer=reviewer,
            ontology_var=changes.get("ontology_var"),
        )
    else:
        edits = changes.get("edits") or []
        if not edits:
            raise ValueError("Informe edits de fatores para aplicar a correção.")
        cycle = apply_factor_edits(
            cycle,
            item_id,
            edits=edits,
            reviewer=reviewer,
            methodology=changes.get("methodology"),
            factors_changed=bool(changes.get("factors_changed", True)),
        )

    # apply_factor_edits já chama run_calculation_step; o hook no orchestrator
    # consome _pending_correction e registra a nova versão.
    pending = cycle.pop("_pending_correction", None)
    if pending and not any(
        v.get("correction_id") == correction_id for v in (cycle.get("result_versions") or [])
    ):
        cycle = register_recalculated_version(cycle, pending)

    # Fecha a solicitação
    for c in cycle.get("corrections") or []:
        if c.get("correction_id") == correction_id:
            c["status"] = "applied"
            c["applied_at"] = now_iso()
            c["applied_by"] = reviewer
            c["resulting_version_id"] = cycle.get("active_result_version_id")
            break

    return cycle


def register_recalculated_version(cycle: dict, pending: dict) -> dict:
    """Registra nova versão preliminar após recálculo (imutável; anterior → superseded)."""
    cycle = _ensure_v1(dict(cycle))
    versions = list(cycle.get("result_versions") or [])
    for v in versions:
        if v.get("status") != "superseded" and v.get("version_id") == pending.get(
            "previous_version_id"
        ):
            v["status"] = "superseded"
        elif v.get("status") == "preliminary" and v.get("version_id") != cycle.get(
            "active_result_version_id"
        ):
            # só a imediatamente anterior ativa
            pass
    # Marca a ativa anterior como superseded
    active_id = cycle.get("active_result_version_id")
    for v in versions:
        if v.get("version_id") == active_id and v.get("status") != "superseded":
            v["status"] = "superseded"

    n = len(versions) + 1
    cycle_id = cycle.get("cycle_id") or "cycle"
    new_version = {
        "version_id": f"{cycle_id}-v{n}",
        "version_number": n,
        "calculation_result_set_id": cycle.get("calculation_result_set_id"),
        "calculation_execution_id": cycle.get("calculation_execution_id"),
        "prov_entity_id": cycle.get("_last_result_prov_entity_id"),
        "status": "preliminary",
        "supersedes": pending.get("previous_version_id") or active_id,
        "correction_id": pending.get("correction_id"),
        "created_at": now_iso(),
        "totals": _snapshot_totals(cycle),
        "changes": pending.get("changes"),
        "previous_totals": pending.get("previous_totals"),
        "calculation_snapshot": {
            "co2e_total_kg": (cycle.get("calculation") or {}).get("co2e_total_kg"),
            "preliminary_hash": (cycle.get("calculation") or {}).get("preliminary_hash"),
            "factors_used": copy.deepcopy(
                (cycle.get("calculation") or {}).get("factors_used") or {}
            ),
            "flat": copy.deepcopy((cycle.get("calculation") or {}).get("flat") or {}),
        },
    }
    versions.append(new_version)
    cycle["result_versions"] = versions
    cycle["active_result_version_id"] = new_version["version_id"]
    return cycle


def mark_active_version_approved(cycle: dict) -> dict:
    """Marca a versão ativa como approved (após finalização)."""
    active_id = cycle.get("active_result_version_id")
    for v in cycle.get("result_versions") or []:
        if v.get("version_id") == active_id:
            v["status"] = "approved"
            v["approved_at"] = now_iso()
    return cycle


def has_open_correction(cycle: dict) -> bool:
    return any(c.get("status") == "open" for c in (cycle.get("corrections") or []))


def has_pending_reapproval(cycle: dict) -> bool:
    review = cycle.get("calculation_review") or {}
    for it in review.get("items") or []:
        if it.get("status") in {"CORRECTION_REQUESTED", "ADJUSTMENT_PENDING_RECALCULATION"}:
            return True
    return has_open_correction(cycle)
