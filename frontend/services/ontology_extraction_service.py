"""Extração de variáveis canônicas a partir da ontologia e projeções."""

from __future__ import annotations

import re
from typing import Any

from services.indicator_extraction_service import cycle_records, extract_variable_from_cycle, num
from services.ontology_indicator_registry import (
    ONTOLOGY_VAR_ALIASES,
    VARIABLE_CLASS_MAP,
    ontology_class_for,
    ontology_var_aliases,
)

_ORIGIN_PRIORITY = {
    "ontology": 0,
    "canonical_projection": 1,
    "calculation_snapshot": 2,
    "normalized_fallback": 3,
}

ORIGIN_LABELS = {
    "ontology": "Ontologia",
    "canonical_projection": "Projeção canônica",
    "calculation_snapshot": "Snapshot do cálculo",
    "normalized_fallback": "Normalizado (fallback)",
}

# Chaves de projeção canônica → ontology_var
_PROJECTION_FIELD_MAP: dict[str, str] = {
    "milkproduction": "milk_production",
    "milksales": "milk_sales",
    "lactatingcows": "lactating_cows",
    "numberoflactatingcows": "lactating_cows",
    "drycows": "dry_cows",
    "numberofdrycows": "dry_cows",
    "heifers": "heifers",
    "calves": "calves",
    "bulls": "bulls",
    "diesel": "diesel",
    "gasoline": "gasoline",
    "electricitygrid": "electricity_grid",
    "photovoltaicenergy": "photovoltaic_energy",
    "organicfertilizer": "organic_fertilizer",
    "nonorganicfertilizer": "non_organic_fertilizer",
    "lactatingcowsweight": "lactating_cows_weight",
    "weight": "weight",
    "totalfeedinput": "total_feed_input",
    "pasturearea": "pasture_area",
}

# Nomes normalizados/brutos → ontology_var
_RAW_NAME_MAP: dict[str, str] = {
    "lactating_cows": "lactating_cows",
    "dry_cows": "dry_cows",
    "heifers": "heifers",
    "calves": "calves",
    "bulls": "bulls",
    "milk_production": "milk_production",
    "milk": "milk",
    "total_milk_production": "total_milk_production",
    "diesel": "diesel",
    "electricity_grid": "electricity_grid",
    "electricity": "electricity_grid",
    "non_organic_fertilizer": "non_organic_fertilizer",
    "organic_fertilizer": "organic_fertilizer",
    "nitrogen_applied": "non_organic_fertilizer",
    "body_weight": "lactating_cows_weight",
    "lactating_cows_weight": "lactating_cows_weight",
}


def origin_label(origin: str | None) -> str:
    return ORIGIN_LABELS.get(origin or "", origin or "—")


def normalize_to_ontology_var(raw_name: str) -> str | None:
    """Normaliza nome bruto/projeção para ontology_var do registry."""
    if not raw_name:
        return None
    key = re.sub(r"[^a-z0-9]", "", str(raw_name).lower())
    if key in _PROJECTION_FIELD_MAP:
        return _PROJECTION_FIELD_MAP[key]
    snake = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", str(raw_name)).lower().replace(" ", "_")
    if snake in _RAW_NAME_MAP:
        return _RAW_NAME_MAP[snake]
    if snake in VARIABLE_CLASS_MAP:
        return snake
    for ov, aliases in ONTOLOGY_VAR_ALIASES.items():
        if snake == ov or snake in aliases:
            return ov
    return snake if snake else None


def _infer_unit(ontology_var: str) -> str:
    v = ontology_var.lower()
    if "milk" in v or v == "productivity":
        return "L"
    if any(x in v for x in ("cow", "heifer", "calf", "bull", "herd")):
        return "head"
    if "weight" in v or v == "weight":
        return "kg"
    if "diesel" in v or "gasoline" in v or "fuel" in v:
        return "L"
    if "electric" in v or "photovoltaic" in v:
        return "kWh"
    if "fertilizer" in v or "nitrogen" in v:
        return "kg"
    if "area" in v or "pasture" in v:
        return "ha"
    if "feed" in v:
        return "kg"
    return "—"


def _var_record(
    ontology_var: str,
    value: Any,
    *,
    unit: str | None = None,
    origin: str,
    source_field: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    return {
        "ontology_var": ontology_var,
        "variable": ontology_var,
        "value": value,
        "unit": unit or _infer_unit(ontology_var),
        "ontology_class": ontology_class_for(ontology_var),
        "origin": origin,
        "source_field": source_field or ontology_var,
        "period": period,
        "status": "VALID",
    }


def _period_matches(record: dict, reporting_period: str | None) -> bool:
    if not reporting_period:
        return True
    for key in ("periodStart", "periodEnd", "period", "periodo", "date"):
        val = str(record.get(key) or "")
        if reporting_period in val[:7] or reporting_period in val[:4]:
            return True
    return False


def parse_canonical_projection(
    projections: list[dict],
    reporting_period: str | None = None,
) -> list[dict]:
    """Extrai variáveis de wrapper.canonical_projection.projections."""
    out: list[dict] = []
    seen: set[str] = set()
    for row in projections or []:
        if not isinstance(row, dict):
            continue
        if reporting_period and not _period_matches(row, reporting_period):
            continue
        period = reporting_period
        for key, val in row.items():
            if key.startswith("Property.") or key.endswith(".periodStart") or key.endswith(".periodEnd"):
                if key.endswith(".periodStart"):
                    period = str(val)[:7] if val else period
                continue
            if not isinstance(val, (int, float)):
                continue
            field = key.split(".")[-1] if "." in key else key
            ov = normalize_to_ontology_var(field)
            if not ov or ov in seen:
                continue
            seen.add(ov)
            out.append(_var_record(ov, val, origin="canonical_projection", source_field=key, period=period))
    return out


def _extract_from_snapshot(cycle: dict) -> list[dict]:
    ont = cycle.get("ontology") or {}
    snap = ont.get("canonical_variables") or []
    out: list[dict] = []
    for v in snap:
        if not isinstance(v, dict):
            continue
        ov = v.get("ontology_var") or v.get("variable")
        if not ov:
            continue
        out.append({
            **v,
            "ontology_var": ov,
            "variable": ov,
            "origin": v.get("origin") or "ontology",
            "ontology_class": v.get("ontology_class") or ontology_class_for(str(ov)),
        })
    return out


def _extract_from_calculation_inputs(cycle: dict) -> list[dict]:
    inputs = (cycle.get("calculation") or {}).get("inputs") or {}
    if not inputs:
        return []
    out: list[dict] = []
    hc = inputs.get("headcounts_by_category") or {}
    mapping = {
        "Lactating_Cows": "lactating_cows",
        "Dry_Cows": "dry_cows",
        "Heifers": "heifers",
        "Calves": "calves",
        "Bulls": "bulls",
    }
    for calc_key, ov in mapping.items():
        val = hc.get(calc_key)
        if val is not None and val != "":
            out.append(_var_record(ov, val, unit="head", origin="calculation_snapshot", source_field=calc_key))

    ml = inputs.get("milk_liters")
    if ml is not None:
        out.append(_var_record("milk_production", ml, unit="L", origin="calculation_snapshot", source_field="milk_liters"))

    n = inputs.get("nitrogen_applied_kg")
    if n is not None:
        out.append(_var_record("non_organic_fertilizer", n, unit="kg", origin="calculation_snapshot", source_field="nitrogen_applied_kg"))

    energy = inputs.get("energy_consumption_by_vector") or {}
    for calc_key, ov in (("Diesel", "diesel"), ("Electricity_Grid", "electricity_grid"), ("Gasoline", "gasoline")):
        val = energy.get(calc_key)
        if val is not None:
            out.append(_var_record(ov, val, origin="calculation_snapshot", source_field=calc_key))

    bw = inputs.get("body_weight_kg_by_category") or {}
    if bw.get("Lactating_Cows"):
        out.append(_var_record("lactating_cows_weight", bw["Lactating_Cows"], unit="kg", origin="calculation_snapshot", source_field="body_weight"))

    return out


def _extract_from_normalized_fallback(cycle: dict) -> list[dict]:
    """Fallback mapeado a partir de normalized_data / wrapper payload."""
    records = cycle_records(cycle)
    if not records:
        return []
    rp = cycle.get("reporting_period")
    out: list[dict] = []
    seen: set[str] = set()

    for rec in records:
        var = rec.get("variable") or rec.get("variavel")
        if var:
            ov = normalize_to_ontology_var(str(var))
            if not ov or ov in seen:
                continue
            val = rec.get("value", rec.get("valor"))
            if val is None:
                continue
            seen.add(ov)
            out.append(_var_record(
                ov, val,
                unit=rec.get("unit") or rec.get("unidade") or _infer_unit(ov),
                origin="normalized_fallback",
                source_field=str(var),
                period=rec.get("period") or rp,
            ))
        else:
            skip = {"year", "property_name", "property", "period", "date", "_temporal_context"}
            for k, v in rec.items():
                if k.startswith("_") or k in skip or not isinstance(v, (int, float)):
                    continue
                ov = normalize_to_ontology_var(k)
                if not ov or ov in seen:
                    continue
                seen.add(ov)
                out.append(_var_record(ov, v, origin="normalized_fallback", source_field=k, period=rp))

    for ov in list(seen):
        val = extract_variable_from_cycle(cycle, ov)
        if val is not None and not any(x["ontology_var"] == ov for x in out):
            out.append(_var_record(ov, val, origin="normalized_fallback", source_field=ov))

    return out


def _merge_by_priority(sources: list[list[dict]]) -> list[dict]:
    merged: dict[str, dict] = {}
    for batch in sources:
        for v in batch:
            ov = v.get("ontology_var") or v.get("variable")
            if not ov:
                continue
            prev = merged.get(ov)
            if prev is None:
                merged[ov] = v
                continue
            p_new = _ORIGIN_PRIORITY.get(v.get("origin", ""), 99)
            p_old = _ORIGIN_PRIORITY.get(prev.get("origin", ""), 99)
            if p_new < p_old:
                merged[ov] = v
    return list(merged.values())


def extract_ontology_variables(cycle: dict) -> list[dict]:
    """Pool unificado de variáveis ontológicas com prioridade de fonte."""
    wrapper = cycle.get("wrapper") or {}
    proj = wrapper.get("canonical_projection") or {}
    projections = proj.get("projections") if isinstance(proj, dict) else None
    rp = cycle.get("reporting_period")

    from_projection = parse_canonical_projection(projections or [], rp) if projections else []

    return _merge_by_priority([
        _extract_from_snapshot(cycle),
        from_projection,
        _extract_from_calculation_inputs(cycle),
        _extract_from_normalized_fallback(cycle),
    ])


def build_canonical_variables_snapshot(cycle: dict) -> list[dict]:
    """Monta snapshot leve para persistir em cycle['ontology']['canonical_variables']."""
    wrapper = cycle.get("wrapper") or {}
    proj = wrapper.get("canonical_projection") or {}
    projections = proj.get("projections") if isinstance(proj, dict) else None
    rp = cycle.get("reporting_period")

    from_projection = parse_canonical_projection(projections or [], rp) if projections else []
    from_normalized = _extract_from_normalized_fallback(cycle)

    merged = _merge_by_priority([from_projection, from_normalized])
    for v in merged:
        # Nunca rotular como ontology se não veio de leitura OWL
        if v.get("origin") == "canonical_projection":
            v["origin"] = "canonical_projection"
        elif v.get("origin") == "normalized_fallback":
            v["origin"] = "normalized_fallback"
    return merged


def build_canonical_variables_snapshot_from_batch(
    normalized_batch: dict,
    reporting_period: str | None = None,
) -> list[dict]:
    """Snapshot a partir do wrapper/normalized_payload na etapa ontology."""
    cycle_stub = {
        "reporting_period": reporting_period,
        "wrapper": normalized_batch,
        "normalized_data": normalized_batch.get("normalized_payload") or [],
    }
    return build_canonical_variables_snapshot(cycle_stub)


def find_ontology_variable(pool: list[dict], ontology_var: str) -> dict | None:
    """Busca variável no pool por ontology_var ou alias."""
    targets = set(ontology_var_aliases(ontology_var))
    for v in pool:
        ov = v.get("ontology_var") or v.get("variable")
        if ov in targets:
            return v
    return None
