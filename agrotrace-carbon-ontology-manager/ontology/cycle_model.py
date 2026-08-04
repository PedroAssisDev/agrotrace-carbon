"""Upsert de Property, Lot, Animal, EmissionCycle e observações de atividade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ontology import iri as iri_mod

CYCLE_STATUSES = ("PendingApproval", "Approved", "Rejected", "Published")
TEMPORAL_GRANULARITIES = ("daily", "monthly", "annual")
ORGANIZATIONAL_GRANULARITIES = ("animal", "lot", "property")
OBS_STATUSES = ("pending", "corrected", "confirmed", "published")


class OrganizationalConsistencyError(ValueError):
    """Animal/Lot/Property association violates same-property rule."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _set_dp(ind: Any, prop: str, value: Any) -> None:
    if value is None:
        return
    setattr(ind, prop, [value])


def _get_dp(ind: Any, prop: str, default: Any = None) -> Any:
    vals = list(getattr(ind, prop, None) or [])
    return vals[0] if vals else default


def _linked_property_id(ind: Any) -> str | None:
    props = list(getattr(ind, "belongsToProperty", None) or [])
    if not props:
        props = list(getattr(ind, "refersToProperty", None) or [])
    if not props:
        return None
    return _get_dp(props[0], "hasIdentifier")


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


def normalize_organizational_granularity(value: str | None) -> str:
    raw = (value or "property").strip().lower()
    aliases = {
        "animal": "animal",
        "lot": "lot",
        "lote": "lot",
        "property": "property",
        "propriedade": "property",
        "farm": "property",
    }
    out = aliases.get(raw)
    if out is None:
        raise ValueError(
            f"Granularidade organizacional inválida: {value!r}. "
            "Esperado: animal|lot|property."
        )
    return out


def assert_same_property(
    *,
    property_id: str,
    other_property_id: str | None,
    context: str,
) -> None:
    if other_property_id is None:
        return
    if str(property_id) != str(other_property_id):
        raise OrganizationalConsistencyError(
            f"{context}: property_id={property_id!r} diverge de {other_property_id!r}."
        )


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


def find_lot(onto: Any, lot_id: str) -> Any | None:
    local = iri_mod.lot_iri(lot_id)
    return onto.search_one(iri=f"*#{local}")


def upsert_lot(
    onto: Any,
    *,
    lot_id: str,
    property_id: str,
    name: str | None = None,
) -> Any:
    if not lot_id:
        raise ValueError("lot_id é obrigatório.")
    if not property_id:
        raise ValueError("property_id é obrigatório para Lot.")
    prop = upsert_property(onto, property_id=property_id)
    existing = find_lot(onto, lot_id)
    if existing is not None:
        existing_pid = _linked_property_id(existing)
        assert_same_property(
            property_id=property_id,
            other_property_id=existing_pid,
            context=f"Lot {lot_id}",
        )
    local = iri_mod.lot_iri(lot_id)
    with onto:
        if existing is None:
            lot = onto.Lot(local)
        else:
            lot = existing
        _set_dp(lot, "hasIdentifier", str(lot_id))
        lot.belongsToProperty = [prop]
        if name:
            lot.label = [str(name)]
        else:
            lot.label = [str(lot_id)]
    return lot


def find_animal(onto: Any, animal_id: str) -> Any | None:
    local = iri_mod.animal_iri(animal_id)
    return onto.search_one(iri=f"*#{local}")


def upsert_animal(
    onto: Any,
    *,
    animal_id: str,
    property_id: str,
    lot_id: str | None = None,
    name: str | None = None,
) -> Any:
    if not animal_id:
        raise ValueError("animal_id é obrigatório.")
    if not property_id:
        raise ValueError("property_id é obrigatório para Animal.")
    prop = upsert_property(onto, property_id=property_id)
    lot = None
    if lot_id:
        lot = upsert_lot(onto, lot_id=lot_id, property_id=property_id)
        lot_pid = _linked_property_id(lot)
        assert_same_property(
            property_id=property_id,
            other_property_id=lot_pid,
            context=f"Animal {animal_id} → Lot {lot_id}",
        )
    existing = find_animal(onto, animal_id)
    if existing is not None:
        existing_pid = _linked_property_id(existing)
        assert_same_property(
            property_id=property_id,
            other_property_id=existing_pid,
            context=f"Animal {animal_id}",
        )
        if lot_id:
            existing_lots = list(getattr(existing, "belongsToLot", None) or [])
            if existing_lots:
                existing_lot_pid = _linked_property_id(existing_lots[0])
                assert_same_property(
                    property_id=property_id,
                    other_property_id=existing_lot_pid,
                    context=f"Animal {animal_id} lot existente",
                )
    local = iri_mod.animal_iri(animal_id)
    with onto:
        if existing is None:
            animal = onto.Animal(local)
        else:
            animal = existing
        _set_dp(animal, "hasIdentifier", str(animal_id))
        animal.belongsToProperty = [prop]
        if lot is not None:
            animal.belongsToLot = [lot]
        if name:
            animal.label = [str(name)]
        else:
            animal.label = [str(animal_id)]
    return animal


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
    lot_id: str | None = None,
) -> Any:
    if not cycle_id:
        raise ValueError("cycle_id é obrigatório.")
    if status not in CYCLE_STATUSES:
        raise ValueError(f"Status de ciclo inválido: {status!r}")
    gran = normalize_granularity(temporal_granularity)
    org_gran = normalize_organizational_granularity(organizational_granularity)
    if org_gran == "lot" and not lot_id:
        raise ValueError(
            "lot_id é obrigatório quando organizational_granularity='lot'."
        )
    prop = upsert_property(onto, property_id=property_id, name=property_name)
    lot = None
    if lot_id:
        lot = upsert_lot(onto, lot_id=lot_id, property_id=property_id)
    local = iri_mod.cycle_iri(cycle_id)
    existing = onto.search_one(iri=f"*#{local}")
    with onto:
        if existing is None:
            cycle = onto.EmissionCycle(local)
        else:
            cycle = existing
        cycle.refersToProperty = [prop]
        if lot is not None:
            cycle.refersToLot = [lot]
        _set_dp(cycle, "hasCycleId", str(cycle_id))
        _set_dp(cycle, "hasIdentifier", str(cycle_id))
        _set_dp(cycle, "hasReportingPeriod", str(reporting_period))
        _set_dp(cycle, "hasTemporalGranularity", gran)
        _set_dp(cycle, "hasOrganizationalGranularity", org_gran)
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
    lot_id: str | None = None,
    animal_id: str | None = None,
    organizational_granularity: str | None = None,
) -> dict[str, Any]:
    if status not in OBS_STATUSES:
        raise ValueError(f"Status de observação inválido: {status!r}")
    cycle = find_emission_cycle(onto, cycle_id)
    if cycle is None:
        raise ValueError(f"EmissionCycle não encontrado: {cycle_id}")
    cycle_org = _get_dp(cycle, "hasOrganizationalGranularity") or "property"
    org_gran = normalize_organizational_granularity(
        organizational_granularity or cycle_org
    )
    if org_gran == "lot" and not lot_id:
        raise ValueError(
            "lot_id é obrigatório para observação com organizational_granularity='lot'."
        )
    prop = upsert_property(onto, property_id=property_id)
    lot = None
    if lot_id:
        lot = upsert_lot(onto, lot_id=lot_id, property_id=property_id)
    animal = None
    if animal_id:
        animal = upsert_animal(
            onto,
            animal_id=animal_id,
            property_id=property_id,
            lot_id=lot_id,
        )
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
        if lot is not None:
            obs.refersToLot = [lot]
        if animal is not None:
            obs.refersToAnimal = [animal]
        _set_dp(obs, "hasOriginalColumnName", str(variable))
        _set_dp(obs, "hasObservationLifecycleStatus", status)
        _set_dp(obs, "hasObservationOrigin", origin)
        _set_dp(obs, "hasOrganizationalGranularity", org_gran)
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.replace(".", "", 1).replace("-", "", 1).isdigit()
        ):
            _set_dp(obs, "hasNumericValue", float(value))
        else:
            _set_dp(obs, "hasTextValue", str(value))
        if unit:
            _set_dp(obs, "hasExpectedUnit", str(unit))
            _set_dp(obs, "hasResultUnit", str(unit))
        if period:
            _set_dp(obs, "hasReportingPeriod", str(period))
    return {
        "observation_key": obs_key,
        "variable": variable,
        "value": float(value) if isinstance(value, (int, float)) else value,
        "unit": unit,
        "status": status,
        "origin": origin,
        "cycle_id": cycle_id,
        "property_id": property_id,
        "lot_id": lot_id,
        "animal_id": animal_id,
        "organizational_granularity": org_gran,
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
        lots = list(getattr(obs, "refersToLot", None) or [])
        animals = list(getattr(obs, "refersToAnimal", None) or [])
        props = list(getattr(obs, "refersToProperty", None) or [])
        out.append({
            "observation_key": obs.name,
            "variable": var,
            "value": num if num is not None else text,
            "unit": _get_dp(obs, "hasExpectedUnit") or _get_dp(obs, "hasResultUnit"),
            "status": _get_dp(obs, "hasObservationLifecycleStatus", "pending"),
            "origin": _get_dp(obs, "hasObservationOrigin", "ontology"),
            "period": _get_dp(obs, "hasReportingPeriod"),
            "cycle_id": cycle_id,
            "property_id": _get_dp(props[0], "hasIdentifier") if props else None,
            "lot_id": _get_dp(lots[0], "hasIdentifier") if lots else None,
            "animal_id": _get_dp(animals[0], "hasIdentifier") if animals else None,
            "organizational_granularity": _get_dp(obs, "hasOrganizationalGranularity"),
        })
    return out
