"""Explicação canônica do cálculo (RF009 / RNF005) — leitura e síntese legada."""

from __future__ import annotations

import logging
from typing import Any

from services import direct_imports as di

logger = logging.getLogger("agrotrace.calculation_explanation")

SCHEMA_VERSION = "calc_explanation_v1"


def _legacy_synthesize(cycle: dict) -> dict[str, Any]:
    """Sintetiza calc_explanation_v1 a partir de campos legados do ciclo."""
    calc = cycle.get("calculation") or {}
    method = calc.get("method") or {}
    temporal = calc.get("temporal") or {}
    factors_used = calc.get("factors_used") or {}
    gwp = calc.get("gwp") or factors_used.get("gwp") or {}
    inputs = calc.get("inputs") or {}
    flat = calc.get("flat") or {
        "ch4_enteric_kg": calc.get("ch4_enteric_kg", 0),
        "ch4_manure_kg": calc.get("ch4_manure_kg", 0),
        "n2o_fertilizer_kg": calc.get("n2o_fertilizer_kg", 0),
        "co2_energy_kg": calc.get("co2_energy_kg", 0),
        "co2e_total_kg": calc.get("co2e_total_kg", 0),
    }
    approval = cycle.get("approval") or {}
    approved_by = approval.get("approver") if approval.get("decision") == "APPROVED" else None

    build_fn = getattr(di, "build_calculation_explanation", None)
    if build_fn is None:
        try:
            from emissions.explanation import build_calculation_explanation as build_fn  # type: ignore
        except Exception:
            build_fn = None

    artifacts = []
    if cycle.get("source_artifact_id"):
        artifacts.append({
            "kind": "raw_file",
            "artifact_id": str(cycle["source_artifact_id"]),
            "label": "source_artifact",
        })

    if build_fn is not None:
        try:
            origin_refs = None
            try:
                from emissions.explanation import OriginArtifactRef  # type: ignore

                origin_refs = [
                    OriginArtifactRef(kind=a["kind"], artifact_id=a.get("artifact_id"), label=a.get("label"))
                    for a in artifacts
                ]
            except Exception:
                origin_refs = None
            expl = build_fn(
                flat=flat,
                inputs=inputs,
                factors_used=factors_used,
                gwp=gwp,
                method_code=method.get("code") or "ECOFARM-T1-DAIRY",
                method_version=method.get("version") or "1.0.0",
                implementation_version=method.get("implementation_version") or calc.get("calculation_version") or "0.3.1",
                methodology_label=calc.get("methodology") or method.get("methodology_label") or "IPCC/IDF-compatible",
                temporal_granularity=temporal.get("scope") or cycle.get("frequency"),
                period=cycle.get("reporting_period"),
                days_in_period=temporal.get("days_in_period") or inputs.get("days_in_period"),
                factor_sources=calc.get("factor_sources") or {},
                origin_artifacts=origin_refs,
                calculation_id=cycle.get("calculation_execution_id") or calc.get("preliminary_hash"),
                result_id=cycle.get("calculation_result_set_id") or calc.get("preliminary_hash"),
                cycle_id=cycle.get("cycle_id"),
                executed_by=cycle.get("uploaded_by"),
                approved_by=approved_by,
            )
            data = expl.to_dict() if hasattr(expl, "to_dict") else dict(expl)
            if artifacts and not data.get("origin_artifacts"):
                data["origin_artifacts"] = artifacts
            return data
        except Exception as exc:
            logger.warning("legacy explanation synthesize failed: %s", exc)

    # Fallback mínimo sem serviço
    return {
        "schema_version": SCHEMA_VERSION,
        "calculation_id": cycle.get("calculation_execution_id") or calc.get("preliminary_hash"),
        "result_id": cycle.get("calculation_result_set_id") or calc.get("preliminary_hash"),
        "cycle_id": cycle.get("cycle_id"),
        "method": {
            "code": method.get("code"),
            "version": method.get("version"),
            "implementation_version": method.get("implementation_version"),
            "methodology_label": calc.get("methodology"),
        },
        "period": cycle.get("reporting_period"),
        "temporal_granularity": temporal.get("scope"),
        "organizational_granularity": "property",
        "gwp": {
            "assessment_report": "IPCC AR4",
            "time_horizon": "100y",
            "values": [
                {"name": k, "value": v, "unit": "kg CO2e/kg gas", "origin": "default", "source": "ipcc_ar4"}
                for k, v in gwp.items()
            ],
        },
        "sources": [],
        "origin_artifacts": artifacts,
        "executed_by": cycle.get("uploaded_by"),
        "approved_by": approved_by,
        "factors_used_mirror": factors_used,
        "synthesized": True,
    }


def get_or_build_explanation(cycle: dict) -> dict[str, Any]:
    """Retorna explanation canônica do ciclo; sintetiza se ausente (compatibilidade)."""
    calc = cycle.get("calculation") or {}
    expl = calc.get("explanation")
    if isinstance(expl, dict) and expl.get("schema_version", "").startswith("calc_explanation"):
        # Enrich agents/ids if missing
        out = dict(expl)
        out.setdefault("cycle_id", cycle.get("cycle_id"))
        out.setdefault("calculation_id", cycle.get("calculation_execution_id") or calc.get("preliminary_hash"))
        out.setdefault("result_id", cycle.get("calculation_result_set_id") or calc.get("preliminary_hash"))
        approval = cycle.get("approval") or {}
        if approval.get("decision") == "APPROVED" and not out.get("approved_by"):
            out["approved_by"] = approval.get("approver")
        return out
    return _legacy_synthesize(cycle)


def get_explanation_by_calculation_id(calculation_id: str) -> dict[str, Any] | None:
    from utils.file_helpers import list_cycles

    needle = str(calculation_id)
    for cycle in list_cycles():
        if str(cycle.get("calculation_execution_id") or "") == needle:
            return get_or_build_explanation(cycle)
        calc = cycle.get("calculation") or {}
        expl = calc.get("explanation") or {}
        if str(expl.get("calculation_id") or "") == needle or str(calc.get("preliminary_hash") or "") == needle:
            return get_or_build_explanation(cycle)
    return None


def get_explanation_by_result_id(result_id: str) -> dict[str, Any] | None:
    from utils.file_helpers import list_cycles

    needle = str(result_id)
    for cycle in list_cycles():
        if str(cycle.get("calculation_result_set_id") or "") == needle:
            return get_or_build_explanation(cycle)
        calc = cycle.get("calculation") or {}
        expl = calc.get("explanation") or {}
        if str(expl.get("result_id") or "") == needle or str(calc.get("preliminary_hash") or "") == needle:
            return get_or_build_explanation(cycle)
    return None


def applied_factors_from_explanation(explanation: dict[str, Any], group: str) -> dict[str, Any]:
    """Extrai mapa grupo→{chave: valor} dos fatores aplicados na explanation."""
    out: dict[str, Any] = {}
    prefix = f"{group}."
    for src in explanation.get("sources") or []:
        for fac in src.get("factors") or []:
            name = str(fac.get("name") or "")
            if fac.get("origin") == "absent" or fac.get("value") is None:
                continue
            if name.startswith(prefix):
                out[name[len(prefix):]] = fac.get("value")
            elif group == "gwp" and name.startswith("gwp."):
                out[name.split(".", 1)[1]] = fac.get("value")
            elif group == "gwp" and name in {"CH4", "N2O", "CO2"} and src.get("source_id") == "total":
                out[name] = fac.get("value")
    if group == "gwp" and not out:
        for v in ((explanation.get("gwp") or {}).get("values") or []):
            if v.get("value") is not None and v.get("name"):
                out[str(v["name"])] = v["value"]
    return out


def factor_origin_map(explanation: dict[str, Any], group: str) -> dict[str, str]:
    origins: dict[str, str] = {}
    prefix = f"{group}."
    for src in explanation.get("sources") or []:
        for fac in src.get("factors") or []:
            name = str(fac.get("name") or "")
            if name.startswith(prefix):
                origins[name[len(prefix):]] = str(fac.get("origin") or "default")
            elif group == "gwp" and ((explanation.get("gwp") or {}).get("values")):
                for v in explanation["gwp"]["values"]:
                    if v.get("name"):
                        origins[str(v["name"])] = str(v.get("origin") or "default")
    return origins
