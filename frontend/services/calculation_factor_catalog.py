"""Catálogo de fatores canônicos para cálculo preliminar (defaults ↔ ontologia)."""

from __future__ import annotations

from typing import Any


FACTOR_GROUPS: tuple[str, ...] = (
    "enteric_ch4_kg_per_animal",
    "manure_kg_per_kg_bw_per_day",
    "manure_ch4_kg_per_kg_manure",
    "energy_co2_kg_per_unit",
    "fertilizer_factors",
    "gwp",
)


def _pending_statuses_for_catalog(catalog: dict[str, Any]) -> dict[str, dict[str, str]]:
    statuses: dict[str, dict[str, str]] = {}
    for group in FACTOR_GROUPS:
        data = catalog.get(group) or {}
        if isinstance(data, dict):
            statuses[group] = {k: "pending" for k in data}
    return statuses


def build_default_factor_catalog(*, source: str = "defaults") -> dict[str, Any]:
    """Monta o catálogo numérico a partir de ``emissions.defaults`` (fonte oficial)."""
    from emissions.defaults import (
        default_energy_co2_kg_per_unit_yearly_basis,
        default_enteric_ch4_kg_per_animal_yearly,
        default_fertilizer_factors,
        default_manure_ch4_kg_per_kg_manure,
        default_manure_kg_per_kg_bw_per_day,
        gwp_ipcc_ar4,
    )

    catalog = {
        "_source": source,
        "_version": "defaults.py:ECOFARM-T1-DAIRY",
        "enteric_ch4_kg_per_animal": dict(default_enteric_ch4_kg_per_animal_yearly()),
        "manure_kg_per_kg_bw_per_day": dict(default_manure_kg_per_kg_bw_per_day()),
        "manure_ch4_kg_per_kg_manure": dict(default_manure_ch4_kg_per_kg_manure()),
        "energy_co2_kg_per_unit": dict(default_energy_co2_kg_per_unit_yearly_basis()),
        "fertilizer_factors": dict(default_fertilizer_factors()),
        "gwp": dict(gwp_ipcc_ar4()),
    }
    catalog["_statuses"] = _pending_statuses_for_catalog(catalog)
    return catalog


def extract_factor_catalog_from_ontology(onto: Any) -> dict[str, Any] | None:
    """Lê EmissionFactor / GWPParameterSet do grafo OWL, se populados."""
    if onto is None:
        return None
    try:
        from ontology.parameter_lifecycle import extract_factor_catalog_with_statuses

        catalog = extract_factor_catalog_with_statuses(onto)
        if catalog is not None:
            return catalog
    except Exception:
        pass

    # Fallback legado sem statuses no grafo
    try:
        factors: dict[str, dict[str, float]] = {
            "enteric_ch4_kg_per_animal": {},
            "manure_kg_per_kg_bw_per_day": {},
            "manure_ch4_kg_per_kg_manure": {},
            "energy_co2_kg_per_unit": {},
            "fertilizer_factors": {},
        }
        ef_cls = getattr(onto, "EmissionFactor", None)
        if ef_cls is not None:
            for ind in ef_cls.instances():
                names = list(getattr(ind, "hasParameterName", None) or [])
                values = list(getattr(ind, "hasParameterValue", None) or [])
                if not names or not values:
                    continue
                param_name = str(names[0])
                value = float(values[0])
                if param_name.startswith("enteric:"):
                    factors["enteric_ch4_kg_per_animal"][param_name.split(":", 1)[1]] = value
                elif param_name.startswith("manure_md:"):
                    factors["manure_kg_per_kg_bw_per_day"][param_name.split(":", 1)[1]] = value
                elif param_name.startswith("manure_ef:"):
                    factors["manure_ch4_kg_per_kg_manure"][param_name.split(":", 1)[1]] = value
                elif param_name.startswith("energy:"):
                    factors["energy_co2_kg_per_unit"][param_name.split(":", 1)[1]] = value
                elif param_name.startswith("fertilizer:"):
                    factors["fertilizer_factors"][param_name.split(":", 1)[1]] = value

        gwp: dict[str, float] = {}
        gwp_cls = getattr(onto, "GWPParameterSet", None)
        if gwp_cls is not None:
            for ind in gwp_cls.instances():
                ch4 = list(getattr(ind, "hasGWP_CH4", None) or [])
                n2o = list(getattr(ind, "hasGWP_N2O", None) or [])
                co2 = list(getattr(ind, "hasGWP_CO2", None) or [])
                if ch4 and ch4[0] is not None:
                    gwp["CH4"] = float(ch4[0])
                if n2o and n2o[0] is not None:
                    gwp["N2O"] = float(n2o[0])
                if co2 and co2[0] is not None:
                    gwp["CO2"] = float(co2[0])
                if gwp:
                    break

        if not any(factors.values()) and not gwp:
            return None

        catalog = build_default_factor_catalog(source="ontology")
        for key, mapping in factors.items():
            if mapping:
                catalog[key] = mapping
        if gwp:
            catalog["gwp"] = {**catalog.get("gwp", {}), **gwp}
        catalog["_source"] = "ontology"
        catalog["_statuses"] = _pending_statuses_for_catalog(catalog)
        return catalog
    except Exception:
        return None
