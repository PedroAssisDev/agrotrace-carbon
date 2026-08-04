"""Serviço de aprovação por item e finalização de arquivo."""

from __future__ import annotations

import logging
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
from utils.pipeline_logging import ids_from_cycle, log_decision, timed_op

logger = logging.getLogger("agrotrace.approval")


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

    from services.calculation_factor_mapping_service import get_factor_groups_for_formula, resolve_sub_id
    from services.ontology_adapter import confirm_calculation_parameters, get_onto_for_cycle

    groups = get_factor_groups_for_formula(item.get("formula_id") or "")
    if groups:
        cycle = confirm_calculation_parameters(cycle, groups, actor=reviewer)

    try:
        from ontology.result_lifecycle import set_results_status

        onto = get_onto_for_cycle(cycle)
        sub = resolve_sub_id(item)
        formula_map = {
            "enteric": ["enteric_fermentation"],
            "manure": ["manure_management"],
            "fertilizer": ["fertilizer_n2o"],
            "energy": ["energy_co2"],
            "total": ["total_ghg", "intensity"],
        }
        fids = formula_map.get(sub or "", [])
        if fids:
            set_results_status(onto, cycle["cycle_id"], "approved", formula_ids=fids)
    except Exception:
        pass

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

    from services.calculation_factor_mapping_service import get_factor_groups_for_formula
    from services.ontology_adapter import confirm_calculation_parameters

    groups = get_factor_groups_for_formula(item.get("formula_id") or "")
    if groups:
        cycle = confirm_calculation_parameters(cycle, groups, actor=reviewer)

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

    from services.calculation_factor_mapping_service import get_factor_groups_for_formula
    from services.ontology_adapter import confirm_calculation_parameters

    groups = get_factor_groups_for_formula(item.get("formula_id") or "")
    if groups:
        cycle = confirm_calculation_parameters(cycle, groups, actor=reviewer)

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
    """Atualiza observação na ontologia, recalcula e marca item para reaprovação."""
    from services import local_orchestrator
    from services.ontology_result_service import update_activity_observation

    item = _require_item(cycle, item_id)
    ov = ontology_var or target_variable
    swap = {
        "target_variable": target_variable,
        "ontology_var": ov,
        "source_variable": source_variable,
        "value": value,
        "applied_at": now_iso(),
        "applied_by": reviewer,
        "source": "ontology",
    }
    # 1) Persistência oficial da observação corrigida
    update_activity_observation(cycle, variable=ov, value=float(value), reviewer=reviewer)

    # 2) Audit trail operacional (não é fonte do cálculo)
    params = dict(cycle.get("calculation_params") or {})
    params["last_activity_correction"] = swap
    # Remove overrides legados — cálculo deve ler observações da ontologia / normalized sincronizado
    overrides = dict(params.get("input_overrides") or {})
    overrides.pop(ov, None)
    overrides.pop(target_variable, None)
    params["input_overrides"] = overrides
    cycle["calculation_params"] = params

    # Sincroniza normalized_data para o adapter de cálculo (ainda monta FarmPeriodInput dos records)
    records = list(cycle.get("normalized_data") or [])
    if records and isinstance(records[0], dict):
        records[0] = {**records[0], ov: float(value)}
        if target_variable != ov:
            records[0][target_variable] = float(value)
        cycle["normalized_data"] = records
        wrapper = dict(cycle.get("wrapper") or {})
        payload = list(wrapper.get("normalized_payload") or records)
        if payload and isinstance(payload[0], dict):
            payload[0] = {**payload[0], ov: float(value)}
            wrapper["normalized_payload"] = payload
            cycle["wrapper"] = wrapper

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
    """Persiste fatores na ontologia, recalcula a partir do factor_catalog e marca reaprovação."""
    from services import local_orchestrator
    from services.calculation_factor_mapping_service import (
        build_factor_params_from_edits,
        get_default_factor_methodology,
    )
    from services.ontology_adapter import upsert_calculation_parameters

    item = _require_item(cycle, item_id)
    if not edits:
        raise ValueError("Informe ao menos um fator para aplicar.")
    if factors_changed and not (methodology or "").strip():
        raise ValueError("Informe a metodologia dos fatores alterados.")

    default_meth = get_default_factor_methodology(cycle)
    applied_meth = (methodology or "").strip() or default_meth

    # 1) Persistência oficial na ontologia (status corrected) + refresh do catalog
    cycle = upsert_calculation_parameters(
        cycle,
        edits,
        status="corrected",
        actor=reviewer,
    )

    # 2) Audit trail em calculation_params (sem injetar valor cru como fonte do calc)
    params = build_factor_params_from_edits(cycle, edits)
    for edit in edits:
        group = edit.get("group")
        if group and group in params:
            # Remove override numérico: o cálculo deve ler o factor_catalog
            params.pop(group, None)
    cycle["calculation_params"] = params

    change = {
        "type": "factor_edit",
        "source": "ontology",
        "edits": edits,
        "methodology": applied_meth if factors_changed else default_meth,
        "applied_at": now_iso(),
        "applied_by": reviewer,
        "ontology_status": "corrected",
    }
    emit_factor_selection_changed(cycle, item_id, [change])

    # 3) Recálculo a partir do catalog atualizado (sem overrides de fator)
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

    # Parâmetros usados pelas fórmulas aprovadas devem estar confirmed na ontologia
    from services.calculation_factor_mapping_service import get_factor_groups_for_formula
    from services.ontology_adapter import parameters_are_confirmed

    needed_groups: set[str] = set()
    for it in items:
        if it.get("status") in APPROVED_STATUSES:
            needed_groups.update(get_factor_groups_for_formula(it.get("formula_id") or ""))
    if needed_groups:
        ok_params, param_msg = parameters_are_confirmed(cycle, needed_groups)
        if not ok_params:
            return False, f"Parâmetros da ontologia não confirmados: {param_msg}"

    return True, "Todos os cálculos obrigatórios foram decididos."


DECIDED_STATUSES = APPROVED_STATUSES | {"REJECTED", "CORRECTION_REQUESTED", "NOT_APPLICABLE"}


def finalize_file_approval(cycle: dict, *, reviewer: str, justification: str = "") -> dict:
    """Finaliza aprovação do arquivo e dispara publicação se liberado."""
    from services import local_orchestrator

    ok, msg = can_finalize(cycle)
    if not ok:
        log_decision(
            logger,
            "finalize_denied",
            level=logging.WARNING,
            **ids_from_cycle(cycle),
            reason=msg,
            reviewer=reviewer,
        )
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
    log_decision(
        logger,
        "finalize_file",
        **ids_from_cycle(cycle),
        reviewer=reviewer,
        review_status=review_status,
        items_approved=approval["items_approved"],
    )
    with timed_op() as timer:
        cycle = local_orchestrator.run_auto_pipeline_after_approval(cycle, approval)
        log_decision(
            logger,
            "finalize_file.done",
            **ids_from_cycle(cycle),
            status=cycle.get("current_status"),
            duration_ms=timer.duration_ms,
        )
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
