"""Matriz de conformidade da auditoria técnica."""

from __future__ import annotations

from typing import Any, Literal

from services.blockchain_view_service import has_final_ontology_published, is_blockchain_unlocked
from services.cycle_state import is_step_done, status_label
from services.provenance_event_catalog import canonical_event_type

ComplianceStatus = Literal["OK", "Pendente", "Atenção", "Erro", "N/A"]

_COMPLIANCE_ITEMS: list[tuple[str, str, str]] = [
    ("raw_preserved", "Arquivo bruto preservado", "raw_data"),
    ("raw_hash", "Hash SHA-256 gerado", "raw_data"),
    ("wrapper", "Wrapper executado", "wrapper"),
    ("normalized", "Lote normalizado criado", "normalization"),
    ("canonical", "Modelo canônico populado", "ontology"),
    ("semantic", "Validação semântica executada", "semantic"),
    ("calculation", "Cálculo preliminar gerado", "calculation"),
    ("approval", "Aprovação humana registrada", "approval"),
    ("publication", "Versão final publicada", "publication"),
    ("evidence", "Pacote de evidências criado", "evidence"),
    ("merkle", "Merkle Root gerada", "evidence"),
    ("anchoring", "Ancoragem simulada/criada", "blockchain"),
    ("integrity", "Verificação de integridade executada", "verification"),
    ("prov_chain", "Cadeia de proveniência verificada", "verification"),
    ("blockchain_gate", "Blockchain usado apenas após publicação final", "publication"),
]


def _event_present(cycle: dict, *names: str) -> bool:
    types = {e.get("event_type") for e in (cycle.get("provenance_events") or [])}
    canonical = {canonical_event_type(t) for t in types if t}
    for name in names:
        if name in types or canonical_event_type(name) in types or name in canonical:
            return True
    return False


def _step_status(cycle: dict, step_id: str) -> str:
    return (cycle.get("steps") or {}).get(step_id, {}).get("status", "PENDING")


def _evaluate_item(key: str, cycle: dict) -> tuple[ComplianceStatus, str]:
    steps = cycle.get("steps") or {}
    unlocked = is_blockchain_unlocked(cycle)
    published = has_final_ontology_published(cycle)

    if key == "raw_preserved":
        if cycle.get("raw_file") and _step_status(cycle, "raw_data") in {"DONE", "DONE_WARNINGS"}:
            return "OK", "Arquivo original registrado e preservado."
        if cycle.get("raw_file"):
            return "Atenção", "Arquivo presente, etapa de preservação incompleta."
        return "Pendente", "Aguardando upload e preservação do arquivo bruto."

    if key == "raw_hash":
        sha = (cycle.get("raw_file") or {}).get("sha256")
        if sha:
            return "OK", f"Hash SHA-256: {sha[:12]}…"
        return "Pendente", "Hash do arquivo bruto ainda não gerado."

    if key == "wrapper":
        st = _step_status(cycle, "wrapper")
        if st in {"DONE", "DONE_WARNINGS"}:
            return "OK", status_label(st)
        if st == "ERROR":
            return "Erro", "Falha na execução do wrapper."
        return "Pendente", "Wrapper ainda não executado."

    if key == "normalized":
        if cycle.get("normalized_data") and is_step_done(cycle, "normalization"):
            return "OK", f"{len(cycle.get('normalized_data') or [])} registro(s) normalizado(s)."
        if cycle.get("normalized_data"):
            return "Atenção", "Dados normalizados presentes, etapa não concluída."
        return "Pendente", "Lote normalizado ainda não criado."

    if key == "canonical":
        if cycle.get("ontology") and is_step_done(cycle, "ontology"):
            return "OK", "Modelo canônico populado."
        return "Pendente", "Ontologia ainda não populada."

    if key == "semantic":
        st = _step_status(cycle, "semantic")
        if st in {"DONE", "DONE_WARNINGS"}:
            return "OK", status_label(st)
        return "Pendente", "Validação semântica pendente."

    if key == "calculation":
        if cycle.get("calculation") and is_step_done(cycle, "calculation"):
            return "OK", "Resultado preliminar gerado."
        return "Pendente", "Cálculo preliminar ainda não executado."

    if key == "approval":
        approval = cycle.get("approval") or {}
        st = _step_status(cycle, "approval")
        if approval.get("decision") == "APPROVED" or st == "APPROVED":
            return "OK", "Aprovação humana registrada."
        if approval.get("decision") == "REJECTED" or st == "REJECTED":
            return "Erro", "Cálculo reprovado."
        return "Pendente", "Aguardando aprovação humana."

    if key == "publication":
        if published:
            return "OK", "Versão final da ontologia publicada."
        return "Pendente", "Publicação final ainda não concluída."

    if key == "evidence":
        if not unlocked:
            return "N/A", "Blockchain bloqueado — pacote ainda não aplicável."
        pkg = cycle.get("evidence_package") or {}
        if pkg.get("evidence_package_id"):
            return "OK", f"Pacote: {pkg.get('evidence_package_id', '—')}"
        return "Pendente", "Pacote de evidências ainda não criado."

    if key == "merkle":
        if not unlocked:
            return "N/A", "Blockchain bloqueado."
        root = (cycle.get("evidence_package") or {}).get("merkle_root")
        if root:
            return "OK", f"Merkle Root: {root[:16]}…"
        return "Pendente", "Merkle Root ainda não gerada."

    if key == "anchoring":
        if not unlocked:
            return "N/A", "Blockchain bloqueado."
        anchoring = cycle.get("anchoring") or {}
        if anchoring.get("transaction_id") or anchoring.get("status") in {"ANCHORED", "SIMULATED"}:
            mode = anchoring.get("mode", "—")
            return "OK", f"Ancoragem registrada (modo: {mode})."
        return "Pendente", "Ancoragem ainda não executada."

    if key == "integrity":
        if not unlocked:
            return "N/A", "Blockchain bloqueado."
        integrity = cycle.get("integrity") or {}
        if integrity.get("is_valid") is True:
            return "OK", "Integridade verificada — íntegro."
        if integrity.get("is_valid") is False:
            return "Erro", "Divergência detectada na verificação."
        return "Pendente", "Verificação de integridade ainda não executada."

    if key == "prov_chain":
        if _event_present(cycle, "PROVENANCE_CHAIN_VERIFIED"):
            return "OK", "Cadeia de proveniência verificada."
        if _step_status(cycle, "verification") in {"DONE", "VERIFIED"}:
            return "Atenção", "Verificação executada, evento canônico ausente."
        return "Pendente", "Cadeia de proveniência ainda não verificada."

    if key == "blockchain_gate":
        evidence_step = steps.get("evidence") or {}
        blockchain_step = steps.get("blockchain") or {}
        if not published and (evidence_step.get("status") in {"DONE", "DONE_WARNINGS"} or cycle.get("evidence_package")):
            return "Erro", "Evidência blockchain antes da publicação final — violação de gate."
        if not published and blockchain_step.get("status") in {"DONE", "ANCHORED", "VERIFIED"}:
            return "Erro", "Ancoragem antes da publicação final — violação de gate."
        if published and unlocked:
            return "OK", "Gate respeitado — blockchain liberado após publicação."
        if not published:
            return "OK", "Gate respeitado — blockchain bloqueado antes da publicação."
        return "Atenção", "Estado de gate requer revisão."

    return "Pendente", "—"


def build_compliance_matrix(cycle: dict) -> list[dict[str, Any]]:
    """Constrói matriz de conformidade para exibição."""
    rows = []
    for key, label, service_hint in _COMPLIANCE_ITEMS:
        status, note = _evaluate_item(key, cycle)
        rows.append({
            "key": key,
            "item": label,
            "status": status,
            "note": note,
            "service": service_hint,
        })
    return rows


def compliance_summary(cycle: dict) -> dict[str, Any]:
    """Resumo agregado da matriz."""
    matrix = build_compliance_matrix(cycle)
    counts = {"OK": 0, "Pendente": 0, "Atenção": 0, "Erro": 0, "N/A": 0}
    for row in matrix:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    errors = [r for r in matrix if r["status"] == "Erro"]
    pending = [r for r in matrix if r["status"] == "Pendente"]
    return {
        "matrix": matrix,
        "counts": counts,
        "has_errors": bool(errors),
        "has_pending": bool(pending),
        "overall": "Erro" if errors else ("Pendente" if pending else "OK"),
    }
