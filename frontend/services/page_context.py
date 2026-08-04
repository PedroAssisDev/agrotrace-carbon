"""Resolução de contexto compartilhado entre páginas (filtro analítico + ciclo operacional).

``PageContext`` separa:

- ``active_cycle`` / ``operational_cycle_id`` — ciclo operacional (wizard, auditoria).
- ``analysis_cycles`` / ``filtered_analysis_cycles`` — escopo analítico multi-ciclo.

Ver docs/architecture/data-lifecycle.md e docs/modules/frontend.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from services.cycle_status_service import ManagerialStatus, resolve_managerial_status
from utils.file_helpers import get_cycle, list_cycles
from utils.global_filter import (
    cycle_period,
    cycles_for_analysis,
    cycles_for_farm,
    derive_status_fields,
    filter_cycles_by_data_mode,
    filter_cycles_by_context,
    is_empty_context,
    is_no_farm_selected,
    normalize_data_mode,
    normalize_filter_state,
    normalize_view_granularity,
    resolve_context_cycle,
)
from utils.temporal_model import TemporalModel, build_temporal_model, empty_temporal_model

logger = logging.getLogger("agrotrace.context")


def _empty_page_context_fields() -> dict:
    return {
        "operational_cycle_id": None,
        "view_granularity": "auto",
        "data_mode": "include_preliminary",
        "included_cycle_ids": [],
        "filtered_analysis_cycles": [],
        "aggregated_approval_status": None,
        "no_official_data": False,
    }


@dataclass
class PageContext:
    """Contexto unificado para renderização de páginas."""

    global_filter: dict
    active_cycle: dict
    farm_id: str | None
    farm_name: str | None
    cycle_id: str | None
    operational_cycle_id: str | None
    period: str | None
    period_display_label: str | None
    granularity: str | None
    view_granularity: str
    data_mode: str
    cycle_status: str | None
    approval_status: str | None
    publication_status: str | None
    evidence_status: str | None
    aggregated_approval_status: str | None
    managerial_status: ManagerialStatus
    all_cycles: list[dict]
    cycles: list[dict]
    analysis_cycles: list[dict]
    filtered_analysis_cycles: list[dict]
    included_cycle_ids: list[str]
    temporal: TemporalModel
    no_farm_selected: bool
    no_farm_cycles: bool
    is_empty: bool
    no_official_data: bool = False


def resolve_page_context(
    cycle: dict | None,
    global_filter: dict | None,
    context_cycle_id: str | None = None,
) -> PageContext:
    all_cycles = list_cycles()
    gf = normalize_filter_state(global_filter, all_cycles, context_cycle_id=context_cycle_id)
    no_farm = is_no_farm_selected(gf)
    farm_id = gf.get("farm_id")
    farm_name = gf.get("farm_name")
    farm_cycles = cycles_for_farm(all_cycles, farm_id) if farm_id else []
    no_farm_cycles = bool(farm_id) and not farm_cycles

    empty_status = resolve_managerial_status({})
    empty_temporal = empty_temporal_model()
    empty_extra = _empty_page_context_fields()

    if no_farm:
        return PageContext(
            global_filter=gf,
            active_cycle={},
            farm_id=None,
            farm_name=None,
            cycle_id=None,
            operational_cycle_id=None,
            period=None,
            period_display_label=None,
            granularity=None,
            view_granularity="auto",
            data_mode="include_preliminary",
            cycle_status=None,
            approval_status=None,
            publication_status=None,
            evidence_status=None,
            aggregated_approval_status=None,
            managerial_status=empty_status,
            all_cycles=all_cycles,
            cycles=[],
            analysis_cycles=[],
            filtered_analysis_cycles=[],
            included_cycle_ids=[],
            temporal=empty_temporal,
            no_farm_selected=True,
            no_farm_cycles=False,
            is_empty=True,
            no_official_data=False,
        )

    if no_farm_cycles:
        return PageContext(
            global_filter=gf,
            active_cycle={},
            farm_id=farm_id,
            farm_name=farm_name,
            cycle_id=None,
            operational_cycle_id=None,
            period=None,
            period_display_label=None,
            granularity=None,
            view_granularity=normalize_view_granularity(gf.get("view_granularity")),
            data_mode=normalize_data_mode(gf.get("data_mode")),
            cycle_status=None,
            approval_status=None,
            publication_status=None,
            evidence_status=None,
            aggregated_approval_status=None,
            managerial_status=empty_status,
            all_cycles=all_cycles,
            cycles=[],
            analysis_cycles=[],
            filtered_analysis_cycles=[],
            included_cycle_ids=[],
            temporal=empty_temporal,
            no_farm_selected=False,
            no_farm_cycles=True,
            is_empty=True,
            no_official_data=False,
        )

    cycle_id = gf.get("cycle_id")
    active = {}
    if cycle_id:
        active = get_cycle(cycle_id) or {}
    if not active.get("cycle_id"):
        filtered = filter_cycles_by_context(all_cycles, gf, None)
        active = resolve_context_cycle(None, filtered, cycle_id, farm_id=farm_id) or {}

    analysis_cycles = cycles_for_analysis(all_cycles, gf, active)
    data_mode = normalize_data_mode(gf.get("data_mode"))
    view_gr = normalize_view_granularity(gf.get("view_granularity"))
    filtered_analysis = filter_cycles_by_data_mode(analysis_cycles, data_mode)
    no_official = data_mode == "official_only" and bool(analysis_cycles) and not filtered_analysis

    temporal = (
        build_temporal_model(filtered_analysis, active, view_gr, data_mode=data_mode)
        if filtered_analysis
        else empty_temporal_model()
    )

    mgr = resolve_managerial_status(active)
    status_fields = derive_status_fields(active)
    op_cycle_id = active.get("cycle_id") or cycle_id
    included_ids = [c.get("cycle_id") for c in analysis_cycles if c.get("cycle_id")]

    is_empty = is_empty_context(filtered_analysis if data_mode == "official_only" else analysis_cycles, gf)
    logger.info(
        "[CTX] resolve farm=%s analysis=%d filtered=%d active=%s empty=%s no_official=%s ids=%s",
        farm_id,
        len(analysis_cycles),
        len(filtered_analysis),
        op_cycle_id,
        is_empty,
        no_official,
        included_ids[:8],
    )

    return PageContext(
        global_filter=gf,
        active_cycle=active,
        farm_id=farm_id,
        farm_name=farm_name or active.get("property_name"),
        cycle_id=op_cycle_id,
        operational_cycle_id=op_cycle_id,
        period=gf.get("period") or cycle_period(active),
        period_display_label=gf.get("period_display_label") or temporal.period_display_label,
        granularity=temporal.calculation_base_granularity or gf.get("granularity"),
        view_granularity=view_gr,
        data_mode=data_mode,
        cycle_status=gf.get("cycle_status") or status_fields["cycle_status"],
        approval_status=gf.get("approval_status") or status_fields["approval_status"],
        publication_status=gf.get("publication_status") or status_fields["publication_status"],
        evidence_status=gf.get("evidence_status") or status_fields["evidence_status"],
        aggregated_approval_status=temporal.aggregated_approval_status or gf.get("aggregated_approval_status"),
        managerial_status=mgr,
        all_cycles=all_cycles,
        cycles=filtered_analysis if filtered_analysis else analysis_cycles,
        analysis_cycles=analysis_cycles,
        filtered_analysis_cycles=filtered_analysis,
        included_cycle_ids=included_ids,
        temporal=temporal,
        no_farm_selected=False,
        no_farm_cycles=False,
        is_empty=is_empty,
        no_official_data=no_official,
    )
