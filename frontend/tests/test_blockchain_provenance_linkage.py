"""RF006 / RNF001 / RNF002 — vínculo rastreável proveniência ↔ blockchain (DBs temporários)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

import config
from services import bootstrap
from services.blockchain_linkage_view_service import build_linkage_trail
from services.local_orchestrator import run_anchoring_step
from services import provenance_adapter as prov


@pytest.fixture
def prov_ready(agrotrace_data_root: Path):
    """Inicializa provenance.db sob data root temporário."""
    bootstrap.configure_paths()
    bootstrap.configure_env()
    assert bootstrap.init_provenance_db()
    # Garante recorder limpo apontando para o DB temporário
    prov._recorder = None
    prov._uow_factory = None
    prov._reviewer_agent_id = None
    return agrotrace_data_root


def _seed_cycle_with_run(*, published: bool = True) -> dict:
    run_code = f"RF006-{uuid4().hex[:10]}"
    started = prov.start_pipeline_run("FARM-RF006", "2026-01", run_code)
    assert started.get("source") == "real", started
    pipeline_run_id = started["pipeline_run_id"]
    package_id = str(uuid4())
    cycle = {
        "cycle_id": f"CYCLE-{run_code}",
        "pipeline_run_id": pipeline_run_id,
        "property_id": "FARM-RF006",
        "reporting_period": "2026-01",
        "calculation": {
            "calculation_result_set_id": str(uuid4()),
            "result_id": str(uuid4()),
        },
        "publication": (
            {
                "publication_id": f"PUB-{run_code}",
                "status": "PUBLISHED",
                "ontology_hash": "a" * 64,
            }
            if published
            else None
        ),
        "evidence_package": {
            "evidence_package_id": package_id,
            "package_hash": "b" * 64,
            "merkle_root": "c" * 64,
            "anchor_request_id": f"req-{package_id[:8]}",
            "network": "local_simulated",
        },
        "approval": {"status": "APPROVED"} if published else {"status": "PENDING"},
        "milestones": ["FINAL_ONTOLOGY_PUBLISHED"] if published else [],
        "steps": {},
        "errors": [],
    }
    return cycle


def test_no_anchor_before_publication(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run(published=False)
    cycle["evidence_package"] = {
        "evidence_package_id": str(uuid4()),
        "package_hash": "d" * 64,
        "merkle_root": "e" * 64,
    }
    out = run_anchoring_step(cycle)
    assert out["steps"]["blockchain"]["status"] == "ERROR"
    anchors = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])
    assert anchors == []


def test_anchor_request_event(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    result = prov.record_anchor_request(cycle, cycle["evidence_package"])
    assert result.get("source") == "real", result
    assert result.get("anchor_status") == "pending"
    anchors = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])
    assert len(anchors) == 1
    assert anchors[0]["evidence_package_external_id"] == cycle["evidence_package"]["evidence_package_id"]
    assert anchors[0]["package_hash"] == "b" * 64
    assert anchors[0]["merkle_root"] == "c" * 64
    assert anchors[0]["metadata"].get("cycle_id") == cycle["cycle_id"]


def test_simulated_confirmation(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    assert prov.record_anchor_request(cycle)["source"] == "real"
    anchor_result = {
        "transaction_id": "0xsim" + "11" * 30,
        "network": "local_simulated",
        "anchoring_kind": "SIMULADA",
        "block_number": "1",
        "package_hash": "b" * 64,
        "merkle_root": "c" * 64,
    }
    conf = prov.record_anchor_confirmation(cycle, anchor_result)
    assert conf.get("source") == "real", conf
    assert conf.get("anchor_status") == "confirmed"
    assert conf.get("transaction_hash") == anchor_result["transaction_id"]
    anchors = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])
    assert anchors[0]["anchor_status"] == "confirmed"


def test_evm_confirmation_fixture(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    assert prov.record_anchor_request(
        cycle,
        request_meta={"network_code": "ethereum_sepolia"},
    )["source"] == "real"
    evm = {
        "transaction_id": "0x" + "ab" * 32,
        "network": "ethereum_sepolia",
        "anchoring_kind": "CONFIRMADA EM REDE EVM",
        "chain_id": "11155111",
        "block_number": "9876543",
        "contract_address": "0x" + "cd" * 20,
        "receipt_status": "1",
        "event_identifier": "EvidenceAnchored(bytes32)",
        "explorer_url": "https://sepolia.etherscan.io/tx/0x" + "ab" * 32,
        "package_hash": "b" * 64,
        "merkle_root": "c" * 64,
        "evidence_key": "0xkey",
    }
    conf = prov.record_anchor_confirmation(cycle, evm)
    assert conf.get("source") == "real", conf
    anchors = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])
    a = anchors[0]
    assert a["chain_id"] == "11155111"
    assert a["block_number"] == "9876543"
    assert a["transaction_hash"] == evm["transaction_id"]
    assert a["metadata"].get("contract_address") == evm["contract_address"]
    assert a["metadata"].get("receipt_status") == "1"
    assert a["metadata"].get("event_identifier") == evm["event_identifier"]


def test_verification_match(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    assert prov.record_anchor_request(cycle)["source"] == "real"
    assert prov.record_anchor_confirmation(
        cycle, {"transaction_id": "0xsimaa", "network": "local_simulated"}
    )["source"] == "real"
    cycle["integrity"] = {
        "is_valid": True,
        "final_status": "VERIFICADO / ÍNTEGRO",
        "verification_id": "ver-match-1",
    }
    ver = prov.record_integrity_verification(cycle, cycle["integrity"])
    assert ver.get("source") == "real", ver
    assert ver.get("result") == "match"
    anchors = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])
    events = prov.list_audit_events_for_anchor(anchors[0]["blockchain_anchor_id"])
    assert any(e["event_type"] == "integrity_verification.match" for e in events)


def test_verification_divergence(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    assert prov.record_anchor_request(cycle)["source"] == "real"
    assert prov.record_anchor_confirmation(
        cycle, {"transaction_id": "0xsimbb", "network": "local_simulated"}
    )["source"] == "real"
    cycle["integrity"] = {
        "is_valid": False,
        "final_status": "FALHA",
        "verification_id": "ver-div-1",
        "rows": [
            {
                "artifact": "Merkle Root",
                "anchored_hash": "c" * 64,
                "recalculated_hash": "f" * 64,
                "status": "divergente",
            }
        ],
    }
    ver = prov.record_integrity_verification(cycle, cycle["integrity"])
    assert ver.get("result") == "divergence"
    events = prov.list_audit_events_for_anchor(
        prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])[0]["blockchain_anchor_id"]
    )
    assert any(e["event_type"] == "integrity_verification.divergence" for e in events)


def test_idempotent_repeat(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    r1 = prov.record_anchor_request(cycle)
    r2 = prov.record_anchor_request(cycle)
    assert r1["blockchain_anchor_id"] == r2["blockchain_anchor_id"]
    assert len(prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])) == 1

    tx = "0x" + "ee" * 32
    c1 = prov.record_anchor_confirmation(cycle, {"transaction_id": tx, "network": "local_simulated"})
    c2 = prov.record_anchor_confirmation(cycle, {"transaction_id": tx, "network": "local_simulated"})
    assert c1["blockchain_anchor_id"] == c2["blockchain_anchor_id"]
    assert len(prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])) == 1

    cycle["integrity"] = {"is_valid": True, "verification_id": "idem-ver"}
    v1 = prov.record_integrity_verification(cycle)
    v2 = prov.record_integrity_verification(cycle)
    assert v1["audit_event_id"] == v2["audit_event_id"]


def test_end_to_end_reconstruction(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    assert prov.record_anchor_request(cycle)["source"] == "real"
    cycle["anchoring"] = {
        "transaction_id": "0x" + "ff" * 32,
        "network": "local_simulated",
        "block_number": "42",
        "anchoring_kind": "SIMULADA",
    }
    assert prov.record_anchor_confirmation(cycle, cycle["anchoring"])["source"] == "real"
    cycle["integrity"] = {"is_valid": True, "verification_id": "e2e-ver", "final_status": "OK"}
    assert prov.record_integrity_verification(cycle)["source"] == "real"

    trail = build_linkage_trail(cycle)
    assert trail["result_id"]
    assert trail["publication_id"]
    assert trail["evidence_package_id"]
    assert trail["anchor_request"]
    assert trail["transaction"]["transaction_hash"]
    assert trail["verification"]["result"] == "match"
    assert trail["complete"] is True
    assert trail["anchor_request"]["mirror_source"] == "audit_blockchain_anchor"


def test_provenance_unavailable_does_not_crash(prov_ready: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cycle = _seed_cycle_with_run()
    monkeypatch.setattr(prov, "_available", lambda: False)
    req = prov.record_anchor_request(cycle)
    conf = prov.record_anchor_confirmation(cycle, {"transaction_id": "0x1"})
    ver = prov.record_integrity_verification(cycle, {"is_valid": True})
    assert req["source"] == "unavailable"
    assert conf["source"] == "unavailable"
    assert ver["source"] == "unavailable"
    # Caminho blockchain do orchestrator ainda pode falhar no gate, mas adapter não levanta
    assert "error" not in req or req.get("status") == "skipped"


def test_no_secrets_in_records(prov_ready: Path) -> None:
    cycle = _seed_cycle_with_run()
    # Tentativa de injetar segredos via request_meta — whitelist deve filtrar
    result = prov.record_anchor_request(
        cycle,
        request_meta={
            "private_key": "0xDEAD",
            "rpc_url": "https://secret.rpc/v1",
            "api_token": "tok",
            "network_code": "local_simulated",
            "request_id": "safe-req",
        },
    )
    assert result.get("source") == "real", result
    anchor = prov.list_anchors_for_pipeline_run(cycle["pipeline_run_id"])[0]
    blob = json.dumps(anchor, default=str).lower()
    assert "private_key" not in (anchor.get("metadata") or {})
    assert "rpc_url" not in (anchor.get("metadata") or {})
    assert "api_token" not in (anchor.get("metadata") or {})
    assert "0xdead" not in blob
    assert "secret.rpc" not in blob
    assert config.BLOCKCHAIN_DB_PATH.parent == config.PROV_DB_PATH.parent
    assert config.BLOCKCHAIN_DB_PATH.name == "blockchain_service.db"
