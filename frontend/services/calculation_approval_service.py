"""Serviço de aprovação por item e finalização de arquivo."""

from __future__ import annotations

from typing import Any

from services.calculation_input_mapping_service import build_input_overrides
from services.calculation_review_service import (
    APPROVED_STATUSES,
    build_calculation_review,
    get_review_item,
    resolve_file_review_status,
)
from services.review_provenance_service import (
    emit_calculation_item_approved,
    emit_calculation_item_correction_requested,
    emit_calculation_item_rejected,
    emit_calculation_item_reviewed,
    emit_calculation_item_with_manual_adjustment,
    emit_calculation_item_with_zero,
    emit_factor_selection_changed,
    emit_file_calculation_approved,
    emit_file_calculation_rejected,
    emit_final_approval_ready,
    emit_input_mapping_changed,
    emit_review_started,
    emit_zero_assumption_confirmed,
)
from utils.date_helpers import now_iso


def _update_item(cycle: dict, item_id: str, **fields) -> dict:
    review = cycle.get("calculation_review") or build_calculation_review(cycle)
    for it in review.get("items") or []:
        if it.get("calculation_item_id") == item_id:
            it.update(fields)
            break
    review["summary"] = _recompute_summary(review.get("items") or [])
    review["updated_at"] = now_iso()
    cycle["calculation_review"] = review
    return cycle


def _recompute_summary(items: list[dict]) -> dict[str, int]:
    from services.calculation_review_service import _compute_summary
    return _compute_summary(items)


def _require_item(cycle: dict, item_id: str) -> dict:
    item = get_review_item(cycle, item_id)
    if not item:
        raise ValueError(f"Item de revisão não encontrado: {item_id}")
    return item


def approve_item(cycle: dict, item_id: str, *, reviewer: str, justification: str = "") -> dict:
    item = _require_item(cycle, item_id)
    if item.get("status") == "COM_ZERO_ASSUMIDO":
        unconfirmed = [z for z in (item.get("zero_assumptions") or []) if not z.get("confirmed")]
        if unconfirmed:
            raise ValueError("Confirme os zeros assumidos antes de aprovar.")
    cycle = _update_item(
        cycle, item_id,
        status="APPROVED",
        review_decision="APPROVED",
        reviewed_by=reviewer,
        reviewed_at=now_iso(),
        justification=justification,
    )
    emit_calculation_item_approved(cycle, item_id, reviewer, justification)
    emit_calculation_item_reviewed(cycle, item_id, "APPROVED", reviewer)
    return cycle


def approve_with_zero(cycle: dict, item_id: str, *, reviewer: str, justification: str = "") -> dict:
    item = _require_item(cycle, item_id)
    zeros = item.get("zero_assumptions") or []
    for z in zeros:
        z["confirmed"] = True
        z["status"] = "confirmed"
    cycle = _update_item(
        cycle, item_id,
        zero_assumptions=zeros,
        status="APPROVED_WITH_ZERO",
        review_decision="APPROVED_WITH_ZERO",
        reviewed_by=reviewer,
        reviewed_at=now_iso(),
        justification=justification or "Zero assumido confirmado pelo revisor.",
    )
    emit_zero_assumption_confirmed(cycle, item_id, reviewer)
    emit_calculation_item_with_zero(cycle, item_id, reviewer, justification)
    emit_calculation_item_reviewed(cycle, item_id, "APPROVED_WITH_ZERO", reviewer)
    return cycle


def reject_item(cycle: dict, item_id: str, *, reviewer: str, justification: str) -> dict:
    if not justification:
        raise ValueError("Justificativa obrigatória para rejeição.")
    cycle = _update_item(
        cycle, item_id,
        status="REJECTED",
        review_decision="REJECTED",
        reviewed_by=reviewer,
        reviewed_at=now_iso(),
        justification=justification,
    )
    emit_calculation_item_rejected(cycle, item_id, reviewer, justification)
    emit_calculation_item_reviewed(cycle, item_id, "REJECTED", reviewer)
    return cycle


def request_correction(cycle: dict, item_id: str, *, reviewer: str, justification: str) -> dict:
    if not justification:
        raise ValueError("Justificativa obrigatória para solicitar correção.")
    cycle = _update_item(
        cycle, item_id,
        status="CORRECTION_REQUESTED",
        review_decision="CORRECTION_REQUESTED",
        reviewed_by=reviewer,
        reviewed_at=now_iso(),
        justification=justification,
    )
    emit_calculation_item_correction_requested(cycle, item_id, reviewer, justification)
    emit_calculation_item_reviewed(cycle, item_id, "CORRECTION_REQUESTED", reviewer)
    return cycle


def save_adjustment(
    cycle: dict,
    item_id: str,
    *,
    reviewer: str,
    adjustment: dict,
    justification: str = "",
) -> dict:
    item = _require_item(cycle, item_id)
    adjustments = list(item.get("manual_adjustments") or [])
    adjustments.append({
        **adjustment,
        "saved_by": reviewer,
        "saved_at": now_iso(),
        "justification": justification,
    })
    cycle = _update_item(
        cycle, item_id,
        manual_adjustments=adjustments,
        status="APPROVED_WITH_MANUAL_ADJUSTMENT",
        review_decision="APPROVED_WITH_MANUAL_ADJUSTMENT",
        reviewed_by=reviewer,
        reviewed_at=now_iso(),
        justification=justification,
    )
    emit_calculation_item_with_manual_adjustment(cycle, item_id, reviewer, adjustment)
    emit_calculation_item_reviewed(cycle, item_id, "APPROVED_WITH_MANUAL_ADJUSTMENT", reviewer)
    return cycle


def apply_variable_swap(
    cycle: dict,
    item_id: str,
    *,
    target_variable: str,
    source_variable: str,
    value: float,
    reviewer: str,
    ontology_var: str | None = None,
) -> dict:
    """Aplica troca de variável, recalcula ciclo e marca item para reaprovação."""
    from services import local_orchestrator

    item = _require_item(cycle, item_id)
    ov = ontology_var or target_variable
    swap = {
        "target_variable": target_variable,
        "ontology_var": ov,
        "source_variable": source_variable,
        "value": value,
        "applied_at": now_iso(),
        "applied_by": reviewer,
    }
    params = dict(cycle.get("calculation_params") or {})
    params["input_overrides"] = build_input_overrides(cycle, swap, ontology_var=ov)
    cycle["calculation_params"] = params

    emit_input_mapping_changed(cycle, item_id, swap)

    cycle = local_orchestrator.run_calculation_step(cycle, params)
    review = build_calculation_review(cycle, preserve_decisions=True)
    for it in review.get("items") or []:
        if it.get("calculation_item_id") == item_id or it.get("formula_id") == item.get("formula_id"):
            adjustments = list(it.get("manual_adjustments") or [])
            adjustments.append({"type": "variable_swap", **swap})
            it["manual_adjustments"] = adjustments
            it["status"] = "ADJUSTMENT_PENDING_RECALCULATION"
            it["review_decision"] = None
            it["reviewed_by"] = None
            it["reviewed_at"] = None
    review["summary"] = _recompute_summary(review.get("items") or [])
    cycle["calculation_review"] = review

    from services.cycle_status_service import mark_pending_approval
    cycle = mark_pending_approval(cycle)
    return cycle


def apply_factor_edits(
    cycle: dict,
    item_id: str,
    *,
    edits: list[dict],
    reviewer: str,
    methodology: str | None = None,
    factors_changed: bool = True,
) -> dict:
    """Aplica valores editados de fatores, recalcula ciclo e marca item para reaprovação."""
    from services import local_orchestrator
    from services.calculation_factor_mapping_service import (
        build_factor_params_from_edits,
        get_default_factor_methodology,
    )

    item = _require_item(cycle, item_id)
    if not edits:
        raise ValueError("Informe ao menos um fator para aplicar.")
    if factors_changed and not (methodology or "").strip():
        raise ValueError("Informe a metodologia dos fatores alterados.")

    default_meth = get_default_factor_methodology(cycle)
    applied_meth = (methodology or "").strip() or default_meth

    params = build_factor_params_from_edits(cycle, edits)
    cycle["calculation_params"] = params

    change = {
        "type": "factor_edit",
        "source": "manual",
        "edits": edits,
        "methodology": applied_meth if factors_changed else default_meth,
        "applied_at": now_iso(),
        "applied_by": reviewer,
    }
    emit_factor_selection_changed(cycle, item_id, [change])

    cycle = local_orchestrator.run_calculation_step(cycle, params)
    review = build_calculation_review(cycle, preserve_decisions=True)
    for it in review.get("items") or []:
        if it.get("calculation_item_id") == item_id or it.get("formula_id") == item.get("formula_id"):
            adjustments = list(it.get("manual_adjustments") or [])
            adjustments.append(change)
            it["manual_adjustments"] = adjustments
            if factors_changed:
                it["factor_methodology"] = {
                    "default": default_meth,
                    "applied": applied_meth,
                    "updated_at": now_iso(),
                    "updated_by": reviewer,
                }
            it["status"] = "ADJUSTMENT_PENDING_RECALCULATION"
            it["review_decision"] = None
            it["reviewed_by"] = None
            it["reviewed_at"] = None
    review["summary"] = _recompute_summary(review.get("items") or [])
    cycle["calculation_review"] = review

    from services.cycle_status_service import mark_pending_approval
    cycle = mark_pending_approval(cycle)
    return cycle


def can_finalize(cycle: dict) -> tuple[bool, str]:
    """Verifica se pode finalizar aprovação do arquivo."""
    review = cycle.get("calculation_review") or build_calculation_review(cycle)
    items = review.get("items") or []
    if not items:
        return False, "Nenhum cálculo disponível para revisão."

    for it in items:
        st = it.get("status", "AWAITING_REVIEW")
        if st == "REJECTED":
            return False, "Há cálculo(s) rejeitado(s). Resolva antes de finalizar."
        if st == "CORRECTION_REQUESTED":
            return False, "Há solicitação de correção pendente."
        if st == "ADJUSTMENT_PENDING_RECALCULATION":
            return False, "Há recálculo pendente de reaprovação."
        if st == "COM_ZERO_ASSUMIDO":
            return False, "Confirme zeros assumidos antes de finalizar."
        if st not in DECIDED_STATUSES:
            return False, f"Cálculo '{it.get('formula_name')}' ainda aguarda decisão."

    if any(it.get("status") == "REJECTED" for it in items):
        return False, "Arquivo possui cálculos rejeitados."

    return True, "Todos os cálculos obrigatórios foram decididos."


DECIDED_STATUSES = APPROVED_STATUSES | {"REJECTED", "CORRECTION_REQUESTED", "NOT_APPLICABLE"}


def finalize_file_approval(cycle: dict, *, reviewer: str, justification: str = "") -> dict:
    """Finaliza aprovação do arquivo e dispara publicação se liberado."""
    from services import local_orchestrator
    from services.cycle_status_service import mark_pending_approval

    ok, msg = can_finalize(cycle)
    if not ok:
        raise ValueError(msg)

    review = cycle.get("calculation_review") or {}
    items = review.get("items") or []
    has_zero = any(it.get("status") == "APPROVED_WITH_ZERO" for it in items)
    has_manual = any(it.get("status") == "APPROVED_WITH_MANUAL_ADJUSTMENT" for it in items)

    if has_zero:
        review_status = "APPROVED_WITH_ZERO_ASSUMPTIONS"
    elif has_manual:
        review_status = "APPROVED_WITH_MANUAL_ADJUSTMENTS"
    else:
        review_status = "APPROVED"

    review["status"] = review_status
    review["finalized_by"] = reviewer
    review["finalized_at"] = now_iso()
    review["final_justification"] = justification
    cycle["calculation_review"] = review

    emit_final_approval_ready(cycle, reviewer)
    emit_file_calculation_approved(cycle, reviewer, justification)

    approval = {
        "decision": "APPROVED",
        "approver": reviewer,
        "justification": justification or "Aprovação por cálculo concluída.",
        "calculation_review_id": review.get("file_review_id"),
        "items_approved": len([it for it in items if it.get("status") in APPROVED_STATUSES]),
    }
    cycle = local_orchestrator.run_auto_pipeline_after_approval(cycle, approval)
    return cycle


def reject_file(cycle: dict, *, reviewer: str, justification: str) -> dict:
    if not justification:
        raise ValueError("Justificativa obrigatória.")
    review = cycle.get("calculation_review") or {}
    review["status"] = "REJECTED"
    review["finalized_by"] = reviewer
    review["finalized_at"] = now_iso()
    review["final_justification"] = justification
    cycle["calculation_review"] = review
    emit_file_calculation_rejected(cycle, reviewer, justification)

    from services import local_orchestrator
    approval = {"decision": "REJECTED", "approver": reviewer, "justification": justification}
    return local_orchestrator.run_approval_step(cycle, approval)


def ensure_review_started(cycle: dict, *, reviewer: str = "Sistema") -> dict:
    if not cycle.get("calculation_review"):
        cycle["calculation_review"] = build_calculation_review(cycle)
        emit_review_started(cycle, reviewer)
    return cycle
