"""Dados mock realistas para demonstração acadêmica."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from utils.date_helpers import now_iso
from utils.hash_helpers import sha256_dict, sha256_text


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


MOCK_FARM = {
    "property_id": "FARM-001",
    "name": "Fazenda Santa Clara",
    "municipality": "Patos de Minas",
    "state": "MG",
    "total_area_ha": 245.0,
    "production_type": "Leite",
    "production_system": "Semi-intensivo",
    "animal_count": 180,
    "animal_categories": ["Lactating_Cows", "Dry_Cows", "Heifers", "Calves"],
    "technical_responsible": "Dr. Ana Souza",
    "status": "ACTIVE",
}


def mock_wrapper_result(raw_file_path: str, layout_name: str, period: str) -> dict[str, Any]:
    return {
        "source": "mock",
        "layout_id": layout_name,
        "layout_version": "v1",
        "processing_status": "SUCCESS",
        "rows_read": 387,
        "rows_valid": 385,
        "rows_rejected": 2,
        "columns_expected": ["Property", "Period", "Milk_Production", "Lactating_Cows"],
        "columns_found": ["Property", "Period", "Milk_Production", "Lactating_Cows"],
        "errors": [],
        "warnings": ["2 linhas com valores ausentes ignoradas"],
        "normalized_payload": [
            {
                "date": "2026-01-15",
                "property": "Fazenda Santa Clara",
                "period": period,
                "variable": "Milk_Production",
                "value": 12659.0,
                "unit": "L",
                "source": "ERP",
                "status": "VALID",
            },
            {
                "date": "2026-01-15",
                "property": "Fazenda Santa Clara",
                "period": period,
                "variable": "Lactating_Cows",
                "value": 19,
                "unit": "head",
                "source": "ERP",
                "status": "VALID",
            },
        ],
        "canonical_projection": {"entities": 12, "relationships": 8},
        "normalized_file": raw_file_path.replace("raw_originals", "normalized"),
        "content_hash": sha256_text("mock-normalized-batch"),
    }


def mock_ontology_result(normalized_batch: dict) -> dict[str, Any]:
    return {
        "source": "mock",
        "entities_created": 14,
        "entities_updated": 3,
        "relationships_created": 22,
        "properties_filled": 87,
        "ontology_version": "agromrv_lite_v2026_01",
        "mapping_version": "1.0",
        "publication_status": "CANONICAL_PUBLISHED",
        "graph_nodes": [
            {"id": "farm", "label": "Fazenda Santa Clara", "type": "Property"},
            {"id": "herd", "label": "Rebanho", "type": "Herd"},
            {"id": "milk", "label": "Produção de Leite", "type": "MilkProduction"},
            {"id": "energy", "label": "Energia", "type": "Energy"},
            {"id": "fert", "label": "Fertilizantes", "type": "Fertilizers"},
            {"id": "emissions", "label": "Fontes de Emissão", "type": "EmissionSources"},
        ],
        "graph_edges": [
            {"from": "farm", "to": "herd", "label": "hasHerd"},
            {"from": "herd", "to": "milk", "label": "produces"},
            {"from": "farm", "to": "energy", "label": "consumes"},
            {"from": "farm", "to": "fert", "label": "applies"},
            {"from": "farm", "to": "emissions", "label": "emits"},
        ],
        "ontology_hash": sha256_dict({"version": "agromrv_lite_v2026_01"}),
        "export_paths": {},
    }


def mock_semantic_validation(canonical_dataset: dict) -> dict[str, Any]:
    return {
        "source": "mock",
        "total_validations": 18,
        "critical_errors": 0,
        "warnings": 2,
        "inferences": 5,
        "affected_entities": 8,
        "rules_applied": [
            "produção de leite não pode ser negativa",
            "número de animais não pode ser zero se há produção de leite",
            "período mensal precisa estar associado a uma propriedade",
            "cálculo de fermentação entérica precisa de categoria animal",
            "resultado CO₂e precisa ter GWP informado por parâmetro",
        ],
        "issues": [
            {"rule": "fertilizante nitrogenado precisa ter teor de nitrogênio", "severity": "WARNING"},
            {"rule": "energia sem vetor identificado", "severity": "WARNING"},
        ],
        "status": "SEMANTIC_VALIDATION_PASSED_WITH_WARNINGS",
        "validation_hash": sha256_dict({"status": "passed_with_warnings"}),
    }


def mock_calculation(canonical_dataset: dict, params: dict | None = None) -> dict[str, Any]:
    gwp = (params or {}).get("gwp", {"CH4": 25.0, "N2O": 298.0, "CO2": 1.0})
    factors_used = (params or {}).get("factors_used") or {
        "enteric_ch4_kg_per_animal": {
            "Lactating_Cows": 100.0, "Dry_Cows": 50.0, "Heifers": 30.0,
            "Calves": 20.0, "Bulls": 10.0,
        },
        "manure_kg_per_kg_bw_per_day": {
            "Lactating_Cows": 0.08, "Dry_Cows": 0.07, "Heifers": 0.06,
            "Calves": 0.05, "Bulls": 0.09,
        },
        "manure_ch4_kg_per_kg_manure": {
            "Lactating_Cows": 0.001, "Dry_Cows": 0.0008, "Heifers": 0.0007,
            "Calves": 0.0006, "Bulls": 0.0012,
        },
        "energy_co2_kg_per_unit": {"Diesel": 2.68, "Electricity_Grid": 0.233},
        "fertilizer_factors": {
            "direct_n2o_emission_factor": 0.01,
            "indirect_n2o_emission_factor": 0.005,
            "fraction_n_volatilized": 0.1,
        },
        "gwp": gwp,
    }
    inputs = {
        "headcounts_by_category": {
            "Lactating_Cows": 19.0, "Dry_Cows": 5.0, "Heifers": 22.0,
            "Calves": 5.0, "Bulls": 0.0,
        },
        "body_weight_kg_by_category": {k: 450.0 for k in factors_used["enteric_ch4_kg_per_animal"]},
        "nitrogen_applied_kg": 120.0,
        "energy_consumption_by_vector": {"Diesel": 500.0, "Electricity_Grid": 1200.0},
        "milk_liters": 12659.0,
        "milk_kg_fpcm": None,
        "days_in_period": 30,
        "temporal_scope": "MONTHLY",
    }
    subcalculations = [
        {
            "id": "enteric", "label": "Fermentação entérica",
            "formula": "Σ(headcount[categoria] × ef_enteric[categoria])",
            "gas": "CH4", "result_kg": 2987.88, "unit": "kg CH4",
            "co2e_kg": 74697.0,
            "inputs": {"headcounts_by_category": inputs["headcounts_by_category"]},
            "factors": {"enteric_ch4_kg_per_animal": factors_used["enteric_ch4_kg_per_animal"]},
        },
        {
            "id": "manure", "label": "Manejo de dejetos",
            "formula": "Σ(n × peso × ef_esterco/dia × ef_CH4/esterco × dias)",
            "gas": "CH4", "result_kg": 2.43, "unit": "kg CH4",
            "co2e_kg": 60.75,
            "inputs": {
                "headcounts_by_category": inputs["headcounts_by_category"],
                "body_weight_kg_by_category": inputs["body_weight_kg_by_category"],
                "days_in_period": 30,
            },
            "factors": {
                "manure_kg_per_kg_bw_per_day": factors_used["manure_kg_per_kg_bw_per_day"],
                "manure_ch4_kg_per_kg_manure": factors_used["manure_ch4_kg_per_kg_manure"],
            },
        },
        {
            "id": "fertilizer", "label": "Fertilizantes N",
            "formula": "N × ef_direto + N × fração_volatilizada × ef_indireto",
            "gas": "N2O", "result_kg": 18.2, "unit": "kg N2O",
            "co2e_kg": 5423.6,
            "inputs": {"nitrogen_applied_kg": 120.0},
            "factors": {"fertilizer_factors": factors_used["fertilizer_factors"]},
        },
        {
            "id": "energy", "label": "Energia",
            "formula": "Σ(consumo[vetor] × ef_CO2[vetor])",
            "gas": "CO2", "result_kg": 2450.0, "unit": "kg CO2",
            "co2e_kg": 2450.0,
            "inputs": {"energy_consumption_by_vector": inputs["energy_consumption_by_vector"]},
            "factors": {"energy_co2_kg_per_unit": factors_used["energy_co2_kg_per_unit"]},
        },
        {
            "id": "total", "label": "Total GEE",
            "formula": "CH4_total × GWP_CH4 + N2O × GWP_N2O + CO2",
            "gas": "CO2e", "result_kg": 82631.35, "unit": "kg CO2e",
            "co2e_kg": 82631.35, "inputs": {}, "factors": {"gwp": gwp},
        },
        {
            "id": "intensity_liter", "label": "Intensidade por litro",
            "formula": "CO2e_total / litros_leite",
            "gas": "CO2e", "result_kg": 6.527, "unit": "kg CO2e/L",
            "co2e_kg": None,
            "inputs": {"milk_liters": 12659.0, "co2e_total_kg": 82631.35},
            "factors": {},
        },
    ]
    method = {
        "code": "ECOFARM-T1-DAIRY",
        "version": "1.0.0",
        "implementation_version": "0.3.1",
        "methodology_label": "IPCC/IDF-compatible",
    }
    temporal = {
        "scope": "MONTHLY",
        "days_in_period": 30,
        "auto_prorate_factors": True,
    }
    results = {
        "ch4_enteric_kg": 2987.88,
        "ch4_manure_kg": 2.43,
        "n2o_fertilizer_kg": 18.2,
        "co2_energy_kg": 2450.0,
        "co2e_total_kg": 82631.35,
        "co2e_intensity_per_milk_liter": 6.527,
        "co2e_per_animal": 458.0,
        "methodology": "IPCC/IDF-compatible",
        "calculation_version": "0.3.1",
        "ontology_version": "agromrv_lite_v2026_01",
        "method": method,
        "temporal": temporal,
        "inputs": inputs,
        "factors_used": factors_used,
        "subcalculations": subcalculations,
        "gwp": gwp,
        "by_source": {
            "Fermentação entérica — CH₄": 74697.0,
            "Manejo de dejetos — CH₄": 60.75,
            "Fertilizantes — N₂O": 5423.6,
            "Energia — CO₂": 2450.0,
        },
        "by_gas": {"CH4": 74757.75, "N2O": 5423.6, "CO2": 2450.0},
    }
    results["source"] = "mock"
    hash_payload = {
        "method": method,
        "temporal": temporal,
        "inputs": inputs,
        "factors_used": factors_used,
        "subcalculations": subcalculations,
        "co2e_total_kg": 82631.35,
    }
    results["preliminary_hash"] = sha256_dict(hash_payload)
    return results


def mock_provenance_events(cycle_id: str) -> list[dict[str, Any]]:
    base = datetime(2026, 6, 10, 15, 42, tzinfo=timezone.utc)
    types = [
        "RAW_DATA_REGISTERED",
        "ORIGINAL_FILE_STORED",
        "WRAPPER_EXECUTED",
        "NORMALIZED_BATCH_CREATED",
        "SEMANTIC_MAPPING_COMPLETED",
        "CANONICAL_PUBLISHED",
        "SEMANTIC_VALIDATION_COMPLETED",
        "CALCULATION_PRELIMINARY_RESULT_CREATED",
        "CALCULATION_APPROVED",
        "FINAL_ONTOLOGY_PUBLISHED",
        "EVIDENCE_PACKAGE_CREATED",
        "LOCAL_HASH_CREATED",
        "ANCHOR_REQUEST_CREATED",
        "ANCHORING_SIMULATED",
        "ANCHORED",
        "VERIFICATION_EXECUTED",
    ]
    events = []
    for i, etype in enumerate(types):
        events.append({
            "event_id": _id("EVT"),
            "event_type": etype,
            "aggregate_id": cycle_id,
            "pipeline_execution_id": f"PIPE-2026-01-0001",
            "calculation_execution_id": f"CALC-2026-01-0001",
            "reporting_period_id": "2026-01",
            "payload_json": {"cycle_id": cycle_id, "step": i + 1},
            "status": "processed",
            "created_at": (base.replace(minute=base.minute + i)).isoformat(),
            "actor": "frontend-orchestrator",
            "source_service": "mock",
        })
    return events


def mock_evidence_package(cycle: dict) -> dict[str, Any]:
    hashes = {
        "raw_file_hash": cycle.get("raw_file", {}).get("sha256", sha256_text("raw")),
        "normalized_batch_hash": sha256_text("normalized"),
        "canonical_dataset_hash": sha256_text("canonical"),
        "semantic_validation_hash": sha256_text("semantic"),
        "preliminary_result_hash": sha256_text("preliminary"),
        "approval_record_hash": sha256_text("approval"),
        "final_ontology_hash": sha256_text("ontology"),
    }
    payload = {
        "evidence_package_id": "EP-2026-01-0001",
        "pipeline_execution_id": "PIPE-2026-01-0001",
        "property_id": cycle.get("property_id", "FARM-001"),
        "reporting_period": cycle.get("reporting_period", "2026-01"),
        "ontology_version": "final_ontology_v2026_01_001",
        "calculation_execution_id": "CALC-2026-01-0001",
        "methodology": "IPCC/IDF-compatible",
        "hashes": hashes,
        "merkle_root": "0x8cfa" + sha256_dict(hashes)[:56],
        "created_at": now_iso(),
        "source": "mock",
        "anchoring_status": "ANCHORING_SIMULATED",
        "network": "local_simulated",
        "transaction_id": "0xsim" + sha256_text("tx")[:58],
    }
    return payload


def mock_integrity_check(integrate: bool = True) -> dict[str, Any]:
    """Retorna verificação íntegra ou divergente."""
    artifacts = [
        ("Arquivo bruto", "a8f9c2d1e4b5", "a8f9c2d1e4b5" if integrate else "a8f9c2d1e4b5", "íntegro"),
        ("Lote normalizado", "c91a7f3e2d10", "c91a7f3e2d10" if integrate else "c91a7f3e2d10", "íntegro"),
        ("Modelo canônico", "d82b4a1c9f00", "d82b4a1c9f00" if integrate else "77ab2c1d8e99", "íntegro" if integrate else "divergente"),
        ("Resultado final", "9f10aa22bb33", "9f10aa22bb33" if integrate else "45bc11dd22ee", "íntegro" if integrate else "divergente"),
        ("Merkle Root", "0x8cfa1122", "0x8cfa1122" if integrate else "0x991b3344", "íntegro" if integrate else "falha"),
    ]
    rows = []
    for name, anchored, recalc, status in artifacts:
        rows.append({
            "artifact": name,
            "anchored_hash": anchored,
            "recalculated_hash": recalc,
            "status": status,
        })
    return {
        "source": "mock",
        "is_valid": integrate,
        "final_status": "VERIFICADO / ÍNTEGRO" if integrate else "FALHA DE INTEGRIDADE / POSSÍVEL ALTERAÇÃO",
        "rows": rows,
    }


def mock_full_cycle() -> dict[str, Any]:
    """Ciclo mensal completo para demonstração."""
    from services.cycle_state import PIPELINE_STEP_DEFS, new_cycle

    cycle_id = _id("CYCLE")
    period = "2026-01"
    raw = {
        "original_filename": "producao_janeiro_2026.csv",
        "stored_path": "frontend/data/raw_originals/demo.csv",
        "sha256": sha256_text("demo-raw"),
        "property_id": MOCK_FARM["property_id"],
        "reporting_period": period,
    }
    wrapper = mock_wrapper_result(raw["stored_path"], "monthly:v1", period)
    ontology = mock_ontology_result(wrapper)
    validation = mock_semantic_validation(ontology)
    calculation = mock_calculation(ontology)
    evidence = mock_evidence_package({"property_id": MOCK_FARM["property_id"], "reporting_period": period, "raw_file": raw})
    base = new_cycle(MOCK_FARM["property_id"], MOCK_FARM["name"], period)
    base.update({
        "cycle_id": cycle_id,
        "status": "VERIFIED",
        "current_status": "VERIFIED",
        "created_at": now_iso(),
        "raw_file": raw,
        "wrapper": wrapper,
        "normalized_data": wrapper["normalized_payload"],
        "ontology": ontology,
        "semantic_validation": validation,
        "calculation": calculation,
        "approval": {
            "decision": "APPROVED",
            "approver": "Dr. Ana Souza",
            "justification": "Resultado consistente com inventário mensal.",
            "approved_at": now_iso(),
        },
        "publication": {
            "ontology_version": "final_ontology_v2026_01_001",
            "published_at": now_iso(),
            "ontology_hash": ontology["ontology_hash"],
        },
        "provenance_events": mock_provenance_events(cycle_id),
        "evidence_package": evidence,
        "integrity": {**mock_integrity_check(integrate=True), "mode": "mock"},
        "anchoring": {"mode": "mock", "transaction_id": evidence.get("transaction_id"), "anchoring_status": "ANCHORING_SIMULATED"},
        "source": "mock",
    })
    for step_def in PIPELINE_STEP_DEFS:
        base["steps"][step_def.step_id] = {
            "status": "VERIFIED" if step_def.step_id == "verification" else (
                "ANCHORED" if step_def.step_id == "blockchain" else (
                    "APPROVED" if step_def.step_id == "approval" else "DONE"
                )
            ),
            "mode": "mock",
            "summary": f"Demo — {step_def.label}",
            "started_at": now_iso(),
            "finished_at": now_iso(),
        }
    return base


def mock_pending_cycle(
    *,
    cycle_id: str = "CYCLE-PENDING-DEMO",
    property_id: str = "FARM-MONTHLY-001",
    property_name: str = "Fazenda Boa Vista Leiteira",
    reporting_period: str = "2026-05",
    granularity: str = "monthly",
) -> dict[str, Any]:
    """Ciclo mensal com cálculo preliminar aguardando aprovação humana."""
    from services.cycle_state import PIPELINE_STEP_DEFS, new_cycle

    period = reporting_period
    raw = {
        "original_filename": "producao_demo.csv",
        "stored_path": "frontend/data/raw_originals/demo-pending.csv",
        "sha256": sha256_text("demo-raw-pending"),
        "property_id": property_id,
        "reporting_period": period,
    }
    wrapper = mock_wrapper_result(raw["stored_path"], "monthly:v1", period)
    ontology = mock_ontology_result(wrapper)
    validation = mock_semantic_validation(ontology)
    calculation = mock_calculation(ontology)
    requested_at = now_iso()

    base = new_cycle(property_id, property_name, period)
    base.update({
        "cycle_id": cycle_id,
        "granularity": granularity,
        "current_status": "AWAITING_HUMAN_APPROVAL",
        "created_at": requested_at,
        "raw_file": raw,
        "wrapper": wrapper,
        "normalized_data": wrapper["normalized_payload"],
        "ontology": ontology,
        "semantic_validation": validation,
        "calculation": calculation,
        "approval": {
            "status": "PendingApproval",
            "reviewer_name": None,
            "reviewer_role": None,
            "decision": None,
            "justification": None,
            "requested_at": requested_at,
            "approved_at": None,
            "rejected_at": None,
        },
        "publication": {
            "status": "NotPublished",
            "published_at": None,
            "published_by": None,
            "version": None,
        },
        "provenance_events": mock_provenance_events(cycle_id)[:8] + [{
            "event_id": _id("EVT"),
            "event_type": "HUMAN_APPROVAL_REQUESTED",
            "aggregate_id": cycle_id,
            "payload_json": {"cycle_id": cycle_id, "status": "PendingApproval"},
            "status": "processed",
            "created_at": requested_at,
            "source_service": "mock",
        }],
        "source": "mock",
    })
    done_steps = {"raw_data", "wrapper", "normalization", "ontology", "semantic", "calculation"}
    for step_def in PIPELINE_STEP_DEFS:
        if step_def.step_id in done_steps:
            base["steps"][step_def.step_id] = {
                "status": "DONE",
                "mode": "mock",
                "summary": f"Demo — {step_def.label}",
                "started_at": requested_at,
                "finished_at": requested_at,
            }
        elif step_def.step_id == "approval":
            base["steps"][step_def.step_id] = {
                "status": "AWAITING_APPROVAL",
                "mode": "mock",
                "summary": "Aguardando revisão e aprovação humana.",
                "started_at": requested_at,
                "finished_at": None,
            }
    return base
