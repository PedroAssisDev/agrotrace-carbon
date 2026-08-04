"""Materialização explícita do factor_catalog antes do cálculo preliminar.

Defaults entram como ``pending`` (revisáveis), com origem/versão/unidade.
Não inventa valores dentro do calculation_adapter — este serviço é o passo oficial.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from services.calculation_factor_catalog import (
    FACTOR_GROUPS,
    build_default_factor_catalog,
)
from utils.date_helpers import now_iso

logger = logging.getLogger("agrotrace.factor_catalog")

_PROTECTED_STATUSES = frozenset({"corrected", "confirmed", "published"})

# Espelha FACTOR_UNITS do calculation-service (contrato calc_explanation_v1).
_FACTOR_UNITS: dict[str, str] = {
    "enteric_ch4_kg_per_animal": "kg CH4/animal/period",
    "manure_kg_per_kg_bw_per_day": "kg manure/kg BW/day",
    "manure_ch4_kg_per_kg_manure": "kg CH4/kg manure",
    "energy_co2_kg_per_unit": "kg CO2/unit",
    "fertilizer_factors": "kg N2O/kg N or fraction",
    "fertilizer_factors.direct_n2o_emission_factor": "kg N2O/kg N",
    "fertilizer_factors.indirect_n2o_emission_factor": "kg N2O/kg N volatilized",
    "fertilizer_factors.fraction_n_volatilized": "fraction",
    "gwp": "kg CO2e/kg gas",
}


def factor_units_for_catalog() -> dict[str, str]:
    return dict(_FACTOR_UNITS)


def _group_has_values(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return any(not str(k).startswith("_") and v is not None for k, v in data.items())


def missing_required_groups(catalog: dict[str, Any] | None) -> list[str]:
    """Grupos obrigatórios ausentes ou vazios (None / {})."""
    catalog = catalog or {}
    missing: list[str] = []
    for group in FACTOR_GROUPS:
        if not _group_has_values(catalog.get(group)):
            missing.append(group)
    return missing


def catalog_is_complete(catalog: dict[str, Any] | None) -> bool:
    return not missing_required_groups(catalog)


def _pending_count(catalog: dict[str, Any]) -> int:
    statuses = catalog.get("_statuses") or {}
    n = 0
    for group_st in statuses.values():
        if isinstance(group_st, dict):
            n += sum(1 for s in group_st.values() if str(s) == "pending")
    return n


def _merge_defaults_preserving_protected(
    existing: dict[str, Any] | None,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Preenche grupos/chaves ausentes com defaults pending; não sobrescreve protected."""
    out = copy.deepcopy(existing) if existing else {}
    out_statuses: dict[str, dict[str, str]] = dict(out.get("_statuses") or {})
    def_statuses = defaults.get("_statuses") or {}

    for group in FACTOR_GROUPS:
        def_data = defaults.get(group) or {}
        if not isinstance(def_data, dict):
            continue
        cur = out.get(group)
        if not isinstance(cur, dict):
            cur = {}
        group_st = dict(out_statuses.get(group) or {})
        def_group_st = def_statuses.get(group) or {}

        for key, value in def_data.items():
            if str(key).startswith("_"):
                continue
            status = str(group_st.get(key) or "")
            if key in cur and status in _PROTECTED_STATUSES:
                continue
            if key not in cur or cur.get(key) is None or not _group_has_values({key: cur.get(key)}):
                cur[key] = value
                if status not in _PROTECTED_STATUSES:
                    group_st[key] = str(def_group_st.get(key) or "pending")
            elif key not in group_st:
                group_st[key] = str(def_group_st.get(key) or "pending")

        out[group] = cur
        out_statuses[group] = group_st

    out["_statuses"] = out_statuses
    out["_source"] = out.get("_source") or defaults.get("_source") or "defaults"
    out["_version"] = out.get("_version") or defaults.get("_version") or "defaults.py:ECOFARM-T1-DAIRY"
    out["_units"] = factor_units_for_catalog()
    return out


def materialize_factor_catalog(
    cycle: dict[str, Any],
    onto: Any | None = None,
    *,
    actor: str | None = None,
    force_defaults: bool = False,
) -> dict[str, Any]:
    """Garante factor_catalog completo no ciclo (e no OWL se ``onto`` for passado).

    Retorna o catálogo materializado. Defaults entram como ``pending``.
    """
    ontology = dict(cycle.get("ontology") or {})
    existing = ontology.get("factor_catalog")
    if force_defaults or not catalog_is_complete(existing if isinstance(existing, dict) else None):
        defaults = build_default_factor_catalog(source="ontology")
        catalog = _merge_defaults_preserving_protected(
            existing if isinstance(existing, dict) else None,
            defaults,
        )
        filled = missing_required_groups(existing if isinstance(existing, dict) else None)
        action = "filled_missing" if filled else "ensured"
    else:
        catalog = copy.deepcopy(existing)
        catalog.setdefault("_units", factor_units_for_catalog())
        catalog.setdefault("_version", catalog.get("_version") or "defaults.py:ECOFARM-T1-DAIRY")
        catalog.setdefault("_source", catalog.get("_source") or "ontology")
        if "_statuses" not in catalog:
            from services.calculation_factor_catalog import _pending_statuses_for_catalog

            catalog["_statuses"] = _pending_statuses_for_catalog(catalog)
        action = "already_complete"
        filled = []

    if onto is not None:
        try:
            from services.ontology_adapter import _apply_catalog_to_onto

            _apply_catalog_to_onto(onto, catalog)
        except Exception as exc:
            logger.warning("Falha ao aplicar factor_catalog no OWL: %s", exc)

    ontology["factor_catalog"] = catalog
    ontology.setdefault("updated_at", now_iso())
    cycle["ontology"] = ontology

    event = {
        "event": "catalog_materialized",
        "at": now_iso(),
        "actor": actor or "system",
        "action": action,
        "filled_groups": filled,
        "version": catalog.get("_version"),
        "source": catalog.get("_source"),
        "pending_count": _pending_count(catalog),
        "groups": list(FACTOR_GROUPS),
    }
    events = list(cycle.get("ontology_parameter_events") or [])
    events.append(event)
    cycle["ontology_parameter_events"] = events

    logger.info(
        "[FACTOR_CATALOG] materialize cycle=%s action=%s pending=%s filled=%s",
        cycle.get("cycle_id"),
        action,
        event["pending_count"],
        filled,
    )
    return catalog


def ensure_factor_catalog_for_calculation(cycle: dict[str, Any]) -> dict[str, Any]:
    """Materializa se necessário; falha se o catálogo continuar incompleto."""
    onto = None
    try:
        from services import ontology_runtime_cache as onto_cache

        onto = onto_cache.get_ontology(cycle.get("cycle_id"))
    except Exception:
        onto = None

    catalog = materialize_factor_catalog(cycle, onto=onto, actor="calculation_prepare")
    missing = missing_required_groups(catalog)
    if missing:
        raise RuntimeError(
            "Parâmetros obrigatórios ausentes na ontologia (factor_catalog): "
            + ", ".join(missing)
            + ". Insira defaults como pending antes do cálculo."
        )
    gwp = catalog.get("gwp") or {}
    if not _group_has_values(gwp):
        raise RuntimeError("GWP ausente na ontologia (factor_catalog['gwp']).")
    return catalog


def status_to_explanation_origin(status: str | None) -> str:
    """Mapeia lifecycle status → origin do calc_explanation_v1."""
    st = str(status or "").lower()
    if st in _PROTECTED_STATUSES:
        return "configured"
    if st == "pending" or not st:
        return "default"
    return "configured"
