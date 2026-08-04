"""Status gerencial do ciclo — linguagem de negócio para a UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.blockchain_view_service import is_blockchain_unlocked


@dataclass(frozen=True)
class ManagerialStatus:
    key: str
    label: str
    variant: str
    is_official: bool
    next_action: str | None
    next_href: str | None


_STATUS_DEFS: dict[str, tuple[str, str, bool]] = {
    "no_data": ("Sem dados", "pendente", False),
    "data_imported": ("Dados importados", "dados-reais", False),
    "data_integrated": ("Dados integrados", "dados-reais", False),
    "calculation_pending": ("Pronto para calcular", "pendente", False),
    "calculation_preliminary": ("Cálculo preliminar", "pendente", False),
    "pending_approval": ("Pendente de aprovação", "pendente", False),
    "approved": ("Aprovado", "aprovado", False),
    "rejected": ("Reprovado", "reprovado", False),
    "published": ("Publicado", "aprovado", True),
    "evidence_generated": ("Evidência técnica gerada", "aprovado", True),
    "integrity_verified": ("Integridade verificada", "aprovado", True),
}


def _step_status(cycle: dict, step_id: str) -> str:
    step = (cycle.get("steps") or {}).get(step_id) or {}
    return step.get("status", "PENDING")


def _nested(cycle: dict, key: str) -> dict:
    val = cycle.get(key)
    return val if isinstance(val, dict) else {}


def _has_integrated_data(cycle: dict) -> bool:
    wrapper_ok = _step_status(cycle, "wrapper") in {"DONE", "DONE_WARNINGS"}
    semantic_ok = _step_status(cycle, "semantic") in {"DONE", "DONE_WARNINGS"}
    return wrapper_ok and semantic_ok and bool(cycle.get("normalized_data"))


def resolve_managerial_status(cycle: dict | None) -> ManagerialStatus:
    """Deriva status gerencial a partir do ciclo ativo."""
    if not cycle or not cycle.get("cycle_id"):
        return _pack("no_data", "Importar dados de produção e manejo.", "/data-entry")

    if _nested(cycle, "integrity").get("is_valid") is True:
        return _pack("integrity_verified", None, "/technical-audit")

    if cycle.get("evidence_package"):
        return _pack("evidence_generated", "Consultar auditoria técnica.", "/technical-audit")

    pub = _step_status(cycle, "publication")
    if pub in {"DONE", "DONE_WARNINGS"} or is_blockchain_unlocked(cycle):
        return _pack("published", "Consultar indicadores oficiais.", "/indicators")

    approval = cycle.get("approval") or {}
    approval_step = _step_status(cycle, "approval")
    if approval.get("decision") == "REJECTED" or approval_step == "REJECTED" or cycle.get("current_status") == "REJECTED":
        return _pack("rejected", "Corrigir dados e recalcular.", "/data-entry")

    if approval.get("decision") == "CORRECTION_REQUESTED" or cycle.get("current_status") == "CORRECTION_REQUESTED":
        return _pack("rejected", "Corrigir dados e recalcular.", "/data-entry")

    if approval_step == "APPROVED" or approval.get("decision") == "APPROVED":
        if pub not in {"DONE", "DONE_WARNINGS"}:
            return _pack("approved", "Publicar resultado aprovado.", "/approval")
        return _pack("published", None, "/indicators")

    calc = cycle.get("calculation") or {}
    calc_step = _step_status(cycle, "calculation")
    if calc or calc_step in {"DONE", "DONE_WARNINGS"}:
        if approval_step in {"AWAITING_APPROVAL", "PENDING"} or not approval.get("decision"):
            return _pack("pending_approval", "Revisar e aprovar o cálculo.", "/approval")
        return _pack("calculation_preliminary", "Enviar para revisão.", "/approval")

    if _has_integrated_data(cycle):
        return _pack("calculation_pending", "Executar cálculo de emissões.", "/calculations")

    if _has_integrated_data(cycle) is False and cycle.get("wrapper"):
        return _pack("data_integrated", "Concluir integração semântica.", "/data-entry")

    if cycle.get("raw_file"):
        return _pack("data_imported", "Integrar e validar dados.", "/data-entry")

    return _pack("no_data", "Importar dados de produção e manejo.", "/data-entry")


def _pack(key: str, next_action: str | None, next_href: str | None) -> ManagerialStatus:
    label, variant, is_official = _STATUS_DEFS[key]
    return ManagerialStatus(key, label, variant, is_official, next_action, next_href)


def managerial_status_label(key: str | None) -> str:
    """Rótulo PT do status gerencial a partir da chave (ex.: pending_approval)."""
    if not key:
        return "—"
    entry = _STATUS_DEFS.get(key)
    return entry[0] if entry else key


def count_pending_approval(cycles: list[dict]) -> int:
    n = 0
    for c in cycles:
        st = resolve_managerial_status(c)
        if st.key == "pending_approval":
            n += 1
    return n


def cycles_pending_approval(cycles: list[dict]) -> list[dict]:
    return [c for c in cycles if resolve_managerial_status(c).key == "pending_approval"]


def traceability_summary(cycle: dict | None) -> dict[str, bool]:
    cycle = cycle or {}
    events = cycle.get("provenance_events") or []
    return {
        "traceability_available": len(events) > 0,
        "evidence_generated": bool(cycle.get("evidence_package")),
        "integrity_verified": _nested(cycle, "integrity").get("is_valid") is True,
    }


def mark_pending_approval(cycle: dict) -> dict:
    """Marca ciclo como aguardando revisão humana (sem aprovar)."""
    from services import provenance_adapter
    from services.cycle_state import set_step
    from utils.date_helpers import now_iso
    from utils.file_helpers import save_cycle

    if not cycle.get("calculation"):
        return cycle

    requested_at = now_iso()
    cycle["approval"] = {
        "status": "PendingApproval",
        "reviewer_name": None,
        "reviewer_role": None,
        "decision": None,
        "justification": None,
        "requested_at": requested_at,
        "approved_at": None,
        "rejected_at": None,
    }
    cycle["publication"] = {
        "status": "NotPublished",
        "published_at": None,
        "published_by": None,
        "version": None,
    }
    cycle.pop("evidence_package", None)
    cycle.pop("integrity", None)
    cycle.pop("anchoring", None)
    cycle["hashes"] = {}

    set_step(
        cycle,
        "approval",
        status="AWAITING_APPROVAL",
        summary="Aguardando revisão e aprovação humana.",
    )
    cycle["current_status"] = "AWAITING_HUMAN_APPROVAL"

    if cycle.get("calculation_result_set_id") and cycle.get("reporting_period_id"):
        prov = provenance_adapter.record_review_request(
            cycle["pipeline_run_id"],
            cycle["calculation_result_set_id"],
            cycle["reporting_period_id"],
        )
        set_step(
            cycle,
            "approval",
            status="AWAITING_APPROVAL",
            mode=prov.get("source", "mock"),
            summary="Aguardando revisão e aprovação humana.",
        )

    evt = provenance_adapter.register_provenance_event(
        "HUMAN_APPROVAL_REQUESTED",
        {
            "cycle_id": cycle.get("cycle_id"),
            "pipeline_run_id": cycle.get("pipeline_run_id"),
            "calculation_result_set_id": cycle.get("calculation_result_set_id"),
            "reporting_period_id": cycle.get("reporting_period_id"),
            "status": "PendingApproval",
        },
    )
    cycle.setdefault("provenance_events", []).append(evt)

    save_cycle(cycle)
    return cycle
