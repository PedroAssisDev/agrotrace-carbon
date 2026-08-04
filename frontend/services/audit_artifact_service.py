"""Artefatos do ciclo para auditoria técnica."""

from __future__ import annotations

from typing import Any

from services.blockchain_view_service import build_evidence_summary, is_blockchain_unlocked
from services.data_view_service import build_raw_data_view
from utils.hash_helpers import truncate_hash


_ARTIFACT_GROUPS = [
    ("operational", "Artefatos operacionais"),
    ("semantic", "Artefatos semânticos"),
    ("calculation", "Artefatos de cálculo"),
    ("final", "Artefatos finais"),
    ("blockchain", "Artefatos blockchain"),
]


def _artifact_row(
    name: str,
    artifact_type: str,
    group: str,
    status: str,
    service: str,
    origin: str,
    hash_val: str | None,
    generated_at: str | None,
    mode: str | None,
    *,
    is_preliminary: bool = False,
) -> dict[str, Any]:
    return {
        "artifact": name,
        "type": artifact_type,
        "group": group,
        "group_label": dict(_ARTIFACT_GROUPS).get(group, group),
        "status": status,
        "service": service,
        "origin": origin or "—",
        "hash_short": truncate_hash(hash_val or "", 12),
        "generated_at": generated_at or "—",
        "mode": mode or "—",
        "is_preliminary": is_preliminary,
        "action": "Inspecionar" if status not in {"Ausente", "Pendente"} else "—",
    }


def _step_mode(cycle: dict, step_id: str) -> str | None:
    step = (cycle.get("steps") or {}).get(step_id) or {}
    return step.get("mode") or step.get("source")


def _step_status_label(cycle: dict, step_id: str) -> str:
    st = (cycle.get("steps") or {}).get(step_id, {}).get("status", "PENDING")
    mapping = {
        "DONE": "Disponível",
        "DONE_WARNINGS": "Disponível (alertas)",
        "APPROVED": "Aprovado",
        "ANCHORED": "Ancorado",
        "VERIFIED": "Verificado",
        "ERROR": "Erro",
        "PENDING": "Pendente",
    }
    return mapping.get(st, st)


def build_artifact_rows(cycle: dict) -> list[dict[str, Any]]:
    """Lista plana de artefatos agrupáveis."""
    if not cycle.get("cycle_id"):
        return []

    raw = build_raw_data_view(cycle)
    rows: list[dict] = []

    if raw.get("filename") or cycle.get("raw_file"):
        rows.append(_artifact_row(
            "Arquivo bruto original",
            "raw_file",
            "operational",
            _step_status_label(cycle, "raw_data"),
            "Frontend / save-file",
            raw.get("stored_path") or raw.get("filename"),
            raw.get("sha256"),
            raw.get("uploaded_at"),
            _step_mode(cycle, "raw_data"),
        ))
        rows.append(_artifact_row(
            "Metadata do upload",
            "upload_metadata",
            "operational",
            "Disponível" if raw.get("filename") else "Pendente",
            "Frontend",
            raw.get("filename"),
            None,
            raw.get("uploaded_at"),
            _step_mode(cycle, "raw_data"),
        ))

    wrapper = cycle.get("wrapper") or {}
    if wrapper or cycle.get("normalized_data"):
        rows.append(_artifact_row(
            "Lote normalizado",
            "normalized_batch",
            "operational",
            _step_status_label(cycle, "normalization"),
            "wrappers-service",
            wrapper.get("layout_id") or "—",
            None,
            wrapper.get("executed_at"),
            _step_mode(cycle, "normalization"),
        ))

    ont = cycle.get("ontology") or {}
    if ont:
        rows.append(_artifact_row(
            "Dataset canônico",
            "canonical_dataset",
            "semantic",
            _step_status_label(cycle, "ontology"),
            "ontology-manager",
            ont.get("canonical_dataset_id") or ont.get("ontology_version"),
            ont.get("dataset_hash"),
            ont.get("populated_at"),
            _step_mode(cycle, "ontology"),
        ))

    sem = cycle.get("semantic_validation") or {}
    if sem:
        rows.append(_artifact_row(
            "Relatório de validação semântica",
            "semantic_validation",
            "semantic",
            _step_status_label(cycle, "semantic"),
            "ontology-manager",
            f"{sem.get('total_validations', 0)} regras",
            sem.get("validation_hash"),
            sem.get("validated_at"),
            _step_mode(cycle, "semantic"),
        ))

    calc = cycle.get("calculation") or {}
    if calc:
        rows.append(_artifact_row(
            "Resultado preliminar",
            "preliminary_result",
            "calculation",
            _step_status_label(cycle, "calculation"),
            "calculation-service",
            f"{calc.get('co2e_total_kg', '—')} kg CO₂e",
            calc.get("result_hash"),
            calc.get("calculated_at"),
            _step_mode(cycle, "calculation"),
            is_preliminary=True,
        ))

    approval = cycle.get("approval") or {}
    if approval.get("decision"):
        rows.append(_artifact_row(
            "Registro de aprovação",
            "approval_record",
            "final",
            approval.get("decision", "—"),
            "Frontend + traceability",
            approval.get("approver") or "—",
            approval.get("record_hash"),
            approval.get("approved_at"),
            _step_mode(cycle, "approval"),
        ))

    pub = cycle.get("publication") or {}
    if pub or is_blockchain_unlocked(cycle):
        rows.append(_artifact_row(
            "Ontologia final",
            "final_ontology",
            "final",
            _step_status_label(cycle, "publication"),
            "ontology-manager",
            pub.get("ontology_version") or "—",
            pub.get("ontology_hash"),
            pub.get("published_at"),
            _step_mode(cycle, "publication"),
        ))

    if is_blockchain_unlocked(cycle):
        summary = build_evidence_summary(cycle)
        evidence = cycle.get("evidence_package") or {}
        if evidence:
            rows.append(_artifact_row(
                "Pacote de evidências",
                "evidence_package",
                "blockchain",
                _step_status_label(cycle, "evidence"),
                "blockchain-service",
                evidence.get("evidence_package_id"),
                summary.get("merkle_root"),
                evidence.get("created_at"),
                evidence.get("mode") or _step_mode(cycle, "evidence"),
            ))

        anchoring = cycle.get("anchoring") or {}
        if anchoring:
            rows.append(_artifact_row(
                "Payload de ancoragem",
                "anchoring_payload",
                "blockchain",
                anchoring.get("status") or "—",
                "blockchain-service",
                anchoring.get("transaction_id") or anchoring.get("anchor_request_id"),
                None,
                anchoring.get("anchored_at"),
                anchoring.get("mode") or _step_mode(cycle, "blockchain"),
            ))

        integrity = cycle.get("integrity") or {}
        if integrity:
            rows.append(_artifact_row(
                "Relatório de integridade",
                "integrity_report",
                "blockchain",
                "Íntegro" if integrity.get("is_valid") else (
                    "Divergente" if integrity.get("is_valid") is False else "Pendente"
                ),
                "blockchain-service",
                integrity.get("verification_id") or "—",
                integrity.get("merkle_root_recomputed"),
                integrity.get("verified_at"),
                integrity.get("mode") or _step_mode(cycle, "verification"),
            ))

    return rows


def group_artifacts(rows: list[dict]) -> dict[str, list[dict]]:
    """Agrupa artefatos por categoria."""
    grouped: dict[str, list[dict]] = {g[0]: [] for g in _ARTIFACT_GROUPS}
    for row in rows:
        grouped.setdefault(row.get("group", "operational"), []).append(row)
    return {k: v for k, v in grouped.items() if v}
