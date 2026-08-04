"""Dropdowns reutilizáveis de seleção de ciclo."""

from __future__ import annotations

import dash_bootstrap_components as dbc


def CycleSelect(
    cycles: list[dict],
    active_cycle: dict,
    *,
    select_id: str = "filter-cycle-select",
    label_fn=None,
    include_all: bool = False,
    all_label: str = "Todos os ciclos",
    class_name: str = "mb-2 form-select-narrow-lg",
) -> list:
    """Retorna lista vazia ou um Select com opções de ciclo."""
    if not include_all and len(cycles) <= 1:
        return []
    if not cycles and not include_all:
        return []

    if label_fn is None:
        label_fn = lambda c: f"{c.get('cycle_id')} — {c.get('reporting_period')}"

    options = []
    if include_all:
        options.append({"label": all_label, "value": ""})
    options.extend({"label": label_fn(c), "value": c.get("cycle_id")} for c in cycles)

    default_value = active_cycle.get("cycle_id", "") if not include_all else (active_cycle.get("cycle_id") or "")
    return [
        dbc.Select(
            id=select_id,
            options=options,
            value=default_value,
            size="sm",
            className=class_name,
        ),
    ]
