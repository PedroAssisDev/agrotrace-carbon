"""Documentação de schemas dos dcc.Store (referência, sem enforcement rígido).

Arquitetura de filtros: docs/modules/frontend.md (filtro global analítico vs operacional)
Modelo conceitual: docs/architecture/data-lifecycle.md
"""

from __future__ import annotations

from typing import Any, TypedDict


class GlobalFilterStore(TypedDict, total=False):
    """Estado do filtro global analítico (navbar) + campos derivados do ciclo operacional."""

    farm_id: str | None
    farm_name: str | None
    analysis_period_start: str | None
    analysis_period_end: str | None
    view_granularity: str | None  # auto | monthly | quarterly | semester | annual | consolidated
    data_mode: str | None  # official_only | include_preliminary | all
    cycle_id: str | None  # operational_cycle_id conceitual
    period: str | None
    period_display_label: str | None
    granularity: str | None
    input_granularity: str | None
    calculation_base_granularity: str | None
    aggregated_approval_status: str | None
    cycle_status: str | None
    approval_status: str | None
    publication_status: str | None
    evidence_status: str | None


class FilterOptionsStore(TypedDict, total=False):
    properties: list[dict[str, Any]]
    cycles: list[dict[str, str]]
    periods: list[str]
    analysis_periods: list[dict[str, str]]


# cycle-store: ver services/cycle_state.new_cycle() — contexto operacional
# context-cycle-id: espelho legado de global-filter-store.cycle_id
# PageContext.included_cycle_ids — derivado de analysis_cycles
