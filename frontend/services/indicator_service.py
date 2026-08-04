"""Camada de indicadores do Painel gerencial — cálculos centralizados."""

from __future__ import annotations

from typing import Any

from services.cycle_state import PIPELINE_STEP_DEFS, progress_pct
from services.ontology_indicator_registry import FEED_VARS
from utils.global_filter import format_period_label, normalize_global_filter, normalize_data_mode
from utils.property_filter import aggregate_by_property, aggregate_calculation_metrics, normalize_property_id
from utils.temporal_series import expand_cycles_period_series
from utils.temporal_model import TemporalModel, build_temporal_model, select_temporal_chart_series

from utils.formatting import NA as _NA

_SUM_ACROSS_CYCLES = frozenset({
    "milk_sales", "organic_fertilizer", "non_organic_fertilizer",
    "electricity_grid", "photovoltaic_energy", "total_feed_input",
    "diesel", "gasoline", "other_fuel",
})


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_payload_records(cycle: dict) -> list[dict]:
    wrapper = cycle.get("wrapper") or {}
    payload = wrapper.get("normalized_payload") or []
    return [r for r in payload if isinstance(r, dict)]


def _record_matches_period(record: dict, reporting_period: str | None) -> bool:
    if not reporting_period:
        return True
    for key in ("period_start", "period_end"):
        val = str(record.get(key) or "")
        if reporting_period in val[:7]:
            return True
    return False


def _extract_milk_from_cycle(cycle: dict) -> float | None:
    records = _extract_payload_records(cycle)
    if not records:
        normalized = cycle.get("normalized_data") or []
        records = [r for r in normalized if isinstance(r, dict)]
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if _record_matches_period(r, rp)]
    pool = matched or records
    values = []
    for r in pool:
        v = _num(r.get("milk_production"))
        if v is None and str(r.get("variable", "")).lower() in ("milk_production", "leite"):
            v = _num(r.get("value"))
        if v is not None:
            values.append(v)
    if not values:
        return None
    return sum(values) if matched else values[-1]


def _extract_animals_from_cycle(cycle: dict) -> float | None:
    for key in ("lactating_cows", "number_of_lactating_cows"):
        val = _extract_variable_from_cycle(cycle, key)
        if val is not None:
            return val
    return None


def _cycle_records(cycle: dict) -> list[dict]:
    records = _extract_payload_records(cycle)
    if records:
        return records
    normalized = cycle.get("normalized_data") or []
    return [r for r in normalized if isinstance(r, dict)]


def _extract_variable_from_cycle(
    cycle: dict,
    var_name: str,
    *,
    sum_records: bool = False,
) -> float | None:
    """Extrai variável canônica de normalized_payload (coluna direta ou variable/value)."""
    records = _cycle_records(cycle)
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if _record_matches_period(r, rp)]
    pool = matched or records
    values: list[float] = []
    for r in pool:
        v = _num(r.get(var_name))
        if v is None and str(r.get("variable", "")).lower() == var_name.lower():
            v = _num(r.get("value"))
        if v is not None:
            values.append(v)
    if not values:
        return None
    if sum_records and matched:
        return sum(values)
    return sum(values) if sum_records else values[-1]


def _extract_text_from_cycle(cycle: dict, var_name: str) -> str | None:
    records = _cycle_records(cycle)
    if not records:
        return None
    rp = cycle.get("reporting_period")
    matched = [r for r in records if _record_matches_period(r, rp)] or records
    for r in reversed(matched):
        raw = r.get(var_name)
        if raw is None and str(r.get("variable", "")).lower() == var_name.lower():
            raw = r.get("value")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def _aggregate_variable(
    cycles: list[dict],
    var_name: str,
    *,
    mode: str = "latest",
) -> float | None:
    """Agrega variável entre ciclos: sum, latest ou avg."""
    if mode == "sum" or var_name in _SUM_ACROSS_CYCLES:
        total = 0.0
        found = False
        for c in cycles:
            v = _extract_variable_from_cycle(c, var_name, sum_records=True)
            if v is not None:
                total += v
                found = True
        return total if found else None

    values: list[float] = []
    for c in sorted(cycles, key=lambda x: x.get("reporting_period") or ""):
        v = _extract_variable_from_cycle(c, var_name)
        if v is not None:
            values.append(v)

    if not values:
        return None
    if mode == "avg":
        return sum(values) / len(values)
    return values[-1]


def _round_or_na(val: float | None, digits: int = 1) -> Any:
    if val is None:
        return _NA
    return round(val, digits)


def _pct_or_na(numerator: float | None, denominator: float | None) -> Any:
    if numerator is None or denominator is None or denominator == 0:
        return _NA
    return round(100.0 * numerator / denominator, 1)


def _ratio_or_na(numerator: float | None, denominator: float | None, digits: int = 1) -> Any:
    if numerator is None or denominator is None or denominator == 0:
        return _NA
    return round(numerator / denominator, digits)


def _integration_data_mode(cycles: list[dict]) -> str:
    """Modo de integração real/mock (distinto de data_mode de governança)."""
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


def _governance_meta(
    cycles: list[dict],
    all_in_scope: list[dict],
    global_filter: dict,
    temporal: TemporalModel | None,
) -> dict[str, Any]:
    from services.cycle_status_service import resolve_managerial_status

    data_mode = normalize_data_mode(global_filter.get("data_mode"))
    official = sum(1 for c in all_in_scope if resolve_managerial_status(c).is_official)
    preliminary = len(all_in_scope) - official
    return {
        "data_mode": data_mode,
        "integration_mode": _integration_data_mode(cycles or all_in_scope),
        "cycle_count": len(cycles),
        "cycles_in_scope": len(all_in_scope),
        "official_count": official,
        "preliminary_count": preliminary,
        "has_official_data": official > 0,
        "has_preliminary_data": preliminary > 0,
        "no_official_in_mode": data_mode == "official_only" and len(cycles) == 0 and len(all_in_scope) > 0,
        "aggregated_approval_status": temporal.aggregated_approval_status if temporal else None,
        "view_granularity": temporal.view_granularity if temporal else None,
        "view_granularity_user": temporal.view_granularity_user if temporal else None,
        "has_partial_data": any(
            not (c.get("calculation") or {}).get("co2e_total_kg") for c in cycles
        ) if cycles else False,
    }


def _aggregate_emissions(cycles: list[dict]) -> dict[str, Any]:
    base = aggregate_calculation_metrics(cycles)
    by_gas: dict[str, float] = {}
    ch4_total = n2o_total = co2_total = 0.0
    per_property: dict[str, float] = {}

    for c in cycles:
        calc = c.get("calculation") or {}
        pid = normalize_property_id(c) or "—"
        co2e = _num(calc.get("co2e_total_kg")) or 0.0
        per_property[pid] = per_property.get(pid, 0.0) + co2e
        for gas, val in (calc.get("by_gas") or {}).items():
            by_gas[gas] = by_gas.get(gas, 0.0) + float(val or 0)
        ch4_total += (_num(calc.get("ch4_enteric_kg")) or 0) + (_num(calc.get("ch4_manure_kg")) or 0)
        n2o_total += _num(calc.get("n2o_fertilizer_kg")) or 0
        co2_total += _num(calc.get("co2_energy_kg")) or 0

    if not by_gas and cycles:
        by_gas = {"CH4": ch4_total, "N2O": n2o_total, "CO2": co2_total}

    return {**base, "by_gas": by_gas, "per_property": per_property,
            "ch4_total_kg": by_gas.get("CH4", ch4_total),
            "n2o_total_kg": by_gas.get("N2O", n2o_total),
            "co2_total_kg": by_gas.get("CO2", co2_total)}


def _chart_period_series(temporal: TemporalModel | None, cycles: list[dict]) -> list[dict]:
    """Série para gráficos temporais — evita bucket consolidado como eixo X."""
    if temporal is not None:
        chart = select_temporal_chart_series(temporal)
        if chart:
            return chart
        if temporal.view_granularity != "consolidated" and temporal.view_series:
            return temporal.series_as_dicts()
        return temporal.base_series_as_dicts()
    return expand_cycles_period_series(cycles)


def _period_series(cycles: list[dict], temporal: TemporalModel | None = None) -> list[dict]:
    return _chart_period_series(temporal, cycles)


def _previous_period_delta(
    series: list[dict],
    all_cycles: list[dict] | None,
    global_filter: dict,
) -> dict[str, Any]:
    if len(series) < 1:
        return {"milk_pct": _NA, "co2e_pct": _NA, "intensity_pct": _NA,
                "current": None, "previous": None}
    current = series[-1]
    prev_period = None
    if all_cycles and current.get("period"):
        gf = normalize_global_filter(global_filter)
        farm_id = gf.get("farm_id")
        same_prop = [
            c for c in all_cycles
            if (not farm_id or normalize_property_id(c) == farm_id)
            and (c.get("reporting_period") or "") < (current.get("period") or "")
        ]
        if same_prop:
            prev_c = max(same_prop, key=lambda x: x.get("reporting_period") or "")
            prev_period = next((r for r in _period_series([prev_c]) if r.get("period")), None)

    if not prev_period and len(series) >= 2:
        prev_period = series[-2]

    if not prev_period:
        return {"milk_pct": _NA, "co2e_pct": _NA, "intensity_pct": _NA,
                "current": current, "previous": None}

    def pct(cur: float | None, prev: float | None) -> Any:
        if cur is None or prev is None or prev == 0:
            return _NA
        return round(100.0 * (cur - prev) / prev, 1)

    return {
        "milk_pct": pct(current.get("milk_liters"), prev_period.get("milk_liters")),
        "co2e_pct": pct(current.get("co2e_kg"), prev_period.get("co2e_kg")),
        "intensity_pct": pct(current.get("intensity"), prev_period.get("intensity")),
        "current": current,
        "previous": prev_period,
    }


def _classify_environmental(intensities: list[float]) -> tuple[str, str]:
    valid = [i for i in intensities if i is not None and i > 0]
    if not valid:
        return _NA, _NA
    current = valid[-1]
    if len(valid) < 2:
        return "atenção", "estável"
    avg = sum(valid) / len(valid)
    if current <= avg * 0.95:
        perf, trend = "bom", "melhorando"
    elif current >= avg * 1.05:
        perf, trend = "crítico", "piorando"
    else:
        perf, trend = "atenção", "estável"
    if len(valid) >= 2:
        if valid[-1] < valid[-2]:
            trend = "melhorando"
        elif valid[-1] > valid[-2]:
            trend = "piorando"
    return perf, trend


def _pipeline_counts(cycles: list[dict]) -> dict[str, Any]:
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


def _audit_counts(cycles: list[dict], events: list[dict] | None) -> dict[str, Any]:
    events = events or []
    packages = sum(1 for c in cycles if (c.get("evidence_package") or {}).get("evidence_package_id"))
    anchored = sum(
        1 for c in cycles
        if (c.get("steps") or {}).get("blockchain", {}).get("status") in ("ANCHORED", "DONE")
        or (c.get("evidence_package") or {}).get("anchoring_status") in ("ANCHORED", "ANCHORING_SIMULATED")
    )
    verified_ok = sum(1 for c in cycles if (c.get("integrity") or {}).get("is_valid") is True)
    divergent = sum(1 for c in cycles if (c.get("steps") or {}).get("verification", {}).get("status") == "DIVERGENT"
                    or (c.get("integrity") or {}).get("is_valid") is False)
    hash_count = sum(len((c.get("hashes") or (c.get("evidence_package") or {}).get("hashes") or {})) for c in cycles)
    merkle_count = sum(1 for c in cycles if (c.get("evidence_package") or {}).get("merkle_root"))

    last_event = events[0].get("created_at") if events else _NA
    last_anchor = _NA
    last_verify = _NA
    for c in cycles:
        ep = c.get("evidence_package") or {}
        if ep.get("created_at"):
            last_anchor = ep.get("created_at")
        integ = c.get("integrity") or {}
        if integ:
            last_verify = c.get("updated_at") or last_verify

    pkg_status: dict[str, int] = {}
    for c in cycles:
        ep = c.get("evidence_package") or {}
        if not ep.get("evidence_package_id"):
            continue
        st = ep.get("anchoring_status") or (c.get("steps") or {}).get("blockchain", {}).get("status") or "CRIADO"
        pkg_status[st] = pkg_status.get(st, 0) + 1

    overall = "íntegro" if divergent == 0 and verified_ok else ("divergente" if divergent else "pendente")

    return {
        "provenance_events": len(events),
        "last_provenance_event": last_event,
        "evidence_packages": packages,
        "hashes_generated": hash_count,
        "merkle_roots": merkle_count,
        "anchored_packages": anchored,
        "last_anchoring": last_anchor,
        "verifications_run": verified_ok + divergent,
        "verifications_ok": verified_ok,
        "verifications_divergent": divergent,
        "last_verification": last_verify,
        "integrity_status": overall,
        "packages_by_status": pkg_status,
        "verification_split": {"íntegro": verified_ok, "divergente": divergent},
    }


def _data_quality_block(cycles: list[dict]) -> dict[str, Any]:
    raw_files = sum(1 for c in cycles if c.get("raw_file"))
    rows_read = rows_valid = rows_rejected = 0
    semantic_errors = semantic_warnings = inferences = 0
    incomplete_periods = 0
    errors_by_step: dict[str, int] = {}

    for c in cycles:
        w = c.get("wrapper") or {}
        rows_read += int(w.get("rows_read") or 0)
        rows_valid += int(w.get("rows_valid") or 0)
        rows_rejected += int(w.get("rows_rejected") or 0)
        sv = c.get("semantic_validation") or {}
        semantic_errors += int(sv.get("critical_errors") or 0)
        semantic_warnings += int(sv.get("warnings") or 0)
        inferences += int(sv.get("inferences") or 0)
        if w.get("rows_valid", 0) < w.get("rows_read", 0):
            incomplete_periods += 1
        for err in c.get("errors") or []:
            step = err.get("step") or "outro"
            errors_by_step[step] = errors_by_step.get(step, 0) + 1

    utilization = round(100.0 * rows_valid / rows_read, 1) if rows_read else None
    rejection_rate = round(100.0 * rows_rejected / rows_read, 1) if rows_read else None

    completeness_series = []
    for row in _period_series(cycles):
        c = next((x for x in cycles if x.get("cycle_id") == row.get("cycle_id")), {})
        w = c.get("wrapper") or {}
        rr, rv = int(w.get("rows_read") or 0), int(w.get("rows_valid") or 0)
        pct = round(100.0 * rv / rr, 1) if rr else None
        completeness_series.append({"period_label": row["period_label"], "pct": pct})

    return {
        "raw_files": raw_files,
        "normalized_records": rows_read,
        "valid_records": rows_valid,
        "alert_records": semantic_warnings,
        "error_records": semantic_errors + rows_rejected,
        "utilization_pct": utilization if utilization is not None else _NA,
        "rejection_pct": rejection_rate if rejection_rate is not None else _NA,
        "semantic_errors": semantic_errors,
        "semantic_warnings": semantic_warnings,
        "inferences": inferences,
        "missing_fields": _NA,
        "incomplete_periods": incomplete_periods,
        "errors_by_step": errors_by_step,
        "completeness_trend": completeness_series,
        "record_breakdown": {"válidos": rows_valid, "alertas": semantic_warnings, "erros": semantic_errors + rows_rejected},
    }


def _source_ranking(by_source: dict[str, float], delta_by_source: dict[str, float] | None = None) -> list[dict]:
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


def _build_management_block(
    cycles: list[dict],
    *,
    total_milk: float | None,
    total_animals: float | None,
) -> dict[str, Any]:
    pasture = _aggregate_variable(cycles, "pasture_area")
    dairy_area = _aggregate_variable(cycles, "area_used_for_dairy_activity")
    total_feed = _aggregate_variable(cycles, "total_feed_input", mode="sum")
    organic = _aggregate_variable(cycles, "organic_fertilizer", mode="sum")
    non_organic = _aggregate_variable(cycles, "non_organic_fertilizer", mode="sum")
    grid_kwh = _aggregate_variable(cycles, "electricity_grid", mode="sum")
    pv_kwh = _aggregate_variable(cycles, "photovoltaic_energy", mode="sum")
    dmi = _aggregate_variable(cycles, "dry_matter_intake")
    energy_density = _aggregate_variable(cycles, "energy_density")

    fert_total = None
    if organic is not None or non_organic is not None:
        fert_total = (organic or 0) + (non_organic or 0)
    energy_total = None
    if grid_kwh is not None or pv_kwh is not None:
        energy_total = (grid_kwh or 0) + (pv_kwh or 0)

    feed_top: list[dict] = []
    for feed in FEED_VARS:
        if feed == "total_feed_input":
            continue
        val = _aggregate_variable(cycles, feed, mode="sum")
        if val is not None and val > 0:
            feed_top.append({"label": feed.replace("_", " ").title(), "value": val})
    feed_top.sort(key=lambda x: x["value"], reverse=True)
    feed_top = feed_top[:5]

    return {
        "pasture_area_ha": _round_or_na(pasture, 2),
        "dairy_area_ha": _round_or_na(dairy_area, 2),
        "total_feed_input_kg": _round_or_na(total_feed, 1),
        "dry_matter_intake": _round_or_na(dmi, 2),
        "energy_density": _round_or_na(energy_density, 2),
        "organic_fertilizer_kg": _round_or_na(organic, 1),
        "non_organic_fertilizer_kg": _round_or_na(non_organic, 1),
        "organic_fertilizer_pct": _pct_or_na(organic, fert_total),
        "electricity_grid_kwh": _round_or_na(grid_kwh, 1),
        "photovoltaic_energy_kwh": _round_or_na(pv_kwh, 1),
        "renewable_energy_pct": _pct_or_na(pv_kwh, energy_total),
        "animals_per_hectare": _ratio_or_na(total_animals, pasture, 2),
        "feed_efficiency": _ratio_or_na(total_milk, total_feed, 4),
        "feed_top5": feed_top,
        "predominant_soil_type": _extract_text_from_cycle(cycles[-1], "predominant_soil_type") if cycles else _NA,
    }


def _build_business_block(
    cycles: list[dict],
    *,
    total_milk: float | None,
    milk_sales: float | None,
    pipeline: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    price = _aggregate_variable(cycles, "milk_gross_price")
    employees = _aggregate_variable(cycles, "employees_during_the_month")
    sales_base = milk_sales if milk_sales is not None else total_milk
    revenue = (price * sales_base) if price is not None and sales_base is not None else None

    return {
        "milk_gross_price": _round_or_na(price, 2),
        "estimated_gross_revenue": _round_or_na(revenue, 2),
        "employees_count": int(employees) if employees is not None else _NA,
        "milk_per_employee": _ratio_or_na(total_milk, employees, 1),
        "cycles_in_progress": pipeline.get("in_progress", 0),
        "awaiting_approval": pipeline.get("awaiting_approval", 0),
        "cycles_approved": pipeline.get("approved", 0),
        "data_utilization_pct": quality.get("utilization_pct", _NA),
        "semantic_warnings": quality.get("semantic_warnings", 0),
        "information_responsible": _extract_text_from_cycle(cycles[-1], "information_responsible") if cycles else _NA,
    }


def build_dashboard_indicators(
    cycles: list[dict],
    active_cycle: dict,
    global_filter: dict,
    provenance_events: list[dict] | None = None,
    all_cycles: list[dict] | None = None,
    temporal: TemporalModel | None = None,
) -> dict:
    """Calcula indicadores do Painel a partir dos ciclos filtrados (data_mode)."""
    from utils.global_filter import filter_cycles_by_data_mode, normalize_view_granularity

    all_in_scope = list(cycles)
    data_mode = normalize_data_mode(global_filter.get("data_mode"))
    view_gr = normalize_view_granularity(global_filter.get("view_granularity"))
    filtered = filter_cycles_by_data_mode(all_in_scope, data_mode)
    cycles = filtered
    temporal = temporal or (
        build_temporal_model(cycles, active_cycle, view_gr, data_mode=data_mode) if cycles else None
    )
    series = _chart_period_series(temporal, cycles)
    operational = [p.to_dict() for p in temporal.operational_daily_series] if temporal else []
    emissions = _aggregate_emissions(cycles)
    delta = _previous_period_delta(series, all_cycles, global_filter)
    pipeline = _pipeline_counts(cycles)
    audit = _audit_counts(cycles, provenance_events)
    quality = _data_quality_block(cycles)

    total_milk = sum(r["milk_liters"] for r in series if r.get("milk_liters") is not None)
    milk_values = [r["milk_liters"] for r in series if r.get("milk_liters") is not None]
    animal_vals = [_extract_animals_from_cycle(c) for c in cycles]
    animal_vals = [a for a in animal_vals if a is not None]
    total_animals = sum(animal_vals) if animal_vals else None
    days_in_period = 30 * max(len(series), 1)

    intensities = [r["intensity"] for r in series if r.get("intensity") is not None]
    env_perf, env_trend = _classify_environmental(intensities)

    by_prop_milk: dict[str, float] = {}
    grouped = aggregate_by_property(cycles)
    for pid, group in grouped.items():
        by_prop_milk[pid] = sum(_extract_milk_from_cycle(c) or 0 for c in group)

    best_period = max(series, key=lambda r: r.get("milk_liters") or 0)["period_label"] if milk_values else _NA
    worst_period = min(series, key=lambda r: r.get("milk_liters") or float("inf"))["period_label"] if milk_values else _NA

    main_source = max(emissions["by_source"], key=emissions["by_source"].get) if emissions["by_source"] else _NA
    co2e_total = emissions["co2e_total_kg"]
    avg_intensity = emissions["avg_intensity"]

    bio_pct = None
    energy_pct = None
    if emissions["by_gas"]:
        total_gas = sum(emissions["by_gas"].values()) or 1
        bio_pct = round(100 * (emissions["by_gas"].get("CH4", 0) + emissions["by_gas"].get("N2O", 0)) / total_gas, 1)
        energy_pct = round(100 * emissions["by_gas"].get("CO2", 0) / total_gas, 1)

    carbon_productivity = (total_milk / co2e_total) if co2e_total and total_milk else None

    milk_sales = _aggregate_variable(cycles, "milk_sales", mode="sum")
    milk_fat = _aggregate_variable(cycles, "milk_fat_percentage", mode="avg")
    milk_protein = _aggregate_variable(cycles, "milk_protein_percentage", mode="avg")
    pasture = _aggregate_variable(cycles, "pasture_area")
    liters_per_ha = (total_milk / pasture) if total_milk and pasture else None
    sales_rate = _pct_or_na(milk_sales, total_milk if milk_values else None)
    co2e_per_ha = (co2e_total / pasture) if co2e_total and pasture else None

    management = _build_management_block(
        cycles, total_milk=total_milk if milk_values else None, total_animals=total_animals,
    )
    business = _build_business_block(
        cycles,
        total_milk=total_milk if milk_values else None,
        milk_sales=milk_sales,
        pipeline=pipeline,
        quality=quality,
    )

    return {
        "meta": _governance_meta(cycles, all_in_scope, global_filter, temporal),
        "summary": {
            "co2e_total_kg": co2e_total,
            "co2e_total_t": round(co2e_total / 1000, 2) if co2e_total else 0,
            "intensity_kg_per_liter": avg_intensity,
            "total_milk_liters": total_milk if milk_values else _NA,
            "cycles_in_progress": pipeline["in_progress"],
            "cycles_approved": pipeline["approved"],
            "packages_anchored": audit["anchored_packages"],
            "divergences": audit["verifications_divergent"],
        },
        "productivity": {
            "total_milk_liters": total_milk if milk_values else _NA,
            "avg_daily_liters": round(total_milk / days_in_period, 1) if milk_values and total_milk else _NA,
            "avg_monthly_liters": round(total_milk / max(len(series), 1), 1) if milk_values else _NA,
            "milk_per_animal": round(total_milk / total_animals, 1) if total_animals and milk_values else _NA,
            "total_animals": int(total_animals) if total_animals else _NA,
            "liters_per_lactating_cow": round(total_milk / total_animals, 1) if total_animals and milk_values else _NA,
            "efficiency_per_cycle": round(total_milk / max(len(cycles), 1), 1) if milk_values else _NA,
            "milk_variation_pct": delta["milk_pct"],
            "best_period": best_period,
            "worst_period": worst_period,
            "milk_by_period": [{"label": r["period_label"], "value": r["milk_liters"]} for r in series if r.get("milk_liters")],
            "operational_milk_by_day": [
                {"label": r["period_label"], "value": r["milk_liters"]} for r in operational if r.get("milk_liters")
            ],
            "milk_by_property": [{"label": k, "value": v} for k, v in by_prop_milk.items()],
            "milk_fat_pct": _round_or_na(milk_fat, 2),
            "milk_protein_pct": _round_or_na(milk_protein, 2),
            "milk_sales_liters": _round_or_na(milk_sales, 1),
            "sales_rate_pct": sales_rate,
            "liters_per_hectare": _round_or_na(liters_per_ha, 1),
        },
        "emissions": {
            "co2e_total_kg": co2e_total,
            "co2e_total_t": round(co2e_total / 1000, 2) if co2e_total else 0,
            "intensity_kg_per_liter": avg_intensity,
            "co2e_per_animal": round(co2e_total / total_animals, 2) if total_animals and co2e_total else _NA,
            "by_property": emissions["per_property"],
            "ch4_total_kg": emissions["ch4_total_kg"],
            "n2o_total_kg": emissions["n2o_total_kg"],
            "co2_total_kg": emissions["co2_total_kg"],
            "by_source": emissions["by_source"],
            "by_gas": emissions["by_gas"],
            "main_source": main_source,
            "co2e_variation_pct": delta["co2e_pct"],
            "intensity_variation_pct": delta["intensity_pct"],
            "co2e_by_period": [{"label": r["period_label"], "value": r["co2e_kg"]} for r in series if r.get("co2e_kg")],
            "intensity_by_period": [{"label": r["period_label"], "value": r["intensity"]} for r in series if r.get("intensity")],
            "period_comparison": {
                "categories": ["Emissões kg CO₂e", "Produção leite", "Intensidade kg CO₂e/L"],
                "current": [
                    delta["current"].get("co2e_kg") if delta.get("current") else None,
                    delta["current"].get("milk_liters") if delta.get("current") else None,
                    delta["current"].get("intensity") if delta.get("current") else None,
                ],
                "previous": [
                    delta["previous"].get("co2e_kg") if delta.get("previous") else None,
                    delta["previous"].get("milk_liters") if delta.get("previous") else None,
                    delta["previous"].get("intensity") if delta.get("previous") else None,
                ],
            },
            "source_ranking": _source_ranking(emissions["by_source"]),
        },
        "sustainability": {
            "liters_per_kg_co2e": round(carbon_productivity, 4) if carbon_productivity else _NA,
            "kg_co2e_per_liter": avg_intensity or _NA,
            "emissions_by_source_pct": {
                k: round(100 * v / (sum(emissions["by_source"].values()) or 1), 1)
                for k, v in emissions["by_source"].items()
            },
            "biogenic_pct": bio_pct if bio_pct is not None else _NA,
            "energy_pct": energy_pct if energy_pct is not None else _NA,
            "environmental_performance": env_perf,
            "environmental_trend": env_trend,
            "carbon_productivity_series": [
                {"label": r["period_label"],
                 "value": round(r["milk_liters"] / r["co2e_kg"], 6) if r.get("milk_liters") and r.get("co2e_kg") else None}
                for r in series
            ],
            "intensity_series": [{"label": r["period_label"], "value": r["intensity"]} for r in series if r.get("intensity")],
            "efficiency_by_property": [
                {"label": pid, "value": round(v / (emissions["per_property"].get(pid) or 1), 6)}
                for pid, v in by_prop_milk.items() if emissions["per_property"].get(pid)
            ],
            "co2e_per_hectare": _round_or_na(co2e_per_ha, 2),
        },
        "management": management,
        "business": business,
        "data_quality": quality,
        "pipeline": pipeline,
        "auditability": audit,
        "series": series,
        "temporal": {
            "input_granularity": temporal.input_granularity if temporal else None,
            "calculation_base_granularity": temporal.calculation_base_granularity if temporal else None,
            "view_granularity": temporal.view_granularity if temporal else None,
            "aggregated_approval_status": temporal.aggregated_approval_status if temporal else None,
            "point_count": len(temporal.view_series) if temporal else 0,
        },
        "active_cycle_id": active_cycle.get("cycle_id"),
    }


def generate_dashboard_insights(indicators: dict) -> list[dict]:
    """Gera insights gerenciais automáticos."""
    insights: list[dict] = []
    em = indicators.get("emissions") or {}
    prod = indicators.get("productivity") or {}
    sus = indicators.get("sustainability") or {}
    mgmt = indicators.get("management") or {}
    qual = indicators.get("data_quality") or {}
    pipe = indicators.get("pipeline") or {}
    audit = indicators.get("auditability") or {}

    main = em.get("main_source")
    if main and main != _NA:
        insights.append({
            "type": "emissao",
            "severity": "info",
            "title": "Principal fonte emissora",
            "message": f"{main} é a principal fonte de emissões no período selecionado.",
        })

    iv = em.get("intensity_variation_pct")
    if isinstance(iv, (int, float)):
        sev = "warning" if iv > 0 else "success"
        dir_ = "aumentou" if iv > 0 else "diminuiu"
        insights.append({
            "type": "emissao",
            "severity": sev,
            "title": "Variação de intensidade",
            "message": f"A intensidade kg CO₂e/L {dir_} {abs(iv):.1f}% em relação ao período anterior.",
        })

    mv, ev = prod.get("milk_variation_pct"), em.get("co2e_variation_pct")
    if isinstance(mv, (int, float)) and isinstance(ev, (int, float)) and mv > 0 and ev > mv:
        insights.append({
            "type": "produtividade",
            "severity": "warning",
            "title": "Produção vs emissões",
            "message": "A produção aumentou, mas as emissões cresceram proporcionalmente mais.",
        })

    if isinstance(mv, (int, float)) and mv > 5:
        insights.append({
            "type": "produtividade",
            "severity": "success",
            "title": "Crescimento de produção",
            "message": f"A produção de leite cresceu {mv:.1f}% em relação ao período anterior.",
        })

    sales_rate = prod.get("sales_rate_pct")
    if isinstance(sales_rate, (int, float)) and sales_rate < 90:
        insights.append({
            "type": "produtividade",
            "severity": "info",
            "title": "Comercialização parcial",
            "message": f"Apenas {sales_rate:.1f}% da produção foi comercializada no período.",
        })

    renew = mgmt.get("renewable_energy_pct")
    if isinstance(renew, (int, float)) and renew >= 10:
        insights.append({
            "type": "manejo",
            "severity": "success",
            "title": "Energia renovável",
            "message": f"{renew:.1f}% do consumo elétrico provém de fonte fotovoltaica.",
        })

    feed_eff = mgmt.get("feed_efficiency")
    if isinstance(feed_eff, (int, float)) and feed_eff > 0:
        insights.append({
            "type": "manejo",
            "severity": "info",
            "title": "Eficiência alimentar",
            "message": f"Eficiência alimentar de {feed_eff:.2f} L de leite por kg de ração.",
        })

    if (qual.get("alert_records") or 0) > 0 or (qual.get("semantic_warnings") or 0) > 0:
        insights.append({
            "type": "qualidade",
            "severity": "warning",
            "title": "Alertas nos dados",
            "message": "Há registros normalizados com alerta que podem afetar a confiabilidade do cálculo.",
        })

    if (pipe.get("awaiting_approval") or 0) > 0:
        insights.append({
            "type": "pipeline",
            "severity": "warning",
            "title": "Aprovação pendente",
            "message": "Um ou mais ciclos ainda aguardam aprovação humana.",
        })

    pkgs = audit.get("evidence_packages") or 0
    anchored = audit.get("anchored_packages") or 0
    if pkgs > anchored:
        insights.append({
            "type": "auditoria",
            "severity": "info",
            "title": "Ancoragem pendente",
            "message": "Pacote(s) de evidências criado(s), mas ainda não totalmente ancorado(s).",
        })

    if (audit.get("verifications_divergent") or 0) > 0:
        insights.append({
            "type": "auditoria",
            "severity": "critical",
            "title": "Divergência de integridade",
            "message": "Foram encontradas divergências na verificação de integridade.",
        })

    perf = sus.get("environmental_performance")
    trend = sus.get("environmental_trend")
    if perf and perf != _NA:
        insights.append({
            "type": "emissao",
            "severity": "success" if perf == "bom" else ("critical" if perf == "crítico" else "warning"),
            "title": "Desempenho ambiental",
            "message": f"Classificação ambiental: {perf} (tendência: {trend}).",
        })

    return insights


def build_dashboard_tables(indicators: dict) -> dict:
    """Monta dados das 4 tabelas do painel."""
    series = indicators.get("series") or []
    em = indicators.get("emissions") or {}
    insights = generate_dashboard_insights(indicators)
    audit = indicators.get("auditability") or {}

    period_rows = []
    for r in series:
        integrity = r.get("integrity")
        if integrity is True:
            integ_label = "íntegro"
        elif integrity is False:
            integ_label = "divergente"
        else:
            integ_label = str(integrity) if integrity else "—"
        period_rows.append({
            "Período": r.get("period_label") or r.get("period"),
            "Produção de leite": r.get("milk_liters") if r.get("milk_liters") is not None else _NA,
            "Emissões kg CO₂e": r.get("co2e_kg") if r.get("co2e_kg") is not None else _NA,
            "kg CO₂e/L": r.get("intensity") if r.get("intensity") is not None else _NA,
            "Status do ciclo": r.get("status") or "—",
            "Integridade": integ_label,
        })

    alert_rows = []
    for ins in insights:
        alert_rows.append({
            "Tipo": ins.get("type", "—"),
            "Indicador": ins.get("title", "—"),
            "Mensagem": ins.get("message", "—"),
            "Severidade": ins.get("severity", "info"),
            "Período": series[-1].get("period_label") if series else "—",
        })

    audit_rows = []
    for r in series[:10]:
        audit_rows.append({
            "Evento": "Ciclo de emissão",
            "Etapa": r.get("status") or "—",
            "Status": r.get("integrity") or "—",
            "Data/hora": r.get("period") or "—",
            "Pacote": r.get("cycle_id") or "—",
        })

    return {
        "ranking_sources": em.get("source_ranking") or [],
        "period_indicators": period_rows,
        "management_alerts": alert_rows,
        "recent_audit": audit_rows,
        "integrity_status": audit.get("integrity_status"),
    }


STEP_BY_LABEL = {s.step_id: s.label.split(". ", 1)[-1][:24] for s in PIPELINE_STEP_DEFS}


def build_dashboard_chart_series(indicators: dict, cycles: list[dict]) -> dict:
    """Séries nomeadas para renderização dos gráficos."""
    prod = indicators.get("productivity") or {}
    em = indicators.get("emissions") or {}
    sus = indicators.get("sustainability") or {}
    mgmt = indicators.get("management") or {}
    biz = indicators.get("business") or {}
    qual = indicators.get("data_quality") or {}
    pipe = indicators.get("pipeline") or {}
    audit = indicators.get("auditability") or {}

    def _lv(items: list[dict]) -> tuple[list[str], list[float]]:
        labels, values = [], []
        for it in items or []:
            v = it.get("value")
            if v is not None:
                labels.append(str(it.get("label", "")))
                values.append(float(v))
        return labels, values

    milk_l, milk_v = _lv(prod.get("milk_by_period"))
    prop_l, prop_v = _lv(prod.get("milk_by_property"))
    co2e_l, co2e_v = _lv(em.get("co2e_by_period"))
    int_l, int_v = _lv(em.get("intensity_by_period"))
    cp_l, cp_v = _lv(sus.get("carbon_productivity_series"))
    eff_l, eff_v = _lv(sus.get("efficiency_by_property"))

    feed_l, feed_v = _lv(mgmt.get("feed_top5"))

    comp = em.get("period_comparison") or {}
    rb = qual.get("record_breakdown") or {}

    return {
        "productivity": {
            "milk_by_period": {"labels": milk_l, "values": milk_v},
            "operational_milk_by_day": {
                "labels": [it.get("label", "") for it in (prod.get("operational_milk_by_day") or []) if it.get("value") is not None],
                "values": [float(it["value"]) for it in (prod.get("operational_milk_by_day") or []) if it.get("value") is not None],
            },
            "milk_by_property": {"labels": prop_l, "values": prop_v},
            "show_by_property": len(prop_v) > 1,
            "quality": {
                "labels": ["Gordura %", "Proteína %"],
                "values": [
                    prod.get("milk_fat_pct") if prod.get("milk_fat_pct") != _NA else None,
                    prod.get("milk_protein_pct") if prod.get("milk_protein_pct") != _NA else None,
                ],
            },
        },
        "emissions": {
            "co2e_by_period": {"labels": co2e_l, "values": co2e_v},
            "intensity_by_period": {"labels": int_l, "values": int_v},
            "by_source": em.get("by_source") or {},
            "by_gas": em.get("by_gas") or {},
            "period_comparison": comp,
        },
        "sustainability": {
            "carbon_productivity": {"labels": cp_l, "values": cp_v},
            "intensity": {"labels": int_l, "values": int_v},
            "efficiency_by_property": {"labels": eff_l, "values": eff_v},
            "co2e_per_hectare": sus.get("co2e_per_hectare"),
        },
        "management": {
            "feed_top5": {"labels": feed_l, "values": feed_v},
            "fertilizer_split": {
                "labels": ["Orgânico", "Químico"],
                "values": [
                    mgmt.get("organic_fertilizer_kg") if mgmt.get("organic_fertilizer_kg") != _NA else None,
                    mgmt.get("non_organic_fertilizer_kg") if mgmt.get("non_organic_fertilizer_kg") != _NA else None,
                ],
            },
            "energy_split": {
                "labels": ["Rede", "Fotovoltaica"],
                "values": [
                    mgmt.get("electricity_grid_kwh") if mgmt.get("electricity_grid_kwh") != _NA else None,
                    mgmt.get("photovoltaic_energy_kwh") if mgmt.get("photovoltaic_energy_kwh") != _NA else None,
                ],
            },
        },
        "business": {
            "pipeline_summary": {
                "labels": ["Em andamento", "Aguard. aprovação", "Aprovados"],
                "values": [
                    biz.get("cycles_in_progress"),
                    biz.get("awaiting_approval"),
                    biz.get("cycles_approved"),
                ],
            },
        },
        "data_quality": {
            "record_breakdown": rb,
            "errors_by_step": qual.get("errors_by_step") or {},
            "completeness_trend": {
                "labels": [x["period_label"] for x in qual.get("completeness_trend") or [] if x.get("pct") is not None],
                "values": [x["pct"] for x in qual.get("completeness_trend") or [] if x.get("pct") is not None],
            },
        },
        "pipeline": {
            "cycles_by_status": pipe.get("by_status") or {},
            "cycles_by_step": {
                STEP_BY_LABEL.get(k, k): v for k, v in (pipe.get("by_step") or {}).items()
            },
        },
        "auditability": {
            "packages_by_status": audit.get("packages_by_status") or {},
            "verification_split": audit.get("verification_split") or {},
        },
    }


def _fmt_kpi_val(val, *, co2e: bool = False, intensity: bool = False) -> str:
    from utils.formatting import format_co2e, format_intensity, format_number

    if val is None or val == _NA:
        return _NA
    if co2e:
        return format_co2e(val)
    if intensity:
        return format_intensity(val)
    if isinstance(val, float):
        return format_number(val)
    return str(val)


def _pct_display(val) -> str:
    if val is None or val == _NA:
        return _NA
    return f"{val}%"


_KPI_SPECS: dict[str, list[tuple[str, str, str, str, bool, bool]]] = {
    "summary": [
        ("Emissões totais", "co2e_total_kg", "fas fa-cloud", "danger", True, False),
        ("Emissões (t CO₂e)", "co2e_total_t", "fas fa-smog", "danger", False, False),
        ("Intensidade kg CO₂e/L", "intensity_kg_per_liter", "fas fa-tint", "primary", False, True),
        ("Produção de leite", "total_milk_liters", "fas fa-cheese", "success", False, False),
        ("Ciclos em andamento", "cycles_in_progress", "fas fa-sync", "info", False, False),
        ("Ciclos aprovados", "cycles_approved", "fas fa-check", "success", False, False),
        ("Pacotes ancorados", "packages_anchored", "fas fa-link", "primary", False, False),
        ("Divergências", "divergences", "fas fa-exclamation-triangle", "danger", False, False),
    ],
    "productivity": [
        ("Produção total", "total_milk_liters", "fas fa-tint", "success", False, False),
        ("Média diária", "avg_daily_liters", "fas fa-calendar-day", "info", False, False),
        ("Média mensal", "avg_monthly_liters", "fas fa-calendar", "info", False, False),
        ("Produção/animal", "milk_per_animal", "fas fa-paw", "success", False, False),
        ("Animais", "total_animals", "fas fa-paw", "secondary", False, False),
        ("L/vaca lactação", "liters_per_lactating_cow", "fas fa-tint", "primary", False, False),
        ("Variação produção", "milk_variation_pct", "fas fa-chart-line", "warning", False, False),
        ("Melhor período", "best_period", "fas fa-arrow-up", "success", False, False),
        ("Pior período", "worst_period", "fas fa-arrow-down", "danger", False, False),
        ("Gordura do leite", "milk_fat_pct", "fas fa-percent", "info", False, False),
        ("Proteína do leite", "milk_protein_pct", "fas fa-percent", "info", False, False),
        ("Leite comercializado", "milk_sales_liters", "fas fa-shopping-cart", "success", False, False),
        ("Taxa comercialização", "sales_rate_pct", "fas fa-percent", "warning", False, False),
        ("Produção/ha", "liters_per_hectare", "fas fa-map", "primary", False, False),
    ],
    "management": [
        ("Área pastagem (ha)", "pasture_area_ha", "fas fa-map-marked-alt", "success", False, False),
        ("Área leiteira (ha)", "dairy_area_ha", "fas fa-map", "info", False, False),
        ("Insumo alimentar (kg)", "total_feed_input_kg", "fas fa-wheat-awn", "secondary", False, False),
        ("MS ingerida (kg/dia)", "dry_matter_intake", "fas fa-weight", "info", False, False),
        ("Densidade energética", "energy_density", "fas fa-bolt", "warning", False, False),
        ("Fert. orgânico (kg)", "organic_fertilizer_kg", "fas fa-seedling", "success", False, False),
        ("Fert. químico (kg)", "non_organic_fertilizer_kg", "fas fa-flask", "danger", False, False),
        ("Fert. orgânico (%)", "organic_fertilizer_pct", "fas fa-leaf", "success", False, False),
        ("Energia rede (kWh)", "electricity_grid_kwh", "fas fa-plug", "secondary", False, False),
        ("Energia solar (kWh)", "photovoltaic_energy_kwh", "fas fa-solar-panel", "warning", False, False),
        ("Energia renovável (%)", "renewable_energy_pct", "fas fa-sun", "success", False, False),
        ("Densidade animal (UA/ha)", "animals_per_hectare", "fas fa-paw", "primary", False, False),
        ("Efic. alimentar (L/kg)", "feed_efficiency", "fas fa-balance-scale", "info", False, False),
    ],
    "business": [
        ("Preço bruto leite", "milk_gross_price", "fas fa-dollar-sign", "success", False, False),
        ("Receita bruta est.", "estimated_gross_revenue", "fas fa-coins", "primary", False, False),
        ("Funcionários", "employees_count", "fas fa-users", "info", False, False),
        ("Produção/funcionário", "milk_per_employee", "fas fa-user-check", "success", False, False),
        ("Ciclos em andamento", "cycles_in_progress", "fas fa-sync", "info", False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False),
        ("Ciclos aprovados", "cycles_approved", "fas fa-check", "success", False, False),
        ("Aproveitamento dados", "data_utilization_pct", "fas fa-database", "secondary", False, False),
        ("Alertas semânticos", "semantic_warnings", "fas fa-bell", "warning", False, False),
    ],
    "emissions": [
        ("CO₂e total", "co2e_total_kg", "fas fa-cloud", "danger", True, False),
        ("CO₂e (toneladas)", "co2e_total_t", "fas fa-smog", "danger", False, False),
        ("Intensidade", "intensity_kg_per_liter", "fas fa-tint", "primary", False, True),
        ("CO₂e/animal", "co2e_per_animal", "fas fa-paw", "warning", True, False),
        ("CH₄ total", "ch4_total_kg", "fas fa-wind", "info", True, False),
        ("N₂O total", "n2o_total_kg", "fas fa-seedling", "warning", True, False),
        ("CO₂ energia", "co2_total_kg", "fas fa-bolt", "secondary", True, False),
        ("Principal fonte", "main_source", "fas fa-fire", "danger", False, False),
        ("Variação emissões", "co2e_variation_pct", "fas fa-percent", "warning", False, False),
    ],
    "sustainability": [
        ("L/kg CO₂e", "liters_per_kg_co2e", "fas fa-leaf", "success", False, False),
        ("kg CO₂e/L", "kg_co2e_per_liter", "fas fa-tint", "primary", False, True),
        ("Emissões biogênicas", "biogenic_pct", "fas fa-tree", "success", False, False),
        ("Emissões energéticas", "energy_pct", "fas fa-bolt", "secondary", False, False),
        ("Desempenho ambiental", "environmental_performance", "fas fa-award", "success", False, False),
        ("Tendência ambiental", "environmental_trend", "fas fa-chart-line", "info", False, False),
        ("CO₂e/ha", "co2e_per_hectare", "fas fa-cloud", "danger", True, False),
    ],
    "data_quality": [
        ("Arquivos brutos", "raw_files", "fas fa-file", "secondary", False, False),
        ("Registros normalizados", "normalized_records", "fas fa-database", "info", False, False),
        ("Registros válidos", "valid_records", "fas fa-check-circle", "success", False, False),
        ("Com alerta", "alert_records", "fas fa-exclamation", "warning", False, False),
        ("Com erro", "error_records", "fas fa-times-circle", "danger", False, False),
        ("Aproveitamento", "utilization_pct", "fas fa-percent", "success", False, False),
        ("Rejeição wrapper", "rejection_pct", "fas fa-ban", "danger", False, False),
        ("Erros semânticos", "semantic_errors", "fas fa-bug", "danger", False, False),
        ("Alertas semânticos", "semantic_warnings", "fas fa-bell", "warning", False, False),
    ],
    "pipeline": [
        ("Total de ciclos", "total_cycles", "fas fa-list", "secondary", False, False),
        ("Em andamento", "in_progress", "fas fa-sync", "info", False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False),
        ("Aprovados", "approved", "fas fa-check", "success", False, False),
        ("Rejeitados", "rejected", "fas fa-times", "danger", False, False),
        ("Publicados", "published", "fas fa-book", "primary", False, False),
        ("Progresso médio", "avg_progress_pct", "fas fa-tasks", "info", False, False),
        ("Última etapa", "last_step", "fas fa-shoe-prints", "secondary", False, False),
        ("Etapa c/ mais falhas", "most_failed_step", "fas fa-exclamation-triangle", "danger", False, False),
    ],
    "auditability": [
        ("Eventos proveniência", "provenance_events", "fas fa-history", "info", False, False),
        ("Pacotes evidência", "evidence_packages", "fas fa-box", "primary", False, False),
        ("Hashes gerados", "hashes_generated", "fas fa-fingerprint", "secondary", False, False),
        ("Merkle roots", "merkle_roots", "fas fa-project-diagram", "info", False, False),
        ("Ancorados", "anchored_packages", "fas fa-link", "success", False, False),
        ("Verificações", "verifications_run", "fas fa-shield-alt", "primary", False, False),
        ("Íntegras", "verifications_ok", "fas fa-check-double", "success", False, False),
        ("Divergentes", "verifications_divergent", "fas fa-exclamation-triangle", "danger", False, False),
        ("Integridade geral", "integrity_status", "fas fa-lock", "success", False, False),
    ],
}

_PCT_KEYS = frozenset({
    "milk_variation_pct", "co2e_variation_pct", "biogenic_pct", "energy_pct",
    "utilization_pct", "rejection_pct", "avg_progress_pct",
    "sales_rate_pct", "organic_fertilizer_pct", "renewable_energy_pct",
    "data_utilization_pct",
})
_TRUNC_KEYS = frozenset({"main_source", "last_step", "most_failed_step"})


def build_section_kpis(indicators: dict, section_key: str) -> list[dict]:
    """Constrói cards KPI para uma seção do dashboard."""
    section = indicators.get(section_key) or {}
    specs = _KPI_SPECS.get(section_key, [])
    kpis = []
    for title, key, icon, color, co2e, intensity in specs:
        val = section.get(key)
        if key in _PCT_KEYS:
            display = _pct_display(val)
        elif key in _TRUNC_KEYS and val not in (None, _NA):
            display = str(val)[:28] if key == "main_source" else str(val)[:20]
        elif isinstance(val, int):
            display = str(val)
        else:
            display = _fmt_kpi_val(val, co2e=co2e, intensity=intensity)
        kpis.append({"title": title, "value": display, "icon": icon, "color": color})
    return kpis


def build_dashboard_chart_components(charts: dict):
    """Instancia componentes Plotly a partir das séries do dashboard."""
    from components.charts import BarChart, EmissionChart, GroupedBarChart, TemporalLineChart

    prod_ch = charts.get("productivity") or {}
    em_ch = charts.get("emissions") or {}
    sus_ch = charts.get("sustainability") or {}
    mgmt_ch = charts.get("management") or {}
    biz_ch = charts.get("business") or {}
    qual_ch = charts.get("data_quality") or {}
    pipe_ch = charts.get("pipeline") or {}
    aud_ch = charts.get("auditability") or {}

    mp = prod_ch.get("milk_by_period") or {}
    prod_charts = []
    milk_line = TemporalLineChart(
        "Produção de leite por período", mp.get("labels", []), mp.get("values", []), "litros",
    )
    if milk_line:
        prod_charts.append(milk_line)
    op_day = prod_ch.get("operational_milk_by_day") or {}
    op_line = TemporalLineChart(
        "Produção diária (operacional)", op_day.get("labels", []), op_day.get("values", []), "litros",
    )
    if op_line:
        prod_charts.append(op_line)
    if prod_ch.get("show_by_property"):
        mb = prod_ch.get("milk_by_property") or {}
        prod_charts.append(BarChart("Produção por propriedade", mb.get("labels", []), mb.get("values", [])))
    qual = prod_ch.get("quality") or {}
    if any(v is not None for v in qual.get("values") or []):
        prod_charts.append(BarChart("Composição do leite (%)", qual.get("labels", []), qual.get("values", []), yaxis_title="%"))

    co2e_p = em_ch.get("co2e_by_period") or {}
    int_p = em_ch.get("intensity_by_period") or {}
    comp = em_ch.get("period_comparison") or {}
    em_charts = []
    co2e_line = TemporalLineChart(
        "Emissões totais por período", co2e_p.get("labels", []), co2e_p.get("values", []), "kg CO₂e",
    )
    if co2e_line:
        em_charts.append(co2e_line)
    int_line = TemporalLineChart(
        "Intensidade por período", int_p.get("labels", []), int_p.get("values", []), "kg CO₂e/L",
    )
    if int_line:
        em_charts.append(int_line)
    em_charts.extend([
        EmissionChart(em_ch.get("by_source"), chart_type="bar"),
        EmissionChart(em_ch.get("by_source"), chart_type="pie"),
        BarChart("Emissões por gás", list((em_ch.get("by_gas") or {}).keys()), list((em_ch.get("by_gas") or {}).values())),
    ])
    if comp.get("categories") and comp.get("current"):
        em_charts.append(GroupedBarChart(
            "Período atual vs anterior",
            comp.get("categories") or [],
            {"Atual": comp.get("current") or [], "Anterior": comp.get("previous") or []},
        ))

    cp = sus_ch.get("carbon_productivity") or {}
    eff = sus_ch.get("efficiency_by_property") or {}
    sus_charts = []
    cp_line = TemporalLineChart(
        "Litros de leite por kg CO₂e", cp.get("labels", []), cp.get("values", []),
    )
    if cp_line:
        sus_charts.append(cp_line)
    int_sus = sus_ch.get("intensity") or {}
    int_sus_line = TemporalLineChart(
        "kg CO₂e por litro", int_sus.get("labels", []), int_sus.get("values", []),
    )
    if int_sus_line:
        sus_charts.append(int_sus_line)
    if eff.get("labels") and eff.get("values"):
        sus_charts.append(BarChart("Eficiência ambiental por propriedade", eff.get("labels", []), eff.get("values", [])))

    mgmt_charts = []
    feed5 = mgmt_ch.get("feed_top5") or {}
    if feed5.get("values"):
        mgmt_charts.append(BarChart("Top 5 insumos alimentares (kg)", feed5.get("labels", []), feed5.get("values", [])))
    fert = mgmt_ch.get("fertilizer_split") or {}
    if any(v is not None for v in fert.get("values") or []):
        mgmt_charts.append(BarChart("Fertilizantes (kg)", fert.get("labels", []), [v or 0 for v in fert.get("values", [])]))
    energy = mgmt_ch.get("energy_split") or {}
    if any(v is not None for v in energy.get("values") or []):
        mgmt_charts.append(BarChart("Consumo energético (kWh)", energy.get("labels", []), [v or 0 for v in energy.get("values", [])]))

    biz_charts = []
    pipe_sum = biz_ch.get("pipeline_summary") or {}
    if any(v is not None for v in pipe_sum.get("values") or []):
        biz_charts.append(BarChart("Resumo de ciclos", pipe_sum.get("labels", []), [v or 0 for v in pipe_sum.get("values", [])]))

    rb = qual_ch.get("record_breakdown") or {}
    qual_charts = []
    if rb:
        qual_charts.append(BarChart("Registros: válidos, alertas e erros", list(rb.keys()), list(rb.values())))
    err_step = qual_ch.get("errors_by_step") or {}
    if err_step:
        qual_charts.append(BarChart("Erros por etapa", list(err_step.keys()), list(err_step.values())))
    ct = qual_ch.get("completeness_trend") or {}
    ct_line = TemporalLineChart(
        "Taxa de completude (%)", ct.get("labels", []), ct.get("values", []), yaxis_title="%",
    )
    if ct_line:
        qual_charts.append(ct_line)

    pipe_charts = [
        BarChart("Ciclos por status", list((pipe_ch.get("cycles_by_status") or {}).keys()),
                 list((pipe_ch.get("cycles_by_status") or {}).values())),
        BarChart("Ciclos por etapa", list((pipe_ch.get("cycles_by_step") or {}).keys()),
                 list((pipe_ch.get("cycles_by_step") or {}).values())),
    ]

    aud_charts = [
        BarChart("Pacotes por status", list((aud_ch.get("packages_by_status") or {}).keys()),
                 list((aud_ch.get("packages_by_status") or {}).values())),
        BarChart("Verificações", list((aud_ch.get("verification_split") or {}).keys()),
                 list((aud_ch.get("verification_split") or {}).values())),
    ]

    return {
        "productivity": prod_charts,
        "emissions": em_charts,
        "sustainability": sus_charts,
        "management": mgmt_charts,
        "business": biz_charts,
        "data_quality": qual_charts,
        "pipeline": pipe_charts,
        "auditability": aud_charts,
    }
