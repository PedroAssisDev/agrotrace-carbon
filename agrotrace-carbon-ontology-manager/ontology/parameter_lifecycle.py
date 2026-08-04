"""Lifecycle de parâmetros de cálculo na ontologia (pending→published)."""

from __future__ import annotations

from typing import Any, Iterable

PARAM_STATUSES = ("pending", "corrected", "confirmed", "published")

# group lógico do cálculo → prefixo hasParameterName
GROUP_TO_PREFIX: dict[str, str] = {
    "enteric_ch4_kg_per_animal": "enteric",
    "manure_kg_per_kg_bw_per_day": "manure_md",
    "manure_ch4_kg_per_kg_manure": "manure_ef",
    "energy_co2_kg_per_unit": "energy",
    "fertilizer_factors": "fertilizer",
}

PREFIX_TO_GROUP: dict[str, str] = {v: k for k, v in GROUP_TO_PREFIX.items()}


def _set_status(ind: Any, status: str) -> None:
    if status not in PARAM_STATUSES:
        raise ValueError(f"Status inválido: {status!r}; esperado {PARAM_STATUSES}")
    ind.hasParameterLifecycleStatus = [status]


def _get_status(ind: Any) -> str:
    vals = list(getattr(ind, "hasParameterLifecycleStatus", None) or [])
    return str(vals[0]) if vals else "pending"


def _find_emission_factor(onto: Any, param_name: str) -> Any | None:
    ef_cls = getattr(onto, "EmissionFactor", None)
    if ef_cls is None:
        return None
    for ind in ef_cls.instances():
        names = list(getattr(ind, "hasParameterName", None) or [])
        if names and str(names[0]) == param_name:
            return ind
    return None


def _find_gwp_set(onto: Any) -> Any | None:
    gwp_cls = getattr(onto, "GWPParameterSet", None)
    if gwp_cls is None:
        return None
    instances = list(gwp_cls.instances())
    return instances[0] if instances else None


def upsert_emission_factor_value(
    onto: Any,
    *,
    group: str,
    key: str,
    value: float,
    status: str = "corrected",
) -> dict[str, Any]:
    """Atualiza ou cria EmissionFactor e define status de lifecycle."""
    prefix = GROUP_TO_PREFIX.get(group)
    if not prefix:
        raise ValueError(f"Grupo de fator desconhecido: {group}")
    param_name = f"{prefix}:{key}"
    ind = _find_emission_factor(onto, param_name)
    if ind is None:
        from ontology import iri as iri_mod

        with onto:
            ind = onto.EmissionFactor(iri_mod.individual_name("ef", f"{prefix}_{key}"))
            ind.label = [param_name]
            ind.hasParameterName = [param_name]
    ind.hasParameterValue = [float(value)]
    _set_status(ind, status)
    return {
        "param_name": param_name,
        "group": group,
        "key": key,
        "value": float(value),
        "status": status,
        "class": "EmissionFactor",
    }


def upsert_gwp_value(
    onto: Any,
    *,
    key: str,
    value: float,
    status: str = "corrected",
) -> dict[str, Any]:
    """Atualiza componente GWP (CH4/N2O/CO2) no GWPParameterSet."""
    ind = _find_gwp_set(onto)
    if ind is None:
        from ontology import iri as iri_mod

        with onto:
            ind = onto.GWPParameterSet(iri_mod.individual_name("gwp", "runtime_gwp_set"))
            ind.label = ["runtime_gwp_set"]
            ind.hasParameterName = ["gwp_set"]
            ind.hasGWP_CO2 = [1.0]
    prop = {"CH4": "hasGWP_CH4", "N2O": "hasGWP_N2O", "CO2": "hasGWP_CO2"}.get(key)
    if not prop:
        raise ValueError(f"Chave GWP inválida: {key}")
    setattr(ind, prop, [float(value)])
    _set_status(ind, status)
    return {
        "param_name": f"gwp:{key}",
        "group": "gwp",
        "key": key,
        "value": float(value),
        "status": status,
        "class": "GWPParameterSet",
    }


def set_parameter_status(
    onto: Any,
    *,
    group: str,
    key: str,
    status: str,
) -> dict[str, Any]:
    """Altera apenas o status de lifecycle de um parâmetro existente."""
    if group == "gwp":
        ind = _find_gwp_set(onto)
        if ind is None:
            raise RuntimeError("GWPParameterSet ausente na ontologia.")
        _set_status(ind, status)
        return {"param_name": f"gwp:{key}", "group": group, "key": key, "status": status}

    prefix = GROUP_TO_PREFIX.get(group)
    if not prefix:
        raise ValueError(f"Grupo de fator desconhecido: {group}")
    param_name = f"{prefix}:{key}"
    ind = _find_emission_factor(onto, param_name)
    if ind is None:
        raise RuntimeError(f"EmissionFactor ausente: {param_name}")
    _set_status(ind, status)
    return {"param_name": param_name, "group": group, "key": key, "status": status}


def set_groups_status(
    onto: Any,
    groups: Iterable[str],
    *,
    status: str,
) -> list[dict[str, Any]]:
    """Define o mesmo status para todos os fatores dos grupos indicados."""
    updated: list[dict[str, Any]] = []
    ef_cls = getattr(onto, "EmissionFactor", None)
    if ef_cls is not None:
        wanted_prefixes = {GROUP_TO_PREFIX[g] for g in groups if g in GROUP_TO_PREFIX}
        for ind in ef_cls.instances():
            names = list(getattr(ind, "hasParameterName", None) or [])
            if not names:
                continue
            name = str(names[0])
            prefix = name.split(":", 1)[0]
            if prefix not in wanted_prefixes:
                continue
            _set_status(ind, status)
            group = PREFIX_TO_GROUP.get(prefix, prefix)
            key = name.split(":", 1)[1] if ":" in name else name
            updated.append({"param_name": name, "group": group, "key": key, "status": status})
    if "gwp" in groups:
        ind = _find_gwp_set(onto)
        if ind is not None:
            _set_status(ind, status)
            updated.append({"param_name": "gwp_set", "group": "gwp", "key": "*", "status": status})
    return updated


def extract_factor_catalog_with_statuses(onto: Any) -> dict[str, Any] | None:
    """Extrai valores + mapa de status a partir do grafo OWL."""
    if onto is None:
        return None
    factors: dict[str, dict[str, float]] = {
        "enteric_ch4_kg_per_animal": {},
        "manure_kg_per_kg_bw_per_day": {},
        "manure_ch4_kg_per_kg_manure": {},
        "energy_co2_kg_per_unit": {},
        "fertilizer_factors": {},
    }
    statuses: dict[str, dict[str, str]] = {k: {} for k in factors}
    statuses["gwp"] = {}

    ef_cls = getattr(onto, "EmissionFactor", None)
    if ef_cls is not None:
        for ind in ef_cls.instances():
            names = list(getattr(ind, "hasParameterName", None) or [])
            values = list(getattr(ind, "hasParameterValue", None) or [])
            if not names or not values:
                continue
            param_name = str(names[0])
            if ":" not in param_name:
                continue
            prefix, key = param_name.split(":", 1)
            group = PREFIX_TO_GROUP.get(prefix)
            if not group:
                continue
            factors[group][key] = float(values[0])
            statuses[group][key] = _get_status(ind)

    gwp: dict[str, float] = {}
    ind = _find_gwp_set(onto)
    if ind is not None:
        st = _get_status(ind)
        for gas, prop in (("CH4", "hasGWP_CH4"), ("N2O", "hasGWP_N2O"), ("CO2", "hasGWP_CO2")):
            vals = list(getattr(ind, prop, None) or [])
            if vals and vals[0] is not None:
                gwp[gas] = float(vals[0])
                statuses["gwp"][gas] = st

    if not any(factors.values()) and not gwp:
        return None

    return {
        "_source": "ontology",
        "_version": "parameter_lifecycle",
        "_statuses": statuses,
        "enteric_ch4_kg_per_animal": factors["enteric_ch4_kg_per_animal"],
        "manure_kg_per_kg_bw_per_day": factors["manure_kg_per_kg_bw_per_day"],
        "manure_ch4_kg_per_kg_manure": factors["manure_ch4_kg_per_kg_manure"],
        "energy_co2_kg_per_unit": factors["energy_co2_kg_per_unit"],
        "fertilizer_factors": factors["fertilizer_factors"],
        "gwp": gwp,
    }


def all_applicable_confirmed(catalog: dict[str, Any], groups: Iterable[str]) -> tuple[bool, str]:
    """Verifica se todos os fatores dos grupos estão confirmed ou published."""
    statuses = catalog.get("_statuses") or {}
    for group in groups:
        group_st = statuses.get(group) or {}
        if not group_st:
            return False, f"Grupo {group} sem status na ontologia."
        for key, st in group_st.items():
            if st not in {"confirmed", "published"}:
                return False, f"Parâmetro {group}.{key} com status {st!r} (exige confirmed)."
    return True, "ok"
