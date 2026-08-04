"""Histórico unificado de ciclos."""

from __future__ import annotations

from components.tables import DataTable
from services.cycle_status_service import resolve_managerial_status


def build_cycle_history_rows(cycles: list[dict]) -> list[dict]:
    rows = []
    for c in cycles:
        st = resolve_managerial_status(c)
        rows.append({
            "cycle_id": c.get("cycle_id"),
            "propriedade": c.get("property_name"),
            "periodo": c.get("reporting_period"),
            "status": st.label,
            "co2e_kg": (c.get("calculation") or {}).get("co2e_total_kg"),
        })
    return rows


def CycleHistoryTable(cycles: list[dict], *, columns: list[str] | None = None) -> DataTable:
    rows = build_cycle_history_rows(cycles)
    cols = columns or (["cycle_id", "propriedade", "periodo", "status", "co2e_kg"] if rows else [])
    return DataTable(rows, columns=cols)
