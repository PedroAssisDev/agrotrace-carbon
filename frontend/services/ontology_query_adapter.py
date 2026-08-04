"""Adapter FE: consulta ontológica (trabalho vs publicada) + DTOs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from services import ontology_runtime_cache as onto_cache
from services.ontology_adapter import get_onto_for_cycle

logger = logging.getLogger("agrotrace.ontology_query")


class OntologyDomainError(RuntimeError):
    pass


def _paths_from_cycle(cycle: dict) -> tuple[str | None, str | None, str | None]:
    ont = cycle.get("ontology") or {}
    exports = ont.get("export_paths") or {}
    working = exports.get("owl") or ont.get("working_ontology_path")
    published = ont.get("published_ontology_path") or exports.get("owl_final")
    if not published and working:
        # convenção: *_final.owl no mesmo diretório
        p = Path(str(working))
        candidate = p.with_name(p.stem + "_final" + p.suffix)
        if candidate.exists():
            published = str(candidate)
        # também agromrv_lite_final.owl
        alt = p.parent / "agromrv_lite_final.owl"
        if alt.exists():
            published = str(alt)
    version = ont.get("ontology_version")
    return working, published, version


def resolve_ontology_source(cycle: dict) -> dict[str, Any]:
    from ontology.query_service import OntologyIntegrityError, resolve_ontology_source as _resolve

    status = (
        cycle.get("current_status")
        or (cycle.get("ontology") or {}).get("publication_status")
        or ((cycle.get("steps") or {}).get("publication") or {}).get("status")
    )
    # Normaliza DONE/COMPLETED de pipeline → Published quando marco final
    pub = (cycle.get("steps") or {}).get("publication") or {}
    if pub.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"} or cycle.get("publication"):
        status = "Published"
    mgr = cycle.get("current_status")
    if mgr in {"Published", "Approved", "Rejected", "PendingApproval"}:
        status = mgr if mgr == "Published" else status

    working, published, version = _paths_from_cycle(cycle)
    try:
        resolved = _resolve(
            cycle_status="Published" if status == "Published" else (status or "PendingApproval"),
            working_path=working,
            published_path=published,
        )
    except OntologyIntegrityError as exc:
        raise OntologyDomainError(str(exc)) from exc
    resolved["ontology_version"] = version
    resolved["cycle_id"] = cycle.get("cycle_id")
    return resolved


def _meta_kwargs(meta: dict) -> dict[str, Any]:
    return {
        "ontology_path": meta.get("ontology_path"),
        "ontology_version": meta.get("ontology_version"),
    }


def _load_onto(cycle: dict) -> tuple[Any, dict[str, Any]]:
    resolved = resolve_ontology_source(cycle)
    path = resolved["ontology_path"]
    cycle_id = cycle.get("cycle_id")
    if resolved["mode"] == "working":
        onto = get_onto_for_cycle(cycle)
    else:
        onto_cache.invalidate(cycle_id)
        from ontology.query_service import load_ontology_from_path

        onto = load_ontology_from_path(path)
        if cycle_id:
            onto_cache.set_ontology(cycle_id, onto)
    meta = {
        "ontology_path": path,
        "ontology_version": resolved.get("ontology_version"),
        "mode": resolved["mode"],
    }
    return onto, meta


def list_properties_from_ontology(cycles: list[dict] | None = None) -> list[dict]:
    """Agrega propriedades a partir das ontologias dos ciclos conhecidos."""
    from utils.file_helpers import list_cycles

    seen: dict[str, dict] = {}
    skip_count = 0
    first_skip: str | None = None
    for cycle in cycles if cycles is not None else list_cycles():
        try:
            onto, meta = _load_onto(cycle)
            from ontology.query_service import list_properties

            for p in list_properties(onto, **_meta_kwargs(meta)):
                seen[p["property_id"]] = p
        except Exception as exc:
            skip_count += 1
            if first_skip is None:
                first_skip = f"{cycle.get('cycle_id')}: {exc}"
            pid = cycle.get("property_id")
            if pid and pid not in seen:
                seen[pid] = {
                    "property_id": pid,
                    "name": cycle.get("property_name") or pid,
                    "source": "ontology",
                    "data_status": "partial_cycle_meta",
                    "ontology_path": ((cycle.get("ontology") or {}).get("export_paths") or {}).get("owl"),
                    "ontology_version": (cycle.get("ontology") or {}).get("ontology_version"),
                }
    if skip_count:
        logger.debug(
            "list_properties skip_summary skipped=%d properties=%d first=%s",
            skip_count,
            len(seen),
            first_skip,
        )
    return sorted(seen.values(), key=lambda x: x.get("name") or x["property_id"])


def list_cycles_from_ontology(
    *,
    property_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    from utils.file_helpers import list_cycles

    out: list[dict] = []
    for cycle in list_cycles():
        if property_id and cycle.get("property_id") != property_id:
            continue
        try:
            onto, meta = _load_onto(cycle)
            from ontology.query_service import get_cycle_context

            ctx = get_cycle_context(onto, cycle["cycle_id"], **_meta_kwargs(meta))
            if ctx is None:
                ctx = _ensure_cycle_projection(cycle, onto, meta)
            if status and ctx.get("status") != status:
                continue
            out.append(ctx)
        except OntologyDomainError:
            raise
        except Exception as exc:
            logger.warning("list_cycles_from_ontology fail %s: %s", cycle.get("cycle_id"), exc)
    return out


def _ensure_cycle_projection(cycle: dict, onto: Any, meta: dict) -> dict:
    from ontology.cycle_model import upsert_emission_cycle
    from ontology.query_service import get_cycle_context
    from services.domain_catalog import normalize_temporal

    gran = normalize_temporal(
        cycle.get("granularity") or cycle.get("frequency") or "monthly"
    ).value
    status = cycle.get("current_status") or "PendingApproval"
    if status not in {"PendingApproval", "Approved", "Rejected", "Published"}:
        pub = (cycle.get("steps") or {}).get("publication") or {}
        if pub.get("status") in {"DONE", "DONE_WARNINGS", "COMPLETED"} or cycle.get("publication"):
            status = "Published"
        else:
            status = "PendingApproval"
    working, published, version = _paths_from_cycle(cycle)
    upsert_emission_cycle(
        onto,
        cycle_id=str(cycle["cycle_id"]),
        property_id=str(cycle.get("property_id") or "UNKNOWN"),
        reporting_period=str(cycle.get("reporting_period") or ""),
        temporal_granularity=gran,
        status=status,
        ontology_version=version,
        working_ontology_path=working,
        published_ontology_path=published,
        property_name=cycle.get("property_name"),
    )
    return get_cycle_context(onto, cycle["cycle_id"], **_meta_kwargs(meta)) or {
        "cycle_id": cycle["cycle_id"],
        "property_id": cycle.get("property_id"),
        "reporting_period": cycle.get("reporting_period"),
        "temporal_granularity": gran,
        "status": status,
        "source": "ontology",
        **_meta_kwargs(meta),
    }


def get_cycle_domain(cycle: dict) -> dict[str, Any]:
    onto, meta = _load_onto(cycle)
    from ontology.query_service import get_cycle_context, get_review_data

    ctx = get_cycle_context(onto, cycle["cycle_id"], **_meta_kwargs(meta))
    if ctx is None:
        ctx = _ensure_cycle_projection(cycle, onto, meta)
    return {
        "cycle": ctx,
        "review": get_review_data(onto, cycle["cycle_id"], **_meta_kwargs(meta)),
        **meta,
    }


def get_emission_summary_for_cycle(cycle: dict) -> dict[str, Any]:
    onto, meta = _load_onto(cycle)
    from ontology.query_service import get_emission_summary

    _ensure_cycle_projection(cycle, onto, meta)
    return get_emission_summary(
        onto, cycle["cycle_id"], property_id=cycle.get("property_id"), **_meta_kwargs(meta)
    )


def get_indicators_for_cycles(cycles: list[dict]) -> dict[str, Any]:
    """Agrega indicadores oficiais a partir de resultados ontológicos (já persistidos)."""
    summaries = []
    by_source: dict[str, float] = {}
    by_gas: dict[str, float] = {}
    total_co2e = 0.0
    total_milk = 0.0
    animals_vals: list[float] = []
    labels: list[str] = []
    series_co2e: list[float | None] = []
    series_intensity: list[float | None] = []
    series_milk: list[float | None] = []

    for cycle in cycles:
        try:
            s = get_emission_summary_for_cycle(cycle)
        except Exception as exc:
            logger.warning("indicator skip %s: %s", cycle.get("cycle_id"), exc)
            continue
        summaries.append(s)
        labels.append((cycle.get("reporting_period") or cycle.get("cycle_id") or ""))
        co2e = s.get("co2e_total_kg")
        series_co2e.append(co2e)
        series_intensity.append(s.get("intensity"))
        series_milk.append(s.get("milk_liters"))
        if co2e is not None:
            total_co2e += float(co2e)
        if s.get("milk_liters") is not None:
            total_milk += float(s["milk_liters"])
        if s.get("animals") is not None:
            animals_vals.append(float(s["animals"]))
        for k, v in (s.get("by_source") or {}).items():
            by_source[k] = by_source.get(k, 0.0) + float(v)
        for k, v in (s.get("by_gas") or {}).items():
            by_gas[k] = by_gas.get(k, 0.0) + float(v)

    intensity = None
    if total_milk > 0 and total_co2e:
        intensity = total_co2e / total_milk

    return {
        "source": "ontology",
        "summaries": summaries,
        "co2e_total_kg": total_co2e if summaries else None,
        "milk_liters": total_milk if summaries else None,
        "intensity": intensity,
        "animals": (sum(animals_vals) / len(animals_vals)) if animals_vals else None,
        "by_source": by_source,
        "by_gas": by_gas,
        "timeseries": {
            "labels": labels,
            "co2e_kg": series_co2e,
            "intensity": series_intensity,
            "milk_liters": series_milk,
            "has_multi_point": len(labels) >= 2,
            "source": "ontology",
        },
        "cycle_count": len(summaries),
    }


def get_review_data_for_cycle(cycle: dict) -> dict[str, Any]:
    onto, meta = _load_onto(cycle)
    from ontology.query_service import get_review_data

    _ensure_cycle_projection(cycle, onto, meta)
    return get_review_data(onto, cycle["cycle_id"], **_meta_kwargs(meta))


def get_breakdown_for_cycle(cycle: dict) -> dict[str, Any]:
    onto, meta = _load_onto(cycle)
    from ontology.query_service import (
        get_emission_breakdown_by_gas,
        get_emission_breakdown_by_source,
    )

    _ensure_cycle_projection(cycle, onto, meta)
    mk = _meta_kwargs(meta)
    return {
        "by_source": get_emission_breakdown_by_source(onto, cycle["cycle_id"], **mk),
        "by_gas": get_emission_breakdown_by_gas(onto, cycle["cycle_id"], **mk),
        "source": "ontology",
        **meta,
    }
