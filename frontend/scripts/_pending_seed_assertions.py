"""Asserções compartilhadas para seed e validação de ciclos pendentes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config
from services.blockchain_view_service import is_blockchain_unlocked
from services.cycle_status_service import (
    count_pending_approval,
    cycles_pending_approval,
    resolve_managerial_status,
)
from services.seed_period_planner import (
    all_approval_groups,
    expected_approval_count,
    expected_entry_count,
)

EXPECTED_ENTRY_COUNT = expected_entry_count()
EXPECTED_APPROVAL_COUNT = expected_approval_count()
EXPECTED_PROPERTY_IDS = frozenset({
    "FARM-MONTHLY-001",
    "FARM-ANNUAL-001",
    "FARM-DAILY-001",
})

SAMPLE_ENTRY_IDS = (
    "ANNUAL-2026-FARM-MONTHLY-001",
    "ANNUAL-2026-FARM-MONTHLY-012",
    "ANNUAL-2021-2025-FARM-ANNUAL-001",
    "ANNUAL-2021-2025-FARM-ANNUAL-005",
    "DAILY-2026-01-2026-06-FARM-DAILY-001",
    "DAILY-2026-01-2026-06-FARM-DAILY-181",
)

SAMPLE_CYCLE_IDS = (
    "ANNUAL-2026-FARM-MONTHLY-001",
    "ANNUAL-2026-FARM-MONTHLY-012",
    "ANNUAL-2021-2025-FARM-ANNUAL-001",
    "ANNUAL-2021-2025-FARM-ANNUAL-005",
    "MONTHLY-2026-01-FARM-DAILY-001",
    "MONTHLY-2026-06-FARM-DAILY-006",
)

FORBIDDEN_POST_APPROVAL_EVENTS = {
    "CALCULATION_APPROVED",
    "FINAL_ONTOLOGY_PUBLISHED",
    "EVIDENCE_PACKAGE_CREATED",
    "LOCAL_HASH_CREATED",
    "MERKLE_ROOT_CREATED",
    "ANCHOR_REQUEST_CREATED",
    "ANCHORING_SIMULATED",
    "BLOCKCHAIN_ANCHOR_CREATED",
    "VERIFICATION_EXECUTED",
    "INTEGRITY_VERIFICATION_EXECUTED",
}

MANIFEST_PATH = config.SAMPLE_DATA_DIR / "seed" / "manifest.json"


def _event_types(cycle: dict) -> list[str]:
    return [e.get("event_type") for e in (cycle.get("provenance_events") or []) if e.get("event_type")]


def _is_seed_cycle(cycle: dict) -> bool:
    pid = cycle.get("property_id")
    return pid in EXPECTED_PROPERTY_IDS


def validate_pending_cycle(cycle: dict, errors: list[str], *, label: str = "") -> None:
    prefix = f"{label}: " if label else ""
    cid = cycle.get("cycle_id", "?")

    st = resolve_managerial_status(cycle)
    if st.key != "pending_approval":
        errors.append(f"{prefix}{cid} status gerencial esperado pending_approval, obteve {st.key}")

    if cycle.get("steps", {}).get("approval", {}).get("status") not in {"AWAITING_APPROVAL", "PENDING"}:
        errors.append(f"{prefix}{cid} approval step não está aguardando aprovação")

    approval = cycle.get("approval") or {}
    if approval.get("decision"):
        errors.append(f"{prefix}{cid} approval.decision deveria ser null")

    publication = cycle.get("publication") or {}
    if publication.get("status") != "NotPublished":
        errors.append(f"{prefix}{cid} publication.status deveria ser NotPublished")

    if cycle.get("evidence_package"):
        errors.append(f"{prefix}{cid} não deveria ter evidence_package")

    if (cycle.get("evidence_package") or {}).get("merkle_root"):
        errors.append(f"{prefix}{cid} não deveria ter Merkle Root")

    if is_blockchain_unlocked(cycle):
        errors.append(f"{prefix}{cid} blockchain deveria estar bloqueado")

    calc = cycle.get("calculation") or {}
    if not calc or (calc.get("co2e_total_kg") or 0) <= 0:
        errors.append(f"{prefix}{cid} cálculo preliminar ausente ou inválido")

    raw_path = (cycle.get("raw_file") or {}).get("stored_path")
    if not raw_path or not Path(raw_path).exists():
        errors.append(f"{prefix}{cid} arquivo bruto não encontrado em {raw_path}")

    normalized = cycle.get("normalized_data") or []
    if not normalized:
        errors.append(f"{prefix}{cid} dados normalizados ausentes")

    data_entries = cycle.get("data_entries") or []
    if not data_entries:
        errors.append(f"{prefix}{cid} data_entries ausente")

    events = set(_event_types(cycle))
    if "CALCULATION_PRELIMINARY_RESULT_CREATED" not in events:
        errors.append(f"{prefix}{cid} evento CALCULATION_PRELIMINARY_RESULT_CREATED ausente")
    if "HUMAN_APPROVAL_REQUESTED" not in events:
        errors.append(f"{prefix}{cid} evento HUMAN_APPROVAL_REQUESTED ausente")

    forbidden = events & FORBIDDEN_POST_APPROVAL_EVENTS
    if forbidden:
        errors.append(f"{prefix}{cid} eventos pós-aprovação indevidos: {sorted(forbidden)}")


def _load_manifest(manifest: dict[str, Any] | None) -> dict[str, Any] | None:
    if manifest is not None:
        return manifest
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def validate_seed_collection(
    cycles: list[dict],
    errors: list[str],
    *,
    manifest: dict[str, Any] | None = None,
) -> None:
    seed_cycles = [c for c in cycles if _is_seed_cycle(c)]
    by_id = {c.get("cycle_id"): c for c in seed_cycles}

    if len(seed_cycles) != EXPECTED_APPROVAL_COUNT:
        errors.append(
            f"esperados {EXPECTED_APPROVAL_COUNT} ciclos seed, obteve {len(seed_cycles)}"
        )

    if len({c.get("property_id") for c in seed_cycles}) != len(EXPECTED_PROPERTY_IDS):
        errors.append("esperadas 3 propriedades distintas nos ciclos seed")

    if count_pending_approval(seed_cycles) != EXPECTED_APPROVAL_COUNT:
        errors.append(
            f"count_pending_approval esperado {EXPECTED_APPROVAL_COUNT}, "
            f"obteve {count_pending_approval(seed_cycles)}"
        )

    pending = cycles_pending_approval(seed_cycles)
    if len(pending) != EXPECTED_APPROVAL_COUNT:
        errors.append(
            f"cycles_pending_approval esperado {EXPECTED_APPROVAL_COUNT}, obteve {len(pending)}"
        )

    manifest_data = _load_manifest(manifest)
    if manifest_data is None:
        errors.append(f"manifest ausente em {MANIFEST_PATH}")
    elif manifest_data.get("entry_count") != EXPECTED_ENTRY_COUNT:
        errors.append(
            f"manifest entry_count esperado {EXPECTED_ENTRY_COUNT}, "
            f"obteve {manifest_data.get('entry_count')}"
        )

    for cid in SAMPLE_CYCLE_IDS:
        if cid not in by_id:
            errors.append(f"ciclo ausente: {cid}")

    monthly_cycles = [c for c in seed_cycles if c.get("property_id") == "FARM-MONTHLY-001"]
    annual_cycles = [c for c in seed_cycles if c.get("property_id") == "FARM-ANNUAL-001"]
    daily_cycles = [c for c in seed_cycles if c.get("property_id") == "FARM-DAILY-001"]

    if len(monthly_cycles) != 12:
        errors.append(f"esperados 12 ciclos mensais Boa Vista, obteve {len(monthly_cycles)}")
    if len(annual_cycles) != 5:
        errors.append(f"esperados 5 ciclos anuais Santa Clara, obteve {len(annual_cycles)}")
    if len(daily_cycles) != 6:
        errors.append(f"esperados 6 ciclos diários consolidados, obteve {len(daily_cycles)}")

    for cycle in daily_cycles:
        coverage = cycle.get("temporal_coverage") or {}
        if coverage.get("source_granularity") != "daily":
            errors.append(
                f"{cycle.get('cycle_id')}: source_granularity deveria ser daily "
                f"({coverage})"
            )
        if coverage.get("granularity") != "monthly":
            errors.append(
                f"{cycle.get('cycle_id')}: granularity de aprovação deveria ser monthly"
            )
        entry_count = len(cycle.get("data_entries") or [])
        if entry_count < 28 or entry_count > 31:
            errors.append(
                f"{cycle.get('cycle_id')}: esperado 28-31 entradas diárias no mês, "
                f"obteve {entry_count}"
            )

    for cycle in monthly_cycles + annual_cycles:
        if len(cycle.get("data_entries") or []) != 1:
            errors.append(
                f"{cycle.get('cycle_id')}: esperada 1 entrada de dados, "
                f"obteve {len(cycle.get('data_entries') or [])}"
            )

    for cycle in seed_cycles:
        validate_pending_cycle(cycle, errors, label=cycle.get("cycle_id", "?"))

    if manifest_data:
        manifest_ids = {e.get("entry_id") for e in manifest_data.get("entries", [])}
        for eid in SAMPLE_ENTRY_IDS:
            if eid not in manifest_ids:
                errors.append(f"entrada ausente no manifest: {eid}")


def infer_granularity(cycle: dict) -> str | None:
    explicit = cycle.get("granularity")
    if explicit:
        return explicit
    period = cycle.get("reporting_period") or ""
    if "/" in period and len(period) > 10:
        return "intraday"
    if len(period) == 9 and period[4] == "-" and period[7] == "-":
        return "annual"
    if len(period) == 4 and period.isdigit():
        return "annual"
    if len(period) == 7 and period[4] == "-":
        return "monthly"
    return None


def expected_cycle_ids() -> list[str]:
    return [group.cycle_id for group in all_approval_groups()]
