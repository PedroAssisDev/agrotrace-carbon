"""Guardião de disponibilidade de dados para widgets gerenciais."""

from __future__ import annotations

from typing import Any

from services.cycle_status_service import resolve_managerial_status
from services.widget_registry import WidgetSpec, get_widget_specs_for_screen


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _farm_type(cycle: dict, property_profile: dict | None) -> str:
    prod = (property_profile or {}).get("production_type") or cycle.get("production_type") or ""
    p = str(prod).lower()
    if "leite" in p or "dairy" in p or "milk" in p:
        return "dairy"
    return "mixed"


def _has_field(cycle: dict, field: str) -> bool:
    calc = cycle.get("calculation") or {}
    if field in calc and _num(calc.get(field)) is not None:
        return True
    records = cycle.get("normalized_data") or (cycle.get("wrapper") or {}).get("normalized_payload") or []
    for r in records:
        if not isinstance(r, dict):
            continue
        if r.get(field) is not None or str(r.get("variable", "")).lower() == field.lower():
            if r.get("value") is not None:
                return True
    return False


def evaluate_widget_visibility(
    spec: WidgetSpec,
    *,
    cycle: dict,
    indicators: dict,
    property_profile: dict | None = None,
) -> tuple[bool, str | None]:
    """Retorna (visível, motivo_oculto)."""
    mgr = resolve_managerial_status(cycle)
    if spec.official_only and not mgr.is_official:
        return False, "official_only"

    if spec.status_dependency:
        allowed = set(spec.status_dependency)
        status_map = {
            "CalculationPreliminary": {"calculation_preliminary", "pending_approval", "approved", "published", "evidence_generated", "integrity_verified"},
            "Published": {"published", "evidence_generated", "integrity_verified"},
            "PendingApproval": {"pending_approval"},
        }
        ok = False
        for dep in spec.status_dependency:
            keys = status_map.get(dep, {dep.lower()})
            if mgr.key in keys or mgr.key == dep.lower():
                ok = True
                break
        if not ok and mgr.key not in allowed:
            return False, "status"

    farm_type = _farm_type(cycle, property_profile)
    if spec.applicable_farm_types and farm_type not in spec.applicable_farm_types:
        return False, "farm_type"

    section = indicators.get(spec.section) or {}
    if spec.kpi_key and spec.kpi_key in section:
        val = section.get(spec.kpi_key)
        if val is None or val == "—" or val == "N/A":
            return False, "no_value"
        return True, None

    for field in spec.required_fields:
        if not _has_field(cycle, field):
            if spec.section == "emissions" and field == "co2e_total_kg":
                if _num((cycle.get("calculation") or {}).get("co2e_total_kg")) is None:
                    return False, f"missing:{field}"
            else:
                return False, f"missing:{field}"

    return True, None


def resolve_visible_widgets(
    screen: str,
    *,
    cycle: dict,
    indicators: dict,
    property_profile: dict | None = None,
) -> list[tuple[WidgetSpec, dict]]:
    """Lista widgets visíveis com metadados KPI prontos para render."""
    out: list[tuple[WidgetSpec, dict]] = []
    for spec in get_widget_specs_for_screen(screen):
        visible, _reason = evaluate_widget_visibility(
            spec, cycle=cycle, indicators=indicators, property_profile=property_profile,
        )
        if not visible:
            continue
        section = indicators.get(spec.section) or {}
        val = section.get(spec.kpi_key) if spec.kpi_key else None
        out.append((spec, {"title": spec.title, "value": val, "icon": spec.icon, "color": spec.color}))
    return out
