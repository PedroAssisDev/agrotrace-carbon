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
    from services.domain_catalog import is_publication_event

    events = cycle.get("provenance_events") or []
    if any(is_publication_event(e.get("event_type") or "") for e in events):
        return True
    status = cycle.get("current_status")
    if status in {"FINAL_ONTOLOGY_PUBLISHED", "APPROVED_RESULT_PUBLISHED", "BLOCKCHAIN_UNLOCKED"}:
        return True
    pub = cycle.get("publication") or {}
    if pub.get("status") == "PUBLISHED" and pub.get("publication_hash"):
        return True
    step = (cycle.get("steps") or {}).get("publication", {})
    return step.get("status") in {"DONE", "DONE_WARNINGS"}


def is_blockchain_unlocked(cycle: dict) -> bool:
    """Gate: blockchain só após publicação final aprovada."""
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
    network = anchoring.get("network") or evidence.get("network") or "local_simulated"
    kind = anchoring.get("anchoring_kind")
    if not kind:
        kind = "SIMULADA" if network == "local_simulated" else "CONFIRMADA EM REDE EVM"
    explorer = anchoring.get("explorer_url")
    if (
        not explorer
        and network == "ethereum_sepolia"
        and anchoring.get("transaction_id")
        and str(anchoring.get("transaction_id")).startswith("0x")
        and len(str(anchoring.get("transaction_id"))) >= 66
    ):
        explorer = f"https://sepolia.etherscan.io/tx/{anchoring.get('transaction_id')}"
    return {
        "unlocked": is_blockchain_unlocked(cycle),
        "lock_reason": blockchain_lock_reason(cycle),
        "evidence_package_id": evidence.get("evidence_package_id"),
        "merkle_root": evidence.get("merkle_root") or anchoring.get("merkle_root"),
        "package_hash": evidence.get("package_hash") or anchoring.get("package_hash"),
        "anchoring_status": evidence.get("anchoring_status") or anchoring.get("status") or anchoring.get("anchoring_status"),
        "transaction_id": anchoring.get("transaction_id"),
        "mode": evidence.get("mode") or anchoring.get("mode"),
        "network": network,
        "chain_id": anchoring.get("chain_id"),
        "contract_address": anchoring.get("contract_address"),
        "evidence_key": anchoring.get("evidence_key"),
        "gas_used": anchoring.get("gas_used"),
        "submitter": (anchoring.get("provider_response") or {}).get("from_address")
        or (anchoring.get("provider_response") or {}).get("onchain_submitter"),
        "explorer_url": explorer,
        "anchoring_kind": kind,
        "onchain_comparison": anchoring.get("onchain_comparison"),
        "hashes": hashes,
        "raw_hash": hashes.get("raw_file_hash") or hashes.get("raw_file") or hashes.get("source_artifact"),
        "normalized_hash": hashes.get("normalized_batch_hash") or hashes.get("normalized_batch"),
        "canonical_hash": hashes.get("canonical_dataset_hash") or hashes.get("canonical_dataset"),
        "semantic_hash": hashes.get("semantic_validation_hash") or hashes.get("semantic_validation"),
        "calculation_hash": hashes.get("preliminary_result_hash") or hashes.get("calculation_result"),
        "approval_hash": hashes.get("approval_record_hash") or hashes.get("approval"),
        "ontology_hash": hashes.get("final_ontology_hash") or hashes.get("final_ontology"),
    }
