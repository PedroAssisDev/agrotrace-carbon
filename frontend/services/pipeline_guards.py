"""Pré-condições explícitas para cada etapa do pipeline operacional."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.blockchain_view_service import has_final_ontology_published, is_blockchain_unlocked


def _step_status(cycle: dict, step_id: str) -> str:
    return (cycle.get("steps") or {}).get(step_id, {}).get("status", "PENDING")


def can_run_wrapper(cycle: dict) -> tuple[bool, str]:
    raw = cycle.get("raw_file") or {}
    stored = raw.get("stored_path")
    if not stored or not Path(stored).exists():
        return False, "Arquivo original não salvo ou caminho inválido."
    if not raw.get("sha256"):
        return False, "Hash SHA-256 do arquivo bruto ausente."
    if _step_status(cycle, "raw_data") not in {"DONE", "RUNNING"} and not cycle.get("pipeline_run_id"):
        return False, "Proveniência inicial do dado bruto não registrada."
    return True, ""


def can_run_ontology(cycle: dict) -> tuple[bool, str]:
    wrapper_status = _step_status(cycle, "wrapper")
    if wrapper_status not in {"DONE", "DONE_WARNINGS"}:
        return False, "Wrapper não concluído."
    if not cycle.get("normalized_data"):
        return False, "Lote normalizado ausente."
    wrapper = cycle.get("wrapper") or {}
    if not wrapper.get("content_hash") and not cycle.get("normalized_batch_id"):
        return False, "Hash do lote normalizado ausente."
    return True, ""


def can_run_semantic_validation(cycle: dict) -> tuple[bool, str]:
    if not cycle.get("ontology"):
        return False, "Modelo canônico não populado."
    if _step_status(cycle, "ontology") not in {"DONE", "DONE_WARNINGS"}:
        return False, "Etapa de ontologia não concluída."
    return True, ""


def can_run_calculation(cycle: dict) -> tuple[bool, str]:
    semantic_status = _step_status(cycle, "semantic")
    if semantic_status not in {"DONE", "DONE_WARNINGS"}:
        return False, "Validação semântica não concluída."
    validation = cycle.get("semantic_validation") or {}
    if not validation:
        return False, "Resultado de validação semântica ausente."
    if validation.get("critical_errors", 0) > 0:
        return False, "Validação semântica possui erro(s) crítico(s)."
    if not cycle.get("ontology"):
        return False, "Dados canônicos indisponíveis."
    return True, ""


def can_publish_final_ontology(cycle: dict) -> tuple[bool, str]:
    if _step_status(cycle, "approval") != "APPROVED":
        return False, "Aprovação humana ausente ou não aprovada."
    approval = cycle.get("approval") or {}
    if approval.get("decision") != "APPROVED":
        return False, "Decisão de aprovação não é APPROVED."
    return True, ""


def can_unlock_blockchain(cycle: dict) -> tuple[bool, str]:
    ok_pub, msg_pub = can_publish_final_ontology(cycle)
    if not ok_pub:
        if _step_status(cycle, "approval") != "APPROVED":
            return False, "BLOCKCHAIN_LOCKED"
        return False, msg_pub
    if not cycle.get("publication"):
        return False, "WAITING_FINAL_PUBLICATION"
    if not has_final_ontology_published(cycle):
        return False, "WAITING_FINAL_PUBLICATION"
    pub_hash = (cycle.get("publication") or {}).get("ontology_hash") or (
        (cycle.get("ontology") or {}).get("ontology_hash")
    )
    if not pub_hash:
        return False, "WAITING_FINAL_PUBLICATION"
    if not is_blockchain_unlocked(cycle):
        return False, "BLOCKCHAIN_LOCKED"
    return True, ""
