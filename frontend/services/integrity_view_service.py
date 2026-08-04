"""View layer — verificação de integridade."""

from __future__ import annotations

from typing import Any


INTEGRITY_OK_MSG = "Todos os hashes conferem. A versão final permanece íntegra."
INTEGRITY_FAIL_MSG = (
    "Há divergências entre os artefatos atuais e o pacote ancorado. "
    "Isso indica alteração, reprocessamento não registrado ou inconsistência."
)


def integrity_message(integrity: dict) -> str:
    if integrity.get("is_valid") is True:
        return INTEGRITY_OK_MSG
    if integrity.get("is_valid") is False:
        return INTEGRITY_FAIL_MSG
    return integrity.get("message", "Verificação pendente.")


def build_comparison_rows(integrity: dict) -> list[dict]:
    comparisons = integrity.get("comparisons") or integrity.get("artifacts") or []
    rows = []
    for item in comparisons:
        if isinstance(item, dict):
            status = item.get("status", "Não verificado")
            rows.append({
                "artifact": item.get("artifact") or item.get("name", "—"),
                "anchored_hash": item.get("anchored_hash") or item.get("expected", "—"),
                "recalculated_hash": item.get("current_hash") or item.get("actual", "—"),
                "status": status,
            })
    if not rows and integrity.get("is_valid") is not None:
        rows.append({
            "artifact": "Pacote completo",
            "anchored_hash": integrity.get("merkle_root_anchored", "—"),
            "recalculated_hash": integrity.get("merkle_root_recomputed", "—"),
            "status": "Íntegro" if integrity.get("is_valid") else "Divergente",
        })
    return rows


def build_integrity_summary(cycle: dict) -> dict[str, Any]:
    integrity = cycle.get("integrity") or {}
    evidence = cycle.get("evidence_package") or {}
    return {
        "package_id": evidence.get("evidence_package_id"),
        "merkle_anchored": evidence.get("merkle_root") or integrity.get("merkle_root_anchored"),
        "merkle_recomputed": integrity.get("merkle_root_recomputed"),
        "is_valid": integrity.get("is_valid"),
        "verified_at": integrity.get("verified_at"),
        "message": integrity_message(integrity),
        "rows": build_comparison_rows(integrity),
    }
