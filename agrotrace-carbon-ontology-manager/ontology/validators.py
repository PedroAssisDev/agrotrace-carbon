"""Basic validation for AgroMRV-O Lite ontology."""

from __future__ import annotations

from typing import Any

from ontology.catalogs import CALCULATION_METHODS, CANONICAL_VARIABLES, UNITS
from ontology.schema import (
    REQUIRED_CLASSES,
    REQUIRED_DATA_PROPERTIES,
    REQUIRED_OBJECT_PROPERTIES,
)


def validate_schema(onto: object) -> list[str]:
    issues: list[str] = []
    for cls_name in REQUIRED_CLASSES:
        if not hasattr(onto, cls_name):
            issues.append(f"Missing class: {cls_name}")
    for prop_name in REQUIRED_OBJECT_PROPERTIES:
        if not hasattr(onto, prop_name):
            issues.append(f"Missing object property: {prop_name}")
    for prop_name in REQUIRED_DATA_PROPERTIES:
        if not hasattr(onto, prop_name):
            issues.append(f"Missing data property: {prop_name}")
    return issues


def validate_catalogs(onto: object) -> list[str]:
    issues: list[str] = []
    cache = getattr(onto, "_catalog_cache", {})
    for v in CANONICAL_VARIABLES:
        if v["name"] not in cache.get("variables", {}):
            issues.append(f"Missing canonical variable individual: {v['name']}")
    for u in UNITS:
        if u["name"] not in cache.get("units", {}):
            issues.append(f"Missing unit individual: {u['name']}")
    return issues


def validate_calculation_methods(onto: object) -> list[str]:
    issues: list[str] = []
    for m in CALCULATION_METHODS:
        name = m["name"]
        individuals = [
            i for i in onto.individuals()
            if hasattr(i, "hasFunctionName")
            and i.hasFunctionName
            and i.hasFunctionName[0] == m["function_name"]
        ]
        if not individuals:
            issues.append(f"Missing calculation method individual: {name}")
            continue
        ind = individuals[0]
        if not ind.hasFunctionName:
            issues.append(f"{name}: missing hasFunctionName")
        if not ind.hasModulePath:
            issues.append(f"{name}: missing hasModulePath")
        if m.get("emission_source") and not ind.calculatesEmissionSource:
            issues.append(f"{name}: missing calculatesEmissionSource")
        if m.get("gas") and not ind.calculatesGas:
            issues.append(f"{name}: missing calculatesGas")
        if m.get("result_unit") and not ind.hasResultUnit:
            issues.append(f"{name}: missing hasResultUnit")
        if m.get("requires_gwp_parameter_set"):
            if not getattr(ind, "requiresGWPParameterSet", None):
                issues.append(f"{name}: must require GWPParameterSet")
            if not ind.usesGWPParameterSet:
                issues.append(f"{name}: must link usesGWPParameterSet")
    return issues


def validate_populated_instances(onto: object) -> list[str]:
    issues: list[str] = []
    obs_class = getattr(onto, "Observation", None)
    if obs_class is None:
        return ["Observation class missing"]
    for obs in obs_class.instances():
        if not obs.observesVariable:
            issues.append(f"Observation {obs.name} missing observesVariable")
        if not obs.hasOrganizationalContext:
            issues.append(f"Observation {obs.name} missing organizational context")
        if not obs.hasTemporalContext:
            issues.append(f"Observation {obs.name} missing temporal context")
        if issubclass(obs.__class__, getattr(onto, "QuantitativeObservation")):
            vals = list(obs.hasNumericValue) if obs.hasNumericValue else []
            if len(vals) == 0:
                issues.append(f"QuantitativeObservation {obs.name} missing numeric value")
            if not obs.hasUnit:
                issues.append(f"QuantitativeObservation {obs.name} missing unit")
        elif issubclass(obs.__class__, getattr(onto, "QualitativeObservation")):
            if not obs.hasTextValue:
                issues.append(f"QualitativeObservation {obs.name} missing text value")
    return issues


def _entity_property_id(ind: Any) -> str | None:
    props = list(getattr(ind, "belongsToProperty", None) or [])
    if not props:
        props = list(getattr(ind, "refersToProperty", None) or [])
    if not props:
        return None
    vals = list(getattr(props[0], "hasIdentifier", None) or [])
    return str(vals[0]) if vals else None


def _entity_id(ind: Any) -> str:
    vals = list(getattr(ind, "hasIdentifier", None) or [])
    return str(vals[0]) if vals else str(getattr(ind, "name", ""))


def validate_organizational_consistency(onto: object) -> list[str]:
    """Check Lot/Animal/Property membership and lot-scoped observations."""
    issues: list[str] = []
    lot_cls = getattr(onto, "Lot", None)
    animal_cls = getattr(onto, "Animal", None)
    obs_cls = getattr(onto, "Observation", None)

    if lot_cls is not None:
        for lot in lot_cls.instances():
            if not list(getattr(lot, "belongsToProperty", None) or []):
                issues.append(f"Lot {_entity_id(lot)} missing belongsToProperty")

    if animal_cls is not None:
        for animal in animal_cls.instances():
            animal_pid = _entity_property_id(animal)
            lots = list(getattr(animal, "belongsToLot", None) or [])
            if lots:
                lot_pid = _entity_property_id(lots[0])
                if animal_pid and lot_pid and animal_pid != lot_pid:
                    issues.append(
                        f"Animal {_entity_id(animal)} property={animal_pid} "
                        f"diverges from Lot property={lot_pid}"
                    )
            # belongsToProperty recommended when Animal was created via upsert_animal;
            # legacy animals without it are tolerated (compatibilidade).

    if obs_cls is not None:
        for obs in obs_cls.instances():
            org_vals = list(getattr(obs, "hasOrganizationalGranularity", None) or [])
            org_gran = str(org_vals[0]).lower() if org_vals else ""
            if org_gran in ("lot", "lote"):
                if not list(getattr(obs, "refersToLot", None) or []):
                    issues.append(
                        f"Observation {obs.name} with granularity=lot missing refersToLot"
                    )
            obs_pid = _entity_property_id(obs)
            lots = list(getattr(obs, "refersToLot", None) or [])
            if obs_pid and lots:
                lot_pid = _entity_property_id(lots[0])
                if lot_pid and obs_pid != lot_pid:
                    issues.append(
                        f"Observation {obs.name} property={obs_pid} "
                        f"diverges from Lot property={lot_pid}"
                    )
    return issues


def validate_all(onto: object, *, include_instances: bool = False) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_schema(onto))
    issues.extend(validate_catalogs(onto))
    issues.extend(validate_calculation_methods(onto))
    issues.extend(validate_organizational_consistency(onto))
    if include_instances:
        issues.extend(validate_populated_instances(onto))
    return issues
