"""Cabeçalho de página padronizado com filtro global e status gerencial."""

from __future__ import annotations

from dash import html

from components.managerial_status import ApprovalStatusBadge, CycleStatusChip
from components.status_badges import FilterBadge
from utils.global_filter import format_filter_badge, is_no_farm_selected, normalize_global_filter
from utils.property_filter import format_page_title_for_farm


def PageHeader(
    base_title: str,
    subtitle: str | None = None,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    *,
    cycle: dict | None = None,
    show_status: bool = True,
) -> html.Div:
    gf = normalize_global_filter(global_filter)
    options = filter_options or {}
    properties = options.get("properties") or []
    farm_id = gf.get("farm_id")

    title_row: list = [
        html.H2(
            format_page_title_for_farm(base_title, farm_id, properties),
            className="page-title d-inline-block me-2 mb-0",
        ),
    ]
    if not is_no_farm_selected(gf):
        title_row.append(FilterBadge(format_filter_badge(gf, options)))

    if show_status and cycle and cycle.get("cycle_id"):
        title_row.append(ApprovalStatusBadge(cycle=cycle))

    block: list = [html.Div(title_row, className="d-flex align-items-center flex-wrap gap-2")]
    if subtitle:
        block.append(html.P(subtitle, className="page-subtitle mt-1 mb-0"))
    if show_status and cycle and cycle.get("cycle_id"):
        block.append(CycleStatusChip(cycle))
    return html.Div(block, className="page-header mb-3")
