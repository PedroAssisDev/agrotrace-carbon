"""View layer — cálculos, aprovação e publicação final."""

from __future__ import annotations

from typing import Any

import config
from services.blockchain_view_service import is_blockchain_unlocked
from services.gwp import resolve_gwp

_FACTOR_GROUP_LABELS: dict[str, str] = {
    "enteric_ch4_kg_per_animal": "Fermentação entérica (kg CH₄/animal/período)",
    "manure_kg_per_kg_bw_per_day": "Produção de esterco (kg/kg peso/dia)",
    "manure_ch4_kg_per_kg_manure": "Emissão CH₄ por esterco (kg CH₄/kg esterco)",
    "energy_co2_kg_per_unit": "Energia (kg CO₂/unidade)",
    "fertilizer_factors": "Fertilizantes N",
    "gwp": "GWP (IPCC AR4)",
}


def build_preliminary_result(cycle: dict) -> dict[str, Any]:
    """Preferência: resumo ontológico; espelho calculation só se marcado deprecated."""
    try:
        from services.ontology_query_adapter import get_emission_summary_for_cycle

        summary = get_emission_summary_for_cycle(cycle)
        if summary.get("co2e_total_kg") is not None or summary.get("source") == "ontology":
            co2e = summary.get("co2e_total_kg")
            return {
                "co2e_total_kg": co2e,
                "co2e_total_t": (co2e or 0) / 1000 if co2e else None,
                "intensity": summary.get("intensity"),
                "milk_production": summary.get("milk_liters"),
                "ch4_kg": (summary.get("by_gas") or {}).get("CH4"),
                "n2o_kg": (summary.get("by_gas") or {}).get("N2O"),
                "co2_kg": (summary.get("by_gas") or {}).get("CO2"),
                "status": (cycle.get("steps") or {}).get("approval", {}).get("status", "AWAITING_APPROVAL"),
                "hash": (cycle.get("calculation") or {}).get("preliminary_hash"),
                "mode": "ontology",
                "domain_source": "ontology",
            }
    except Exception:
        pass
    c = cycle.get("calculation") or {}
    ch4_kg = c.get("ch4_kg")
    if ch4_kg is None:
        ch4_kg = float(c.get("ch4_enteric_kg") or 0) + float(c.get("ch4_manure_kg") or 0)
    return {
        "co2e_total_kg": c.get("co2e_total_kg"),
        "co2e_total_t": (c.get("co2e_total_kg") or 0) / 1000 if c.get("co2e_total_kg") else None,
        "intensity": c.get("co2e_intensity_per_milk_liter"),
        "milk_production": c.get("milk_production_l") or (c.get("inputs") or {}).get("milk_liters"),
        "ch4_kg": ch4_kg,
        "n2o_kg": c.get("n2o_kg", c.get("n2o_fertilizer_kg")),
        "co2_kg": c.get("co2_kg", c.get("co2_energy_kg")),
        "status": (cycle.get("steps") or {}).get("approval", {}).get("status", "AWAITING_APPROVAL"),
        "hash": c.get("preliminary_hash") or c.get("result_hash"),
        "mode": c.get("mode") or c.get("source"),
        "domain_source": "legacy_calculation_mirror",
    }


def build_calculation_parameters(cycle: dict) -> dict[str, Any]:
    from services.calculation_explanation_service import get_or_build_explanation

    c = cycle.get("calculation") or {}
    ont = cycle.get("ontology") or {}
    method = c.get("method") or {}
    temporal = c.get("temporal") or {}
    explanation = get_or_build_explanation(cycle)
    gwp_block = explanation.get("gwp") or {}
    return {
        "methodology": c.get("methodology") or method.get("methodology_label", "IPCC / GEE agropecuário"),
        "method_code": method.get("code") or (explanation.get("method") or {}).get("code") or "—",
        "method_version": method.get("version") or (explanation.get("method") or {}).get("version") or "—",
        "calculation_version": c.get("calculation_version") or method.get("implementation_version", "—"),
        "gwp": c.get("gwp") or resolve_gwp(),
        "gwp_assessment_report": gwp_block.get("assessment_report"),
        "gwp_time_horizon": gwp_block.get("time_horizon"),
        "factors_used": c.get("factors_used") or {},
        "temporal": temporal,
        "inputs": c.get("inputs") or {},
        "canonical_version": ont.get("ontology_version"),
        "explanation": explanation,
        "schema_version": explanation.get("schema_version"),
        "executed_by": explanation.get("executed_by"),
        "approved_by": explanation.get("approved_by"),
    }


def build_subcalculations(cycle: dict) -> list[dict[str, Any]]:
    """Linhas para tabela de subcálculos (fórmula, gás, resultado, CO2e)."""
    subs = (cycle.get("calculation") or {}).get("subcalculations") or []
    rows = []
    for s in subs:
        rows.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "formula": s.get("formula"),
            "gas": s.get("gas"),
            "result_kg": s.get("result_kg"),
            "unit": s.get("unit"),
            "co2e_kg": s.get("co2e_kg"),
        })
    return rows


def build_factor_tables(cycle: dict) -> list[dict[str, Any]]:
    """Blocos por grupo de fatores para tabelas/edição na UI."""
    factors = (cycle.get("calculation") or {}).get("factors_used") or {}
    blocks: list[dict[str, Any]] = []

    for group_key, label in _FACTOR_GROUP_LABELS.items():
        group_data = factors.get(group_key)
        if group_data is None:
            continue
        rows: list[dict[str, Any]] = []
        if group_key == "gwp":
            for k, v in group_data.items():
                rows.append({"group": group_key, "key": k, "label": k, "value": v})
        elif group_key == "fertilizer_factors":
            fert_labels = {
                "direct_n2o_emission_factor": "EF direto N₂O (kg N₂O/kg N)",
                "indirect_n2o_emission_factor": "EF indireto N₂O (kg N₂O/kg N volat.)",
                "fraction_n_volatilized": "Fração N volatilizada",
            }
            for k, v in group_data.items():
                rows.append({
                    "group": group_key,
                    "key": k,
                    "label": fert_labels.get(k, k),
                    "value": v,
                })
        else:
            for k, v in group_data.items():
                rows.append({"group": group_key, "key": k, "label": k, "value": v})
        blocks.append({"group": group_key, "title": label, "rows": rows})

    return blocks


def build_inputs_summary(cycle: dict) -> list[dict[str, Any]]:
    """Entradas do inventário usadas no cálculo."""
    inputs = (cycle.get("calculation") or {}).get("inputs") or {}
    rows: list[dict[str, Any]] = []

    temporal = (cycle.get("calculation") or {}).get("temporal") or {}
    if temporal:
        rows.append({"Parâmetro": "Escopo temporal", "Valor": temporal.get("scope", "—")})
        rows.append({"Parâmetro": "Dias no período", "Valor": temporal.get("days_in_period", "—")})
        rows.append({
            "Parâmetro": "Prorratação automática",
            "Valor": "Sim" if temporal.get("auto_prorate_factors") else "Não",
        })

    for cat, n in (inputs.get("headcounts_by_category") or {}).items():
        rows.append({"Parâmetro": f"Rebanho — {cat}", "Valor": n})
    for cat, w in (inputs.get("body_weight_kg_by_category") or {}).items():
        rows.append({"Parâmetro": f"Peso médio — {cat} (kg)", "Valor": w})
    if inputs.get("nitrogen_applied_kg") is not None:
        rows.append({"Parâmetro": "N aplicado (kg N)", "Valor": inputs["nitrogen_applied_kg"]})
    for vec, cons in (inputs.get("energy_consumption_by_vector") or {}).items():
        rows.append({"Parâmetro": f"Consumo — {vec}", "Valor": cons})
    if inputs.get("milk_liters") is not None:
        rows.append({"Parâmetro": "Produção leite (L)", "Valor": inputs["milk_liters"]})

    return rows


_ENTERIC_EF_KEYS = ("ef_enteric_kg_ch4", "ef_enteric_kgCH4")
_ENTERIC_TCO2E_KEYS = ("enteric_tco2e", "enteric_tCO2e")
_TIER1_ENTERIC_FORMULA = "Σ(headcount[categoria] × ef_enteric[categoria])"


def _row_float(row: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _normalize_period_key(period: str | None) -> str | None:
    if not period or not isinstance(period, str):
        return None
    period = period.strip()
    if len(period) >= 7 and period[4] == "-":
        return period[:7]
    if len(period) == 4 and period.isdigit():
        return period
    return period


def _row_period_key(row: dict) -> str | None:
    temporal = row.get("_temporal_context") or {}
    start = temporal.get("start") or row.get("period_start")
    if isinstance(start, str) and len(start) >= 7:
        return start[:7]
    return None


def _normalized_records(cycle: dict) -> list[dict]:
    data = cycle.get("normalized_data")
    if isinstance(data, list) and data:
        return data
    wrapper = cycle.get("wrapper") or {}
    payload = wrapper.get("normalized_payload")
    if isinstance(payload, list):
        return payload
    return []


def _rows_with_enteric_observed(records: list[dict]) -> list[dict]:
    return [
        row for row in records
        if _row_float(row, _ENTERIC_EF_KEYS) is not None
        or _row_float(row, _ENTERIC_TCO2E_KEYS) is not None
    ]


def _select_enteric_observed_rows(cycle: dict, records: list[dict]) -> list[dict]:
    candidates = _rows_with_enteric_observed(records)
    if not candidates:
        return []

    period_key = _normalize_period_key(cycle.get("reporting_period"))
    if period_key:
        if len(period_key) == 7:
            matched = [row for row in candidates if _row_period_key(row) == period_key]
            if matched:
                return matched
        elif len(period_key) == 4:
            matched = [
                row for row in candidates
                if (_row_period_key(row) or "").startswith(period_key)
            ]
            if matched:
                return matched

    if len(candidates) == 1:
        return candidates
    return []


def _tier1_enteric_values(cycle: dict) -> dict[str, Any]:
    calc = cycle.get("calculation") or {}
    from services.gwp import resolve_gwp
    gwp = resolve_gwp(calc.get("gwp"))
    gwp_ch4 = float(gwp.get("CH4", 25))

    ch4_kg = calc.get("ch4_enteric_kg")
    co2e_kg = None
    formula = _TIER1_ENTERIC_FORMULA

    for sub in calc.get("subcalculations") or []:
        if sub.get("id") == "enteric":
            ch4_kg = ch4_kg if ch4_kg is not None else sub.get("result_kg")
            co2e_kg = sub.get("co2e_kg")
            formula = sub.get("formula") or formula
            break

    if ch4_kg is not None and co2e_kg is None:
        co2e_kg = float(ch4_kg) * gwp_ch4

    method = calc.get("method") or {}
    return {
        "method_code": method.get("code", "ECOFARM-T1-DAIRY"),
        "formula": formula,
        "ch4_kg": ch4_kg,
        "co2e_kg": co2e_kg,
        "gwp_ch4": gwp_ch4,
    }


def _aggregate_tier2_observed(rows: list[dict]) -> dict[str, Any]:
    ef_values = [_row_float(row, _ENTERIC_EF_KEYS) for row in rows]
    tco2e_values = [_row_float(row, _ENTERIC_TCO2E_KEYS) for row in rows]
    ef_values = [v for v in ef_values if v is not None]
    tco2e_values = [v for v in tco2e_values if v is not None]

    period_labels: list[str] = []
    for row in rows:
        start = row.get("period_start") or (row.get("_temporal_context") or {}).get("start")
        end = row.get("period_end") or (row.get("_temporal_context") or {}).get("end")
        if start and end:
            period_labels.append(f"{start} → {end}")
        elif start:
            period_labels.append(str(start))

    ef = ef_values[0] if len(ef_values) == 1 else (sum(ef_values) if ef_values else None)
    tco2e_t = tco2e_values[0] if len(tco2e_values) == 1 else (sum(tco2e_values) if tco2e_values else None)

    return {
        "source": "ECOFARM (normalized_data)",
        "row_count": len(rows),
        "period_label": period_labels[0] if len(period_labels) == 1 else "; ".join(period_labels[:3]),
        "ef_enteric_kg_ch4": ef,
        "enteric_tco2e_t": tco2e_t,
        "enteric_co2e_kg": float(tco2e_t) * 1000.0 if tco2e_t is not None else None,
    }


def _format_delta_pct(tier1: float | None, tier2: float | None) -> float | None:
    if tier1 is None or tier2 is None or tier1 == 0:
        return None
    return ((tier2 - tier1) / abs(tier1)) * 100.0


def build_enteric_tier_comparison(cycle: dict) -> dict[str, Any] | None:
    """Compara fermentação entérica Tier 1 (pipeline) vs Tier 2 observado no ECOFARM."""
    records = _normalized_records(cycle)
    observed_rows = _select_enteric_observed_rows(cycle, records)
    if not observed_rows:
        return None

    tier1 = _tier1_enteric_values(cycle)
    tier2 = _aggregate_tier2_observed(observed_rows)
    has_tier1 = tier1.get("ch4_kg") is not None or tier1.get("co2e_kg") is not None

    co2e_delta_kg = None
    if tier1.get("co2e_kg") is not None and tier2.get("enteric_co2e_kg") is not None:
        co2e_delta_kg = tier2["enteric_co2e_kg"] - float(tier1["co2e_kg"])

    return {
        "has_tier1": has_tier1,
        "tier1": tier1,
        "tier2": tier2,
        "co2e_delta_kg": co2e_delta_kg,
        "co2e_delta_pct": _format_delta_pct(tier1.get("co2e_kg"), tier2.get("enteric_co2e_kg")),
        "reporting_period": cycle.get("reporting_period"),
    }


def build_source_breakdown(cycle: dict) -> list[dict]:
    c = cycle.get("calculation") or {}
    by_source = c.get("by_source") or {}
    if not by_source and c.get("co2e_total_kg"):
        by_source = {
            "Fermentação entérica": c.get("enteric_ch4_co2e", 0),
            "Manejo de dejetos": c.get("manure_ch4_co2e", 0),
            "Fertilizantes": c.get("fertilizer_n2o_co2e", 0),
            "Energia": c.get("energy_co2", 0),
        }
    return [{"fonte": k, "co2e_kg": v} for k, v in by_source.items()]


def build_approval_view(cycle: dict) -> dict[str, Any]:
    a = cycle.get("approval") or {}
    step = (cycle.get("steps") or {}).get("approval", {})
    return {
        "decision": a.get("decision") or step.get("status"),
        "approver": a.get("approver"),
        "justification": a.get("justification"),
        "approved_at": a.get("approved_at"),
        "hash": a.get("approval_hash"),
        "mode": step.get("mode"),
    }


def build_publication_view(cycle: dict) -> dict[str, Any]:
    pub = cycle.get("publication") or {}
    return {
        "ontology_version": pub.get("ontology_version"),
        "ontology_hash": pub.get("ontology_hash"),
        "published_at": pub.get("published_at"),
        "blockchain_unlocked": is_blockchain_unlocked(cycle),
        "status": (cycle.get("steps") or {}).get("publication", {}).get("status"),
    }


def rebuild_calculation_params_from_factor_inputs(
    factor_ids: list[dict | None],
    factor_values: list,
    cycle: dict,
) -> dict[str, Any]:
    """Reconstrói calculation_params a partir dos inputs editáveis na UI."""
    from services.calculation_factor_mapping_service import get_effective_factors_used

    base = dict(cycle.get("calculation_params") or {})
    calc = cycle.get("calculation") or {}
    factors_used = get_effective_factors_used(cycle)
    temporal = calc.get("temporal") or {}

    params: dict[str, Any] = {
        "gwp": dict(factors_used.get("gwp") or base.get("gwp") or resolve_gwp()),
        "enteric_ch4_kg_per_animal": dict(factors_used.get("enteric_ch4_kg_per_animal") or {}),
        "manure_kg_per_kg_bw_per_day": dict(factors_used.get("manure_kg_per_kg_bw_per_day") or {}),
        "manure_ch4_kg_per_kg_manure": dict(factors_used.get("manure_ch4_kg_per_kg_manure") or {}),
        "energy_co2_kg_per_unit": dict(factors_used.get("energy_co2_kg_per_unit") or {}),
        "fertilizer_factors": dict(factors_used.get("fertilizer_factors") or {}),
        "temporal_scope": temporal.get("scope") or base.get("temporal_scope", "MONTHLY"),
        "days_in_period": temporal.get("days_in_period") or base.get("days_in_period"),
        "auto_prorate_factors": temporal.get("auto_prorate_factors", base.get("auto_prorate_factors", True)),
        "methodology": calc.get("methodology") or base.get("methodology"),
    }

    for fid, val in zip(factor_ids, factor_values):
        if not fid or val is None or val == "":
            continue
        group = fid.get("group")
        key = fid.get("key")
        if group is None or key is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if group == "gwp":
            params["gwp"][key] = num
        elif group == "fertilizer_factors":
            params["fertilizer_factors"][key] = num
        elif group in params:
            params[group][key] = num

    return params
