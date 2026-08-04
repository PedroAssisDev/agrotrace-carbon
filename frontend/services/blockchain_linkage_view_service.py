"""Read model: reconstrói resultado → publicação → pacote → solicitação → tx → verificação.

Acesso apenas via adapters de proveniência (provenance.db) e ciclo JSON.
Não abre blockchain_service.db diretamente — verdades criptográficas via blockchain_adapter
quando necessário.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agrotrace.blockchain_linkage")


def build_linkage_trail(cycle: dict | None) -> dict[str, Any]:
    """Monta trilha de auditoria ponta a ponta sem JOIN SQL cross-DB."""
    cycle = cycle or {}
    calculation = cycle.get("calculation") or {}
    publication = cycle.get("publication") or {}
    evidence = cycle.get("evidence_package") or {}
    anchoring = cycle.get("anchoring") or {}
    integrity = cycle.get("integrity") or {}
    mirrors = cycle.get("provenance_mirrors") or {}

    result_id = (
        calculation.get("calculation_result_set_id")
        or calculation.get("result_id")
        or (calculation.get("explanation") or {}).get("result_id")
    )
    publication_id = publication.get("publication_id")
    package_id = evidence.get("evidence_package_id")
    pipeline_run_id = cycle.get("pipeline_run_id")

    anchors: list[dict[str, Any]] = []
    verification_events: list[dict[str, Any]] = []
    if pipeline_run_id:
        try:
            from services import provenance_adapter as prov

            anchors = prov.list_anchors_for_pipeline_run(pipeline_run_id)
            if package_id:
                anchors = [
                    a
                    for a in anchors
                    if a.get("evidence_package_external_id") == package_id
                ] or anchors
            for a in anchors:
                aid = a.get("blockchain_anchor_id")
                if aid:
                    verification_events.extend(prov.list_audit_events_for_anchor(aid))
        except Exception as exc:
            logger.warning("Falha ao ler espelhos de ancoragem: %s", exc)

    primary = anchors[-1] if anchors else None
    request = None
    transaction = None
    if primary:
        meta = primary.get("metadata") or {}
        request = {
            "blockchain_anchor_id": primary.get("blockchain_anchor_id"),
            "request_id": meta.get("request_id"),
            "status": primary.get("anchor_status"),
            "network_code": primary.get("blockchain_network") or meta.get("network_code"),
            "package_hash": primary.get("package_hash") or meta.get("package_hash"),
            "merkle_root": primary.get("merkle_root") or meta.get("merkle_root"),
            "submitted_at": primary.get("submitted_at"),
            "agent": meta.get("agent") or meta.get("service"),
            "mirror_source": "audit_blockchain_anchor",
        }
        if primary.get("transaction_hash") or primary.get("anchor_status") == "confirmed":
            transaction = {
                "transaction_hash": primary.get("transaction_hash")
                or anchoring.get("transaction_id"),
                "contract_address": meta.get("contract_address")
                or anchoring.get("contract_address"),
                "chain_id": primary.get("chain_id") or anchoring.get("chain_id"),
                "block_number": primary.get("block_number") or anchoring.get("block_number"),
                "receipt_status": meta.get("receipt_status"),
                "event_identifier": meta.get("event_identifier")
                or anchoring.get("evidence_key"),
                "confirmed_at": primary.get("confirmed_at") or meta.get("confirmed_at"),
                "verification_uri": primary.get("verification_uri")
                or anchoring.get("explorer_url"),
                "mirror_source": "audit_blockchain_anchor",
            }

    # Fallback a partir do cycle JSON se o espelho ainda não existir (ciclos legados)
    if request is None and package_id:
        request = {
            "blockchain_anchor_id": (mirrors.get("anchor_request") or {}).get(
                "blockchain_anchor_id"
            ),
            "request_id": evidence.get("anchor_request_id") or package_id,
            "status": "pending" if not anchoring else "legacy_cycle_json",
            "network_code": evidence.get("network") or anchoring.get("network"),
            "package_hash": evidence.get("package_hash"),
            "merkle_root": evidence.get("merkle_root"),
            "submitted_at": None,
            "agent": "frontend.cycle_json",
            "mirror_source": "cycle_json",
        }
    if transaction is None and anchoring.get("transaction_id"):
        transaction = {
            "transaction_hash": anchoring.get("transaction_id"),
            "contract_address": anchoring.get("contract_address"),
            "chain_id": anchoring.get("chain_id"),
            "block_number": anchoring.get("block_number"),
            "receipt_status": anchoring.get("receipt_status"),
            "event_identifier": anchoring.get("evidence_key"),
            "confirmed_at": anchoring.get("anchored_at"),
            "verification_uri": anchoring.get("explorer_url"),
            "mirror_source": "cycle_json",
        }

    verification = None
    if verification_events:
        latest = verification_events[-1]
        payload = latest.get("payload") or {}
        verification = {
            "verification_id": payload.get("verification_id"),
            "result": payload.get("result"),
            "local_values": payload.get("local_values"),
            "recovered_values": payload.get("recovered_values"),
            "verified_at": payload.get("verified_at") or latest.get("recorded_at"),
            "audit_event_id": latest.get("audit_event_id"),
            "event_type": latest.get("event_type"),
            "mirror_source": "audit_event",
        }
    elif integrity:
        verification = {
            "verification_id": integrity.get("verification_id"),
            "result": "match" if integrity.get("is_valid") else "divergence",
            "local_values": {
                "package_hash": evidence.get("package_hash"),
                "merkle_root": evidence.get("merkle_root"),
            },
            "recovered_values": {"final_status": integrity.get("final_status")},
            "verified_at": integrity.get("verified_at"),
            "audit_event_id": (mirrors.get("integrity_verification") or {}).get(
                "audit_event_id"
            ),
            "event_type": None,
            "mirror_source": "cycle_json",
        }

    steps = [
        {"key": "result", "label": "Resultado", "id": result_id, "present": bool(result_id)},
        {
            "key": "publication",
            "label": "Publicação",
            "id": publication_id,
            "present": bool(publication_id),
        },
        {
            "key": "evidence_package",
            "label": "Pacote de evidências",
            "id": package_id,
            "present": bool(package_id),
        },
        {
            "key": "anchor_request",
            "label": "Solicitação de ancoragem",
            "id": (request or {}).get("blockchain_anchor_id")
            or (request or {}).get("request_id"),
            "present": bool(request),
        },
        {
            "key": "transaction",
            "label": "Transação",
            "id": (transaction or {}).get("transaction_hash"),
            "present": bool(transaction and transaction.get("transaction_hash")),
        },
        {
            "key": "verification",
            "label": "Verificação",
            "id": (verification or {}).get("verification_id")
            or (verification or {}).get("audit_event_id"),
            "present": bool(verification),
        },
    ]

    return {
        "cycle_id": cycle.get("cycle_id"),
        "pipeline_run_id": pipeline_run_id,
        "result_id": result_id,
        "publication_id": publication_id,
        "evidence_package_id": package_id,
        "anchor_request": request,
        "transaction": transaction,
        "verification": verification,
        "anchors": anchors,
        "verification_events": verification_events,
        "steps": steps,
        "complete": all(s["present"] for s in steps),
        # Caminho único configurado do DB blockchain (nunca consultado aqui).
        "blockchain_db_path_note": "config.BLOCKCHAIN_DB_PATH via blockchain_adapter apenas",
    }


def build_linkage_rows(trail: dict[str, Any] | None) -> list[dict[str, str]]:
    """Linhas tabulares para a UI de auditoria técnica."""
    trail = trail or {}
    rows: list[dict[str, str]] = []
    for step in trail.get("steps") or []:
        rows.append(
            {
                "etapa": step.get("label") or step.get("key") or "—",
                "identificador": str(step.get("id") or "—"),
                "presente": "sim" if step.get("present") else "não",
            }
        )
    req = trail.get("anchor_request") or {}
    tx = trail.get("transaction") or {}
    ver = trail.get("verification") or {}
    if req:
        rows.append(
            {
                "etapa": "Origem solicitação",
                "identificador": str(req.get("mirror_source") or "—"),
                "presente": req.get("status") or "—",
            }
        )
    if tx:
        rows.append(
            {
                "etapa": "Rede / chain",
                "identificador": str(tx.get("chain_id") or req.get("network_code") or "—"),
                "presente": str(tx.get("block_number") or "—"),
            }
        )
    if ver:
        rows.append(
            {
                "etapa": "Resultado verificação",
                "identificador": str(ver.get("result") or "—"),
                "presente": str(ver.get("verified_at") or "—"),
            }
        )
    return rows
