"""Timeline gerencial simplificada do ciclo."""

from __future__ import annotations

from dash import html

from services.cycle_status_service import resolve_managerial_status


_MILESTONES = [
    ("data_imported", "Dados importados"),
    ("data_integrated", "Dados integrados"),
    ("calculation_preliminary", "Cálculo preliminar"),
    ("pending_approval", "Revisão"),
    ("approved", "Aprovado"),
    ("published", "Publicado"),
    ("evidence_generated", "Evidência técnica"),
    ("integrity_verified", "Integridade verificada"),
]

_ORDER = [m[0] for m in _MILESTONES]


def CycleStatusTimeline(cycle: dict | None) -> html.Div:
    if not cycle or not cycle.get("cycle_id"):
        return html.Div()
    current = resolve_managerial_status(cycle).key
    try:
        idx = _ORDER.index(current)
    except ValueError:
        idx = 0
    items = []
    for i, (key, label) in enumerate(_MILESTONES):
        cls = "cycle-milestone"
        if i < idx:
            cls += " cycle-milestone--done"
        elif key == current:
            cls += " cycle-milestone--active"
        items.append(html.Span(label, className=cls))
    return html.Div(items, className="cycle-status-timeline d-flex flex-wrap gap-2 mb-3")
