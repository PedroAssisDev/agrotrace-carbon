"""View layer — blockchain e pacote de evidências (somente pós-publicação final)."""

from __future__ import annotations

from typing import Any

BLOCKCHAIN_LOCKED_MESSAGE = (
    "Blockchain ainda não liberado. "
    "A ancoragem só pode ocorrer após aprovação humana e publicação da versão final da ontologia."
)

WAITING_PUBLICATION_MESSAGE = (
    "Aguardando publicação final da ontologia aprovada antes de liberar evidências e blockchain."
)


def has_final_ontology_published(cycle: dict) -> bool:
    events = cycle.get("provenance_events") or []
    if any(e.get("event_type") == "FINAL_ONTOLOGY_PUBLISHED" for e in events):
        return True
    if cycle.get("current_status") == "FINAL_ONTOLOGY_PUBLISHED":
        return True
    pub = (cycle.get("steps") or {}).get("publication", {})
    return pub.get("status") in {"DONE", "DONE_WARNINGS"}


def is_blockchain_unlocked(cycle: dict) -> bool:
    """Gate: blockchain só após FINAL_ONTOLOGY_PUBLISHED e aprovação."""
    approval = (cycle.get("steps") or {}).get("approval", {})
    if approval.get("status") != "APPROVED":
        return False
    if (cycle.get("approval") or {}).get("decision") != "APPROVED":
        return False
    return has_final_ontology_published(cycle)


def blockchain_lock_reason(cycle: dict) -> str:
    """Retorna código de bloqueio: BLOCKCHAIN_LOCKED ou WAITING_FINAL_PUBLICATION."""
    approval = (cycle.get("steps") or {}).get("approval", {})
    if approval.get("status") != "APPROVED":
        return "BLOCKCHAIN_LOCKED"
    if (cycle.get("approval") or {}).get("decision") != "APPROVED":
        return "BLOCKCHAIN_LOCKED"
    if not cycle.get("publication") and not has_final_ontology_published(cycle):
        return "WAITING_FINAL_PUBLICATION"
    pub_hash = (cycle.get("publication") or {}).get("ontology_hash") or (
        (cycle.get("ontology") or {}).get("ontology_hash")
    )
    if not pub_hash:
        return "WAITING_FINAL_PUBLICATION"
    if not is_blockchain_unlocked(cycle):
        return "BLOCKCHAIN_LOCKED"
    return ""


def blockchain_lock_message(cycle: dict) -> str:
    reason = blockchain_lock_reason(cycle)
    if reason == "WAITING_FINAL_PUBLICATION":
        return WAITING_PUBLICATION_MESSAGE
    if reason == "BLOCKCHAIN_LOCKED":
        return BLOCKCHAIN_LOCKED_MESSAGE
    return ""


def build_evidence_summary(cycle: dict) -> dict[str, Any]:
    evidence = cycle.get("evidence_package") or {}
    anchoring = cycle.get("anchoring") or {}
    hashes = evidence.get("hashes") or cycle.get("hashes") or {}
    return {
        "unlocked": is_blockchain_unlocked(cycle),
        "lock_reason": blockchain_lock_reason(cycle),
        "evidence_package_id": evidence.get("evidence_package_id"),
        "merkle_root": evidence.get("merkle_root"),
        "anchoring_status": evidence.get("anchoring_status") or anchoring.get("status"),
        "transaction_id": anchoring.get("transaction_id"),
        "mode": evidence.get("mode") or anchoring.get("mode"),
        "hashes": hashes,
        "raw_hash": hashes.get("raw_file_hash") or hashes.get("raw_file") or hashes.get("source_artifact"),
        "normalized_hash": hashes.get("normalized_batch_hash") or hashes.get("normalized_batch"),
        "canonical_hash": hashes.get("canonical_dataset_hash") or hashes.get("canonical_dataset"),
        "semantic_hash": hashes.get("semantic_validation_hash") or hashes.get("semantic_validation"),
        "calculation_hash": hashes.get("preliminary_result_hash") or hashes.get("calculation_result"),
        "approval_hash": hashes.get("approval_record_hash") or hashes.get("approval"),
        "ontology_hash": hashes.get("final_ontology_hash") or hashes.get("final_ontology"),
    }
