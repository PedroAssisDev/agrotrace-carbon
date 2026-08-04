"""Lifecycle e upsert de EmissionResult / AggregationResult na ontologia."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ontology import iri as iri_mod
from ontology.cycle_model import find_emission_cycle, upsert_emission_cycle, upsert_property

RESULT_STATUSES = ("preliminary", "recalculated", "approved", "published")

_GAS_CLASS = {
    "CH4": "CH4EmissionResult",
    "N2O": "N2OEmissionResult",
    "CO2": "CO2EmissionResult",
    "CO2e": "CO2EquivalentResult",
    "CO2E": "CO2EquivalentResult",
}

_SOURCE_CLASS = {
    "enteric": "EntericFermentation",
    "enteric_fermentation": "EntericFermentation",
    "fermentação entérica": "EntericFermentation",
    "manure": "ManureManagement",
    "manure_management": "ManureManagement",
    "manejo de dejetos": "ManureManagement",
    "fertilizer": "FertilizerApplication",
    "fertilizers": "FertilizerApplication",
    "fertilizantes": "FertilizerApplication",
    "energy": "EnergyUse",
    "energia": "EnergyUse",
    "total": "TotalGHG",
    "total_ghg": "TotalGHG",
    "intensity": "TotalGHG",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _set_dp(ind: Any, prop: str, value: Any) -> None:
    if value is None:
        return
    setattr(ind, prop, [value])


def _get_dp(ind: Any, prop: str, default: Any = None) -> Any:
    vals = list(getattr(ind, prop, None) or [])
    return vals[0] if vals else default


def _result_class(onto: Any, gas: str) -> Any:
    name = _GAS_CLASS.get(str(gas).upper(), "EmissionResult")
    return getattr(onto, name, None) or onto.EmissionResult


def _link_gas_source(onto: Any, ind: Any, gas: str, emission_source: str) -> None:
    gas_map = {"CH4": "Methane", "N2O": "NitrousOxide", "CO2": "CarbonDioxide", "CO2E": "CarbonDioxide", "CO2e": "CarbonDioxide"}
    gname = gas_map.get(str(gas), None)
    if gname and hasattr(onto, gname):
        gcls = getattr(onto, gname)
        instances = list(gcls.instances())
        if not instances:
            with onto:
                instances = [gcls(iri_mod.individual_name("gas", gname))]
        ind.calculatesGas = [instances[0]]
    src_key = (emission_source or "").strip().lower()
    sname = _SOURCE_CLASS.get(src_key) or _SOURCE_CLASS.get(src_key.replace(" ", "_"))
    if sname and hasattr(onto, sname):
        scls = getattr(onto, sname)
        instances = list(scls.instances())
        if not instances:
            with onto:
                instances = [scls(iri_mod.individual_name("src", sname))]
        ind.calculatesEmissionSource = [instances[0]]


def find_result_by_key(onto: Any, result_key: str) -> Any | None:
    cls = getattr(onto, "CalculationResult", None)
    if cls is None:
        return None
    for ind in cls.instances():
        if _get_dp(ind, "hasResultKey") == result_key and _get_dp(ind, "isActiveResult", True):
            return ind
    return None


def upsert_emission_result(
    onto: Any,
    *,
    cycle_id: str,
    property_id: str,
    reporting_period: str,
    temporal_granularity: str,
    formula_id: str,
    gas: str,
    value: float,
    unit: str,
    co2e_value: float | None = None,
    co2e_unit: str = "kg CO2e",
    emission_source: str = "",
    organizational_granularity: str = "property",
    status: str = "preliminary",
    method_id: str | None = None,
    method_version: str | None = None,
    ontology_version: str | None = None,
    property_name: str | None = None,
) -> dict[str, Any]:
    if status not in RESULT_STATUSES:
        raise ValueError(f"Status de resultado inválido: {status!r}")
    if value is None:
        raise ValueError("value de EmissionResult é obrigatório.")

    from ontology.cycle_model import normalize_granularity

    gran = normalize_granularity(temporal_granularity)
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        cycle = upsert_emission_cycle(
            onto,
            cycle_id=cycle_id,
            property_id=property_id,
            reporting_period=reporting_period,
            temporal_granularity=gran,
            organizational_granularity=organizational_granularity,
            property_name=property_name,
        )
    prop = upsert_property(onto, property_id=property_id, name=property_name)

    result_key = iri_mod.make_result_key(
        cycle_id=cycle_id,
        formula_id=formula_id,
        gas=gas,
        period=reporting_period,
        granularity=gran,
        org_scope=organizational_granularity,
        emission_source=emission_source,
    )
    previous = find_result_by_key(onto, result_key)
    cls = _result_class(onto, gas)
    local = iri_mod.result_iri(result_key)
    calculated_at = _now_iso()

    with onto:
        if previous is not None and status in {"recalculated", "preliminary"}:
            _set_dp(previous, "isActiveResult", False)
            prev_status = _get_dp(previous, "hasResultLifecycleStatus")
            if prev_status == "preliminary" and status == "recalculated":
                pass
            ind = cls(f"{local}_{iri_mod.short_hash(calculated_at)}")
            ind.hasPreviousResult = [previous]
        elif previous is not None:
            ind = previous
        else:
            ind = cls(local)

        ind.belongsToCycle = [cycle]
        ind.refersToProperty = [prop]
        _set_dp(ind, "hasResultKey", result_key)
        _set_dp(ind, "hasNumericResult", float(value))
        _set_dp(ind, "hasResultUnit", str(unit))
        _set_dp(ind, "hasResultLifecycleStatus", status)
        _set_dp(ind, "isActiveResult", True)
        _set_dp(ind, "hasFormulaId", str(formula_id))
        _set_dp(ind, "hasReportingPeriod", str(reporting_period))
        _set_dp(ind, "hasTemporalGranularity", gran)
        _set_dp(ind, "hasOrganizationalGranularity", organizational_granularity)
        _set_dp(ind, "hasCalculatedAt", calculated_at)
        if co2e_value is not None:
            _set_dp(ind, "hasCO2eValue", float(co2e_value))
            _set_dp(ind, "hasCO2eUnit", str(co2e_unit))
        if method_id:
            _set_dp(ind, "hasMethodId", str(method_id))
        if method_version:
            _set_dp(ind, "hasMethodVersion", str(method_version))
        if ontology_version:
            _set_dp(ind, "hasOntologyVersion", str(ontology_version))
        _link_gas_source(onto, ind, gas, emission_source)

    return {
        "result_key": result_key,
        "result_id": ind.name,
        "cycle_id": cycle_id,
        "property_id": property_id,
        "reporting_period": reporting_period,
        "temporal_granularity": gran,
        "organizational_granularity": organizational_granularity,
        "formula_id": formula_id,
        "emission_source": emission_source,
        "gas": gas,
        "value": float(value),
        "unit": unit,
        "co2e_value": float(co2e_value) if co2e_value is not None else None,
        "co2e_unit": co2e_unit,
        "status": status,
        "method_id": method_id,
        "method_version": method_version,
        "ontology_version": ontology_version,
        "calculated_at": calculated_at,
        "active": True,
    }


def set_results_status(
    onto: Any,
    cycle_id: str,
    status: str,
    *,
    formula_ids: list[str] | None = None,
) -> int:
    if status not in RESULT_STATUSES:
        raise ValueError(f"Status de resultado inválido: {status!r}")
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        return 0
    cls = getattr(onto, "CalculationResult", None)
    if cls is None:
        return 0
    n = 0
    for ind in cls.instances():
        cycles = list(getattr(ind, "belongsToCycle", None) or [])
        if not cycles or cycles[0] != cycle:
            continue
        if not _get_dp(ind, "isActiveResult", True):
            continue
        fid = _get_dp(ind, "hasFormulaId")
        if formula_ids and fid not in formula_ids:
            continue
        _set_dp(ind, "hasResultLifecycleStatus", status)
        n += 1
    return n


def list_active_results(onto: Any, cycle_id: str) -> list[dict[str, Any]]:
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        return []
    cls = getattr(onto, "CalculationResult", None)
    if cls is None:
        return []
    out: list[dict[str, Any]] = []
    for ind in cls.instances():
        cycles = list(getattr(ind, "belongsToCycle", None) or [])
        if not cycles or cycles[0] != cycle:
            continue
        if not _get_dp(ind, "isActiveResult", True):
            continue
        out.append({
            "result_key": _get_dp(ind, "hasResultKey"),
            "result_id": ind.name,
            "cycle_id": cycle_id,
            "formula_id": _get_dp(ind, "hasFormulaId"),
            "gas": _infer_gas(ind),
            "emission_source": _infer_source(ind),
            "value": _get_dp(ind, "hasNumericResult"),
            "unit": _get_dp(ind, "hasResultUnit"),
            "co2e_value": _get_dp(ind, "hasCO2eValue"),
            "co2e_unit": _get_dp(ind, "hasCO2eUnit"),
            "status": _get_dp(ind, "hasResultLifecycleStatus", "preliminary"),
            "reporting_period": _get_dp(ind, "hasReportingPeriod"),
            "temporal_granularity": _get_dp(ind, "hasTemporalGranularity"),
            "method_id": _get_dp(ind, "hasMethodId"),
            "method_version": _get_dp(ind, "hasMethodVersion"),
            "ontology_version": _get_dp(ind, "hasOntologyVersion"),
            "calculated_at": _get_dp(ind, "hasCalculatedAt"),
        })
    return out


def _infer_gas(ind: Any) -> str:
    gases = list(getattr(ind, "calculatesGas", None) or [])
    if not gases:
        name = ind.__class__.__name__
        if "CH4" in name:
            return "CH4"
        if "N2O" in name:
            return "N2O"
        if "CO2Equivalent" in name or "CO2e" in name:
            return "CO2e"
        if "CO2" in name:
            return "CO2"
        return "CO2e"
    n = gases[0].__class__.__name__
    return {"Methane": "CH4", "NitrousOxide": "N2O", "CarbonDioxide": "CO2"}.get(n, "CO2e")


def _infer_source(ind: Any) -> str:
    srcs = list(getattr(ind, "calculatesEmissionSource", None) or [])
    if not srcs:
        return ""
    n = srcs[0].__class__.__name__
    return {
        "EntericFermentation": "enteric",
        "ManureManagement": "manure",
        "FertilizerApplication": "fertilizer",
        "EnergyUse": "energy",
        "TotalGHG": "total",
    }.get(n, n)
