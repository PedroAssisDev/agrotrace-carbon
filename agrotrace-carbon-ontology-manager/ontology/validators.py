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


def validate_all(onto: object, *, include_instances: bool = False) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_schema(onto))
    issues.extend(validate_catalogs(onto))
    issues.extend(validate_calculation_methods(onto))
    if include_instances:
        issues.extend(validate_populated_instances(onto))
    return issues
