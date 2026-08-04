"""Upsert de Property, EmissionCycle e observações de atividade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ontology import iri as iri_mod

CYCLE_STATUSES = ("PendingApproval", "Approved", "Rejected", "Published")
TEMPORAL_GRANULARITIES = ("daily", "monthly", "annual")
OBS_STATUSES = ("pending", "corrected", "confirmed", "published")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _set_dp(ind: Any, prop: str, value: Any) -> None:
    if value is None:
        return
    setattr(ind, prop, [value])


def _get_dp(ind: Any, prop: str, default: Any = None) -> Any:
    vals = list(getattr(ind, prop, None) or [])
    return vals[0] if vals else default


def normalize_granularity(value: str | None) -> str:
    raw = (value or "monthly").strip().lower()
    aliases = {
        "daily": "daily",
        "day": "daily",
        "monthly": "monthly",
        "month": "monthly",
        "mensal": "monthly",
        "annual": "annual",
        "anual": "annual",
        "yearly": "annual",
        "year": "annual",
    }
    out = aliases.get(raw)
    if out is None:
        raise ValueError(
            f"Granularidade inválida: {value!r}. Esperado: daily|monthly|annual."
        )
    return out


def upsert_property(
    onto: Any,
    *,
    property_id: str,
    name: str | None = None,
    municipality: str | None = None,
    state: str | None = None,
) -> Any:
    if not property_id:
        raise ValueError("property_id é obrigatório.")
    local = iri_mod.property_iri(property_id)
    existing = onto.search_one(iri=f"*#{local}")
    with onto:
        if existing is None:
            prop = onto.Property(local)
        else:
            prop = existing
        _set_dp(prop, "hasIdentifier", str(property_id))
        if name:
            _set_dp(prop, "hasPropertyName", str(name))
            prop.label = [str(name)]
        if municipality:
            _set_dp(prop, "hasLocationName", str(municipality))
        if state and not municipality:
            _set_dp(prop, "hasLocationName", str(state))
    return prop


def upsert_emission_cycle(
    onto: Any,
    *,
    cycle_id: str,
    property_id: str,
    reporting_period: str,
    temporal_granularity: str = "monthly",
    organizational_granularity: str = "property",
    status: str = "PendingApproval",
    period_start: str | None = None,
    period_end: str | None = None,
    ontology_version: str | None = None,
    working_ontology_path: str | None = None,
    published_ontology_path: str | None = None,
    property_name: str | None = None,
) -> Any:
    if not cycle_id:
        raise ValueError("cycle_id é obrigatório.")
    if status not in CYCLE_STATUSES:
        raise ValueError(f"Status de ciclo inválido: {status!r}")
    gran = normalize_granularity(temporal_granularity)
    prop = upsert_property(onto, property_id=property_id, name=property_name)
    local = iri_mod.cycle_iri(cycle_id)
    existing = onto.search_one(iri=f"*#{local}")
    with onto:
        if existing is None:
            cycle = onto.EmissionCycle(local)
        else:
            cycle = existing
        cycle.refersToProperty = [prop]
        _set_dp(cycle, "hasCycleId", str(cycle_id))
        _set_dp(cycle, "hasIdentifier", str(cycle_id))
        _set_dp(cycle, "hasReportingPeriod", str(reporting_period))
        _set_dp(cycle, "hasTemporalGranularity", gran)
        _set_dp(cycle, "hasOrganizationalGranularity", organizational_granularity)
        _set_dp(cycle, "hasCycleStatus", status)
        if period_start:
            _set_dp(cycle, "hasStartDate", str(period_start))
        if period_end:
            _set_dp(cycle, "hasEndDate", str(period_end))
        if ontology_version:
            _set_dp(cycle, "hasOntologyVersion", str(ontology_version))
        if working_ontology_path:
            _set_dp(cycle, "hasWorkingOntologyPath", str(working_ontology_path))
        if published_ontology_path:
            _set_dp(cycle, "hasPublishedOntologyPath", str(published_ontology_path))
        cycle.label = [f"{property_id}:{reporting_period}"]
    return cycle


def find_emission_cycle(onto: Any, cycle_id: str) -> Any | None:
    local = iri_mod.cycle_iri(cycle_id)
    return onto.search_one(iri=f"*#{local}")


def set_cycle_status(onto: Any, cycle_id: str, status: str) -> Any:
    if status not in CYCLE_STATUSES:
        raise ValueError(f"Status de ciclo inválido: {status!r}")
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        raise ValueError(f"EmissionCycle não encontrado: {cycle_id}")
    _set_dp(cycle, "hasCycleStatus", status)
    return cycle


def _find_observation(onto: Any, obs_key: str) -> Any | None:
    return onto.search_one(iri=f"*#{obs_key}")


def upsert_observation(
    onto: Any,
    *,
    cycle_id: str,
    property_id: str,
    variable: str,
    value: float | str,
    unit: str | None = None,
    status: str = "pending",
    origin: str = "normalized",
    period: str | None = None,
    observation_class: str = "QuantitativeObservation",
) -> dict[str, Any]:
    if status not in OBS_STATUSES:
        raise ValueError(f"Status de observação inválido: {status!r}")
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        raise ValueError(f"EmissionCycle não encontrado: {cycle_id}")
    prop = upsert_property(onto, property_id=property_id)
    obs_key = iri_mod.observation_iri(f"cycle_{cycle_id}", variable)
    cls = getattr(onto, observation_class, None) or onto.QuantitativeObservation
    existing = _find_observation(onto, obs_key)
    with onto:
        if existing is None:
            obs = cls(obs_key)
        else:
            obs = existing
        obs.belongsToCycle = [cycle]
        obs.refersToProperty = [prop]
        _set_dp(obs, "hasOriginalColumnName", str(variable))
        _set_dp(obs, "hasObservationLifecycleStatus", status)
        _set_dp(obs, "hasObservationOrigin", origin)
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.replace(".", "", 1).replace("-", "", 1).isdigit()
        ):
            _set_dp(obs, "hasNumericValue", float(value))
        else:
            _set_dp(obs, "hasTextValue", str(value))
        if unit:
            _set_dp(obs, "hasExpectedUnit", str(unit))
            _set_dp(obs, "hasResultUnit", str(unit))
    return {
        "observation_key": obs_key,
        "variable": variable,
        "value": float(value) if isinstance(value, (int, float)) else value,
        "unit": unit,
        "status": status,
        "origin": origin,
        "cycle_id": cycle_id,
        "updated_at": _now_iso(),
    }


def list_cycle_observations(onto: Any, cycle_id: str) -> list[dict[str, Any]]:
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        return []
    out: list[dict[str, Any]] = []
    obs_cls = getattr(onto, "Observation", None)
    if obs_cls is None:
        return out
    for obs in obs_cls.instances():
        cycles = list(getattr(obs, "belongsToCycle", None) or [])
        if not cycles or cycles[0] != cycle:
            continue
        var = _get_dp(obs, "hasOriginalColumnName") or ""
        num = _get_dp(obs, "hasNumericValue")
        text = _get_dp(obs, "hasTextValue")
        out.append({
            "observation_key": obs.name,
            "variable": var,
            "value": num if num is not None else text,
            "unit": _get_dp(obs, "hasExpectedUnit") or _get_dp(obs, "hasResultUnit"),
            "status": _get_dp(obs, "hasObservationLifecycleStatus", "pending"),
            "origin": _get_dp(obs, "hasObservationOrigin", "ontology"),
            "period": _get_dp(obs, "hasReportingPeriod"),
            "cycle_id": cycle_id,
        })
    return out
