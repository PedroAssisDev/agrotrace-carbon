"""Camada central de consulta à ontologia (trabalho ou publicada)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ontology.cycle_model import (
    _get_dp,
    find_emission_cycle,
    list_cycle_observations,
    normalize_granularity,
)
from ontology.dto import (
    CycleContextDTO,
    EmissionResultDTO,
    EmissionSummaryDTO,
    PropertyOptionDTO,
)
from ontology.parameter_lifecycle import extract_factor_catalog_with_statuses
from ontology.result_lifecycle import list_active_results

SOURCE_LABELS = {
    "enteric": "Fermentação entérica",
    "manure": "Manejo de dejetos",
    "fertilizer": "Fertilizantes",
    "energy": "Energia",
    "total": "Total GEE",
    "intensity": "Intensidade",
}


class OntologyIntegrityError(RuntimeError):
    """Ciclo publicado sem ontologia final ou inconsistência de fonte."""


def resolve_ontology_source(
    *,
    cycle_status: str | None,
    working_path: str | Path | None,
    published_path: str | Path | None,
) -> dict[str, Any]:
    """Resolve qual arquivo OWL usar. Published exige OWL final sem fallback."""
    status = (cycle_status or "").strip()
    if status == "Published":
        if not published_path or not Path(published_path).exists():
            raise OntologyIntegrityError(
                "Ciclo Published sem ontologia final publicada "
                f"(path={published_path!r})."
            )
        return {
            "mode": "published",
            "ontology_path": str(published_path),
            "status": status,
        }
    if not working_path or not Path(working_path).exists():
        raise OntologyIntegrityError(
            f"Ontologia de trabalho ausente (path={working_path!r})."
        )
    return {
        "mode": "working",
        "ontology_path": str(working_path),
        "status": status or "PendingApproval",
    }


def load_ontology_from_path(path: str | Path) -> Any:
    from owlready2 import get_ontology

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"OWL não encontrado: {p}")
    onto = get_ontology(p.as_uri()).load()
    return onto


def _meta(onto_path: str | None, version: str | None) -> dict[str, Any]:
    return {"ontology_path": onto_path, "ontology_version": version}


def list_properties(onto: Any, *, ontology_path: str | None = None, ontology_version: str | None = None) -> list[dict]:
    cls = getattr(onto, "Property", None)
    if cls is None:
        return []
    out: list[dict] = []
    for prop in cls.instances():
        pid = _get_dp(prop, "hasIdentifier") or prop.name
        dto = PropertyOptionDTO(
            property_id=str(pid),
            name=str(_get_dp(prop, "hasPropertyName") or pid),
            municipality=str(_get_dp(prop, "hasLocationName") or ""),
            ontology_path=ontology_path,
            ontology_version=ontology_version,
        )
        out.append(dto.to_dict())
    return sorted(out, key=lambda x: x.get("name") or x["property_id"])


def get_property(onto: Any, property_id: str, **meta) -> dict | None:
    for p in list_properties(onto, **meta):
        if p["property_id"] == property_id:
            return p
    return None


def _cycle_to_dto(cycle: Any, *, ontology_path: str | None, ontology_version: str | None) -> CycleContextDTO:
    props = list(getattr(cycle, "refersToProperty", None) or [])
    prop = props[0] if props else None
    pid = _get_dp(prop, "hasIdentifier") if prop else None
    pname = _get_dp(prop, "hasPropertyName") if prop else None
    gran = _get_dp(cycle, "hasTemporalGranularity") or "monthly"
    try:
        gran = normalize_granularity(str(gran))
    except ValueError:
        gran = "monthly"
    return CycleContextDTO(
        cycle_id=str(_get_dp(cycle, "hasCycleId") or cycle.name),
        property_id=str(pid or ""),
        property_name=str(pname) if pname else None,
        reporting_period=str(_get_dp(cycle, "hasReportingPeriod") or ""),
        temporal_granularity=gran,
        organizational_granularity=str(_get_dp(cycle, "hasOrganizationalGranularity") or "property"),
        status=str(_get_dp(cycle, "hasCycleStatus") or "PendingApproval"),
        period_start=_get_dp(cycle, "hasStartDate"),
        period_end=_get_dp(cycle, "hasEndDate"),
        ontology_path=ontology_path or _get_dp(cycle, "hasWorkingOntologyPath"),
        ontology_version=ontology_version or _get_dp(cycle, "hasOntologyVersion"),
        published_ontology_path=_get_dp(cycle, "hasPublishedOntologyPath"),
        data_status=_get_dp(cycle, "hasCycleStatus"),
    )


def list_cycles(
    onto: Any,
    *,
    property_id: str | None = None,
    status: str | None = None,
    ontology_path: str | None = None,
    ontology_version: str | None = None,
) -> list[dict]:
    cls = getattr(onto, "EmissionCycle", None)
    if cls is None:
        return []
    out: list[dict] = []
    for cycle in cls.instances():
        dto = _cycle_to_dto(cycle, ontology_path=ontology_path, ontology_version=ontology_version)
        if property_id and dto.property_id != property_id:
            continue
        if status and dto.status != status:
            continue
        out.append(dto.to_dict())
    return out


def get_cycle_context(
    onto: Any,
    cycle_id: str,
    *,
    ontology_path: str | None = None,
    ontology_version: str | None = None,
) -> dict | None:
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        return None
    return _cycle_to_dto(cycle, ontology_path=ontology_path, ontology_version=ontology_version).to_dict()


def get_activity_observations(onto: Any, cycle_id: str, **meta) -> list[dict]:
    rows = list_cycle_observations(onto, cycle_id)
    for r in rows:
        r["source"] = "ontology"
        r.update(_meta(meta.get("ontology_path"), meta.get("ontology_version")))
    return rows


def get_calculation_parameters(onto: Any, cycle_id: str | None = None, **meta) -> dict[str, Any]:
    catalog = extract_factor_catalog_with_statuses(onto) or {}
    catalog["source"] = "ontology"
    catalog["cycle_id"] = cycle_id
    catalog.update(_meta(meta.get("ontology_path"), meta.get("ontology_version")))
    return catalog


def get_emission_results(
    onto: Any,
    cycle_id: str,
    *,
    status: str | None = None,
    emission_source: str | None = None,
    gas: str | None = None,
    period: str | None = None,
    ontology_path: str | None = None,
    ontology_version: str | None = None,
    property_id: str | None = None,
) -> list[dict]:
    rows = list_active_results(onto, cycle_id)
    out: list[dict] = []
    for r in rows:
        if status and r.get("status") != status:
            continue
        if emission_source and r.get("emission_source") != emission_source:
            continue
        if gas and str(r.get("gas")).upper() != str(gas).upper():
            continue
        if period and r.get("reporting_period") != period:
            continue
        dto = EmissionResultDTO(
            result_id=str(r.get("result_id") or ""),
            result_key=str(r.get("result_key") or ""),
            cycle_id=cycle_id,
            property_id=property_id,
            formula_id=r.get("formula_id"),
            gas=str(r.get("gas") or "CO2e"),
            emission_source=str(r.get("emission_source") or ""),
            value=r.get("value"),
            unit=r.get("unit"),
            co2e_value=r.get("co2e_value"),
            co2e_unit=r.get("co2e_unit"),
            status=str(r.get("status") or "preliminary"),
            reporting_period=r.get("reporting_period"),
            temporal_granularity=r.get("temporal_granularity"),
            ontology_path=ontology_path,
            ontology_version=ontology_version or r.get("ontology_version"),
            calculated_at=r.get("calculated_at"),
        )
        out.append(dto.to_dict())
    return out


def get_emission_breakdown_by_source(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    rows = get_emission_results(onto, cycle_id, **meta)
    by_source: dict[str, float] = {}
    for r in rows:
        src = r.get("emission_source") or "total"
        if src in {"total", "intensity"}:
            continue
        label = SOURCE_LABELS.get(src, src)
        co2e = r.get("co2e_value")
        if co2e is None:
            continue
        by_source[label] = by_source.get(label, 0.0) + float(co2e)
    total = sum(by_source.values())
    return {
        "cycle_id": cycle_id,
        "by_source": by_source,
        "total_kg": total,
        "rows": [
            {
                "fonte": k,
                "co2e_kg": v,
                "co2e_t": v / 1000.0,
                "participacao_pct": (100.0 * v / total) if total else None,
            }
            for k, v in sorted(by_source.items(), key=lambda x: -x[1])
        ],
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_emission_breakdown_by_gas(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    rows = get_emission_results(onto, cycle_id, **meta)
    by_gas: dict[str, float] = {}
    for r in rows:
        if r.get("emission_source") in {"total", "intensity"}:
            continue
        gas = str(r.get("gas") or "").upper()
        if gas in {"CO2E", "CO2EQ"}:
            continue
        co2e = r.get("co2e_value")
        if co2e is None and gas:
            # use mass * implied already co2e when only value stored as co2e
            continue
        if co2e is not None:
            by_gas[gas] = by_gas.get(gas, 0.0) + float(co2e)
    total = sum(by_gas.values())
    return {
        "cycle_id": cycle_id,
        "by_gas": by_gas,
        "total_kg": total,
        "rows": [
            {
                "gas": k,
                "gas_key": k,
                "co2e_kg": v,
                "co2e_t": v / 1000.0,
                "participacao_pct": (100.0 * v / total) if total else None,
            }
            for k, v in sorted(by_gas.items(), key=lambda x: -x[1])
        ],
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_emission_summary(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    qmeta = {k: meta[k] for k in ("ontology_path", "ontology_version") if k in meta}
    rows = get_emission_results(
        onto,
        cycle_id,
        property_id=meta.get("property_id"),
        **qmeta,
    )
    total = next((r for r in rows if r.get("emission_source") == "total" or r.get("formula_id") == "total_ghg"), None)
    intensity = next((r for r in rows if r.get("emission_source") == "intensity" or r.get("formula_id") == "intensity"), None)
    by_source = get_emission_breakdown_by_source(onto, cycle_id, **qmeta)["by_source"]
    by_gas = get_emission_breakdown_by_gas(onto, cycle_id, **qmeta)["by_gas"]
    obs = get_activity_observations(onto, cycle_id, **qmeta)
    milk = None
    animals = None
    for o in obs:
        var = str(o.get("variable") or "").lower()
        if var in {"milk_production", "milk"} and o.get("value") is not None:
            milk = float(o["value"])
        if var in {"lactating_cows", "number_of_lactating_cows"} and o.get("value") is not None:
            animals = float(o["value"])
    ctx = get_cycle_context(onto, cycle_id, **qmeta) or {}
    dto = EmissionSummaryDTO(
        cycle_id=cycle_id,
        property_id=ctx.get("property_id") or meta.get("property_id"),
        co2e_total_kg=(total or {}).get("co2e_value") or (total or {}).get("value"),
        intensity=(intensity or {}).get("value"),
        milk_liters=milk,
        animals=animals,
        by_source=by_source,
        by_gas=by_gas,
        ontology_path=qmeta.get("ontology_path"),
        ontology_version=qmeta.get("ontology_version"),
        data_status=ctx.get("status"),
    )
    return dto.to_dict()


def get_emission_timeseries(onto: Any, cycle_ids: list[str], **meta) -> dict[str, Any]:
    labels: list[str] = []
    co2e: list[float | None] = []
    intensity: list[float | None] = []
    milk: list[float | None] = []
    by_source_series: dict[str, list[float | None]] = {}
    for cid in cycle_ids:
        ctx = get_cycle_context(onto, cid, **meta) or {}
        summary = get_emission_summary(onto, cid, **meta)
        label = ctx.get("reporting_period") or cid
        labels.append(label)
        co2e.append(summary.get("co2e_total_kg"))
        intensity.append(summary.get("intensity"))
        milk.append(summary.get("milk_liters"))
        for src, val in (summary.get("by_source") or {}).items():
            by_source_series.setdefault(src, [None] * (len(labels) - 1)).append(float(val))
        for src, series in by_source_series.items():
            while len(series) < len(labels):
                series.append(None)
    return {
        "labels": labels,
        "co2e_kg": co2e,
        "intensity": intensity,
        "milk_liters": milk,
        "by_source": by_source_series,
        "has_multi_point": len(labels) >= 2,
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_indicators(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    summary = get_emission_summary(onto, cycle_id, **meta)
    ctx = get_cycle_context(onto, cycle_id, **meta) or {}
    return {
        "summary": summary,
        "cycle": ctx,
        "kpis": {
            "co2e_total_kg": summary.get("co2e_total_kg"),
            "intensity": summary.get("intensity"),
            "milk_liters": summary.get("milk_liters"),
            "animals": summary.get("animals"),
        },
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_parameter_lifecycle(onto: Any, cycle_id: str | None = None, **meta) -> dict[str, Any]:
    return get_calculation_parameters(onto, cycle_id, **meta)


def get_calculation_statuses(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    rows = get_emission_results(onto, cycle_id, **meta)
    by_formula: dict[str, str] = {}
    for r in rows:
        fid = r.get("formula_id") or r.get("emission_source")
        if fid:
            by_formula[str(fid)] = str(r.get("status"))
    return {
        "cycle_id": cycle_id,
        "by_formula": by_formula,
        "all_approved": bool(by_formula) and all(s == "approved" or s == "published" for s in by_formula.values()),
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_review_data(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    return {
        "cycle": get_cycle_context(onto, cycle_id, **meta),
        "parameters": get_calculation_parameters(onto, cycle_id, **meta),
        "observations": get_activity_observations(onto, cycle_id, **meta),
        "results": get_emission_results(onto, cycle_id, **meta),
        "statuses": get_calculation_statuses(onto, cycle_id, **meta),
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_published_cycle(onto: Any, cycle_id: str, **meta) -> dict[str, Any]:
    ctx = get_cycle_context(onto, cycle_id, **meta)
    if not ctx or ctx.get("status") != "Published":
        raise OntologyIntegrityError(f"Ciclo {cycle_id} não está Published na ontologia.")
    return {
        "cycle": ctx,
        "summary": get_emission_summary(onto, cycle_id, **meta),
        "results": get_emission_results(onto, cycle_id, status="published", **meta)
        or get_emission_results(onto, cycle_id, **meta),
        "source": "ontology",
        **_meta(meta.get("ontology_path"), meta.get("ontology_version")),
    }


def get_ontology_version(onto: Any, cycle_id: str | None = None, **meta) -> dict[str, Any]:
    if cycle_id:
        ctx = get_cycle_context(onto, cycle_id, **meta) or {}
        return {
            "cycle_id": cycle_id,
            "ontology_version": ctx.get("ontology_version") or meta.get("ontology_version"),
            "ontology_path": ctx.get("ontology_path") or meta.get("ontology_path"),
            "source": "ontology",
        }
    return {
        "ontology_version": meta.get("ontology_version"),
        "ontology_path": meta.get("ontology_path"),
        "source": "ontology",
    }


def _ind_id(ind: Any) -> str | None:
    val = _get_dp(ind, "hasIdentifier")
    return str(val) if val is not None else None


def list_lots_for_property(onto: Any, property_id: str) -> list[dict[str, Any]]:
    cls = getattr(onto, "Lot", None)
    if cls is None:
        return []
    out: list[dict[str, Any]] = []
    for lot in cls.instances():
        props = list(getattr(lot, "belongsToProperty", None) or [])
        if not props:
            continue
        pid = _ind_id(props[0])
        if pid != property_id:
            continue
        out.append({"lot_id": _ind_id(lot), "property_id": pid})
    return sorted(out, key=lambda x: x.get("lot_id") or "")


def list_animals_for_lot(onto: Any, lot_id: str) -> list[dict[str, Any]]:
    cls = getattr(onto, "Animal", None)
    if cls is None:
        return []
    out: list[dict[str, Any]] = []
    for animal in cls.instances():
        lots = list(getattr(animal, "belongsToLot", None) or [])
        if not lots:
            continue
        lid = _ind_id(lots[0])
        if lid != lot_id:
            continue
        props = list(getattr(animal, "belongsToProperty", None) or [])
        pid = _ind_id(props[0]) if props else None
        out.append({"animal_id": _ind_id(animal), "lot_id": lid, "property_id": pid})
    return sorted(out, key=lambda x: x.get("animal_id") or "")


def resolve_organizational_chain(
    onto: Any,
    *,
    animal_id: str | None = None,
    lot_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve animal → lot → property (or lot → property)."""
    from ontology import iri as iri_mod

    if animal_id:
        animal = onto.search_one(iri=f"*#{iri_mod.animal_iri(animal_id)}")
        if animal is None:
            return None
        lots = list(getattr(animal, "belongsToLot", None) or [])
        props = list(getattr(animal, "belongsToProperty", None) or [])
        lot = lots[0] if lots else None
        prop = props[0] if props else None
        if lot is not None and prop is None:
            lot_props = list(getattr(lot, "belongsToProperty", None) or [])
            prop = lot_props[0] if lot_props else None
        return {
            "animal_id": _ind_id(animal),
            "lot_id": _ind_id(lot) if lot is not None else None,
            "property_id": _ind_id(prop) if prop is not None else None,
        }
    if lot_id:
        lot = onto.search_one(iri=f"*#{iri_mod.lot_iri(lot_id)}")
        if lot is None:
            return None
        props = list(getattr(lot, "belongsToProperty", None) or [])
        prop = props[0] if props else None
        return {
            "animal_id": None,
            "lot_id": _ind_id(lot),
            "property_id": _ind_id(prop) if prop is not None else None,
        }
    return None
