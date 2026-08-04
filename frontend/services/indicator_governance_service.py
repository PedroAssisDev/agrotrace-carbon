"""Governança, pipeline, auditabilidade e metadados analíticos."""

from __future__ import annotations

from typing import Any

from services.cycle_state import progress_pct
from services.blockchain_view_service import is_blockchain_unlocked
from utils.formatting import NA as _NA
from utils.global_filter import normalize_data_mode
from utils.temporal_model import TemporalModel


def integration_data_mode(cycles: list[dict]) -> str:
    modes: set[str] = set()
    for c in cycles:
        for key in ("calculation", "wrapper", "evidence_package", "integrity", "semantic_validation"):
            block = c.get(key) or {}
            src = block.get("source") or block.get("mode")
            if src in ("real", "mock"):
                modes.add(src)
    if not modes:
        return "mock"
    if modes == {"real"}:
        return "real"
    return "mixed"


def governance_meta(
    cycles: list[dict],
    all_in_scope: list[dict],
    global_filter: dict,
    temporal: TemporalModel | None,
    active_cycle: dict | None = None,
) -> dict[str, Any]:
    from services.cycle_status_service import resolve_managerial_status

    data_mode = normalize_data_mode(global_filter.get("data_mode"))
    official = sum(1 for c in all_in_scope if resolve_managerial_status(c).is_official)
    preliminary = len(all_in_scope) - official
    included_ids = [c.get("cycle_id") for c in cycles if c.get("cycle_id")]
    last_cycle_id = None
    if cycles:
        latest = max(cycles, key=lambda x: x.get("reporting_period") or x.get("updated_at") or "")
        last_cycle_id = latest.get("cycle_id")

    blockchain_unlocked = any(is_blockchain_unlocked(c) for c in cycles) if cycles else False
    blockchain_blocked = bool(cycles) and not blockchain_unlocked

    period_label = global_filter.get("period_display_label") or global_filter.get("period")

    return {
        "data_mode": data_mode,
        "integration_mode": integration_data_mode(cycles or all_in_scope),
        "cycle_count": len(cycles),
        "cycles_in_scope": len(all_in_scope),
        "included_cycle_ids": included_ids,
        "last_cycle_id": last_cycle_id,
        "period_label": period_label,
        "official_count": official,
        "preliminary_count": preliminary,
        "has_official_data": official > 0,
        "has_preliminary_data": preliminary > 0,
        "includes_preliminary": preliminary > 0 and data_mode != "official_only",
        "no_official_in_mode": data_mode == "official_only" and len(cycles) == 0 and len(all_in_scope) > 0,
        "aggregated_approval_status": temporal.aggregated_approval_status if temporal else None,
        "view_granularity": temporal.view_granularity if temporal else None,
        "view_granularity_user": temporal.view_granularity_user if temporal else None,
        "has_partial_data": any(
            not (c.get("calculation") or {}).get("co2e_total_kg") for c in cycles
        ) if cycles else False,
        "blockchain_unlocked": blockchain_unlocked,
        "blockchain_blocked": blockchain_blocked,
        "active_cycle_id": (active_cycle or {}).get("cycle_id"),
    }


def resolve_period_status_label(meta: dict, cycles: list[dict]) -> str:
    if not cycles:
        return "Sem dados"
    agg = meta.get("aggregated_approval_status")
    data_mode = meta.get("data_mode")
    if agg == "rejected":
        return "Rejeitado"
    if agg in ("published", "evidence_generated", "integrity_verified"):
        return "Publicado"
    if agg == "approved":
        if data_mode == "include_preliminary" and meta.get("has_preliminary_data") and not meta.get("has_official_data"):
            return "Preliminar"
        return "Aprovado"
    if agg in ("partial_pending", "partial"):
        return "Parcial"
    if agg == "pending_approval":
        return "Pendente de aprovação"
    if data_mode == "include_preliminary" and meta.get("has_preliminary_data"):
        return "Preliminar"
    if meta.get("cycle_count", 0) == 0:
        return "Sem dados"
    return "Pendente de aprovação"


def pipeline_counts(cycles: list[dict]) -> dict[str, Any]:
    total = len(cycles)
    in_progress = sum(1 for c in cycles if 0 < progress_pct(c) < 100)
    awaiting = sum(
        1 for c in cycles
        if (c.get("steps") or {}).get("calculation", {}).get("status") == "DONE"
        and (c.get("steps") or {}).get("approval", {}).get("status") in {"PENDING", "AWAITING_APPROVAL"}
    )
    approved = sum(1 for c in cycles if (c.get("approval") or {}).get("decision") == "APPROVED"
                   or (c.get("steps") or {}).get("approval", {}).get("status") == "APPROVED")
    rejected = sum(1 for c in cycles if (c.get("approval") or {}).get("decision") == "REJECTED")
    published = sum(1 for c in cycles if c.get("publication") or (c.get("steps") or {}).get("publication", {}).get("status") == "DONE")
    progress_vals = [progress_pct(c) for c in cycles]
    avg_progress = round(sum(progress_vals) / len(progress_vals), 1) if progress_vals else 0

    by_status: dict[str, int] = {}
    by_step: dict[str, int] = {}
    failures: dict[str, int] = {}
    for c in cycles:
        st = c.get("current_status") or c.get("status") or "PENDING"
        by_status[st] = by_status.get(st, 0) + 1
        step = c.get("current_step") or "raw_data"
        by_step[step] = by_step.get(step, 0) + 1
        for sid, sdata in (c.get("steps") or {}).items():
            if (sdata or {}).get("status") == "ERROR":
                failures[sid] = failures.get(sid, 0) + 1

    last_step = None
    if cycles:
        latest = max(cycles, key=lambda x: x.get("updated_at") or x.get("created_at") or "")
        last_step = latest.get("current_step")

    return {
        "total_cycles": total,
        "in_progress": in_progress,
        "awaiting_approval": awaiting,
        "approved": approved,
        "rejected": rejected,
        "published": published,
        "avg_progress_pct": avg_progress,
        "last_step": last_step or _NA,
        "avg_pipeline_time": _NA,
        "reprocess_count": _NA,
        "by_status": by_status,
        "by_step": by_step,
        "failures_by_step": failures,
        "most_failed_step": max(failures, key=failures.get) if failures else _NA,
    }


def audit_counts(cycles: list[dict], events: list[dict] | None) -> dict[str, Any]:
    events = events or []
    packages = sum(
        1 for c in cycles
        if is_blockchain_unlocked(c) and (c.get("evidence_package") or {}).get("evidence_package_id")
    )
    anchored = sum(
        1 for c in cycles
        if is_blockchain_unlocked(c)
        and (
            (c.get("steps") or {}).get("blockchain", {}).get("status") in ("ANCHORED", "DONE")
            or (c.get("evidence_package") or {}).get("anchoring_status") in ("ANCHORED", "ANCHORING_SIMULATED")
        )
    )
    verified_ok = sum(
        1 for c in cycles
        if is_blockchain_unlocked(c) and (c.get("integrity") or {}).get("is_valid") is True
    )
    divergent = sum(
        1 for c in cycles
        if is_blockchain_unlocked(c)
        and (
            (c.get("steps") or {}).get("verification", {}).get("status") == "DIVERGENT"
            or (c.get("integrity") or {}).get("is_valid") is False
        )
    )
    hash_count = sum(
        len((c.get("hashes") or (c.get("evidence_package") or {}).get("hashes") or {}))
        for c in cycles
        if is_blockchain_unlocked(c)
    )
    merkle_count = sum(
        1 for c in cycles
        if is_blockchain_unlocked(c) and (c.get("evidence_package") or {}).get("merkle_root")
    )

    last_event = events[0].get("created_at") if events else _NA
    last_anchor = _NA
    last_verify = _NA
    for c in cycles:
        if not is_blockchain_unlocked(c):
            continue
        ep = c.get("evidence_package") or {}
        if ep.get("created_at"):
            last_anchor = ep.get("created_at")
        integ = c.get("integrity") or {}
        if integ:
            last_verify = c.get("updated_at") or last_verify

    pkg_status: dict[str, int] = {}
    for c in cycles:
        if not is_blockchain_unlocked(c):
            continue
        ep = c.get("evidence_package") or {}
        if not ep.get("evidence_package_id"):
            continue
        st = ep.get("anchoring_status") or (c.get("steps") or {}).get("blockchain", {}).get("status") or "CRIADO"
        pkg_status[st] = pkg_status.get(st, 0) + 1

    overall = "íntegro" if divergent == 0 and verified_ok else ("divergente" if divergent else "pendente")
    unlocked_count = sum(1 for c in cycles if is_blockchain_unlocked(c))

    return {
        "provenance_events": len(events),
        "last_provenance_event": last_event,
        "evidence_packages": packages,
        "hashes_generated": hash_count,
        "merkle_roots": merkle_count,
        "anchored_packages": anchored,
        "blockchain_unlocked_count": unlocked_count,
        "blockchain_blocked_count": len(cycles) - unlocked_count,
        "last_anchoring": last_anchor,
        "verifications_run": verified_ok + divergent,
        "verifications_ok": verified_ok,
        "verifications_divergent": divergent,
        "last_verification": last_verify,
        "integrity_status": overall,
        "packages_by_status": pkg_status,
        "verification_split": {"íntegro": verified_ok, "divergente": divergent},
    }


def source_ranking(by_source: dict[str, float], delta_by_source: dict[str, float] | None = None) -> list[dict]:
    total = sum(by_source.values()) or 1.0
    delta_by_source = delta_by_source or {}
    rows = []
    for src, val in sorted(by_source.items(), key=lambda x: -x[1]):
        pct = round(100.0 * val / total, 1)
        delta = delta_by_source.get(src)
        status = "estável"
        if isinstance(delta, (int, float)):
            status = "crescimento" if delta > 0 else ("redução" if delta < 0 else "estável")
        rows.append({
            "Fonte": src,
            "Emissão kg CO₂e": round(val, 2),
            "Participação %": pct,
            "Variação": delta if delta is not None else _NA,
            "Status": status,
        })
    return rows
