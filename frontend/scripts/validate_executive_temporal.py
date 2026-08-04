"""Validação headless da seção temporal do Painel Executivo.

Uso:
    python scripts/validate_executive_temporal.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.indicator_service import (  # noqa: E402
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_dashboard_indicators,
    build_executive_temporal_section,
    build_executive_temporal_series,
)
from services.mock_data import mock_pending_cycle  # noqa: E402
from services.page_context import resolve_page_context  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402
from utils.global_filter import DEFAULT_GLOBAL_FILTER, normalize_filter_state  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


_LEGACY_EXECUTIVE_TEMPORAL_TITLES = frozenset({
    "Produção de leite por período",
    "Produção diária (operacional)",
    "Emissões totais por período",
    "Intensidade por período",
    "Período atual vs anterior",
    "Primeiro vs último período",
    "Litros de leite por kg CO₂e",
    "kg CO₂e por litro",
})

_EXECUTIVE_TEMPORAL_TITLES = frozenset({
    "Emissões ao longo do tempo",
    "Produção ao longo do tempo",
    "Intensidade de emissão ao longo do tempo",
})


def _titles_contain(titles: set[str], needle: str) -> bool:
    return any(needle in (title or "") for title in titles)


def _figure_title(fig) -> str | None:
    if fig is None:
        return None
    layout = getattr(fig, "layout", None) or {}
    title_obj = layout.get("title") if hasattr(layout, "get") else getattr(layout, "title", None)
    if isinstance(title_obj, dict):
        return title_obj.get("text")
    if title_obj is not None:
        return getattr(title_obj, "text", None)
    return None


def _chart_titles(components: dict) -> list[str]:
    titles: list[str] = []
    for section_charts in components.values():
        for chart in section_charts or []:
            text = _figure_title(getattr(chart, "figure", None))
            if text:
                titles.append(str(text))
    return titles


_EXECUTIVE_SECTION_TITLE = "Evolução temporal dos indicadores"

_EXECUTIVE_CHART_IDS = frozenset({
    "ga-temporal-emissions-chart",
    "ga-temporal-production-chart",
    "ga-temporal-intensity-chart",
})


def _walk_graphs(component) -> list:
    """Coleta dcc.Graph da árvore de componentes."""
    graphs = []
    if type(component).__name__ == "Graph":
        return [component]
    children = getattr(component, "children", None)
    if children is None:
        return graphs
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if child is not None:
            graphs.extend(_walk_graphs(child))
    return graphs


def _walk_graph_titles(component) -> list[str]:
    titles: list[str] = []
    for graph in _walk_graphs(component):
        text = _figure_title(getattr(graph, "figure", None))
        if text:
            titles.append(str(text))
    return titles


def _walk_graph_ids(component) -> list[str]:
    ids: list[str] = []
    for graph in _walk_graphs(component):
        gid = getattr(graph, "id", None)
        if gid:
            ids.append(str(gid))
    return ids


def _pending_cycle(cid: str, period: str, milk: float, co2e: float, property_id: str, name: str) -> dict:
    cycle = mock_pending_cycle(
        cycle_id=cid,
        property_id=property_id,
        property_name=name,
        reporting_period=period,
    )
    cycle["calculation"] = {
        **(cycle.get("calculation") or {}),
        "co2e_total_kg": co2e,
        "co2e_intensity_per_milk_liter": co2e / milk if milk else 0,
    }
    cycle["wrapper"] = {
        **(cycle.get("wrapper") or {}),
        "normalized_payload": [{"milk_production": milk, "period_start": f"{period}-01" if len(period) == 7 else period}],
    }
    return cycle


def main() -> int:
    v = Validator()

    cycles = [
        _pending_cycle("C-2021", "2021", 700000, 120000, "FARM-ANNUAL-001", "Santa Clara"),
        _pending_cycle("C-2022", "2022", 720000, 125000, "FARM-ANNUAL-001", "Santa Clara"),
        _pending_cycle("C-2023", "2023", 735000, 123456, "FARM-ANNUAL-001", "Santa Clara"),
        _pending_cycle("C-2024", "2024", 740000, 128000, "FARM-ANNUAL-001", "Santa Clara"),
        _pending_cycle("C-2025", "2025", 750000, 130000, "FARM-ANNUAL-001", "Santa Clara"),
    ]
    gf = normalize_filter_state(
        {"farm_id": "FARM-ANNUAL-001", "view_granularity": "annual"},
        cycles,
    )
    ind = build_dashboard_indicators(cycles, cycles[-1], gf, [], cycles)

    ts = build_executive_temporal_series(ind)
    v.check("series: chaves emissions/production/intensity", all(k in ts for k in ("emissions", "production", "intensity")))
    v.check("series: point_count >= 2", (ts.get("point_count") or 0) >= 2, str(ts.get("point_count")))

    em = ts["emissions"]
    raw_co2e = [r.get("co2e_kg") for r in ind.get("series") or [] if r.get("co2e_kg") is not None]
    if raw_co2e and em.get("values"):
        expected_t = raw_co2e[0] / 1000
        v.check("emissions: conversao kg para t", abs(em["values"][0] - expected_t) < 0.001, f"{em['values'][0]} vs {expected_t}")
    v.check("emissions: unit t CO2e", em.get("unit") == "t CO₂e")
    v.check("production: unit L", ts["production"].get("unit") == "L")
    v.check("intensity: unit kg CO2e/L", ts["intensity"].get("unit") == "kg CO₂e/L")

    summary = ind.get("summary") or {}
    v.check("KPI: co2e_total_t presente", "co2e_total_t" in summary)
    v.check("KPI: intensity_consolidated presente", "intensity_consolidated_kg_per_l" in summary)
    v.check("KPI: period_status_label presente", "period_status_label" in summary)
    if summary.get("co2e_total_kg") and summary.get("total_milk_liters") not in (None, "—", "N/A"):
        expected_int = summary["co2e_total_kg"] / summary["total_milk_liters"]
        got = summary.get("intensity_consolidated_kg_per_l")
        v.check(
            "KPI: intensidade consolidada sum/sum",
            got not in (None, "—", "N/A") and abs(float(got) - expected_int) < 0.01,
            f"{got} vs {expected_int}",
        )

    all_labels = (em.get("labels") or []) + (ts["production"].get("labels") or [])
    v.check("labels: sem intervalo consolidado", not any(" a " in (lbl or "") for lbl in all_labels), str(all_labels[:3]))
    v.check("labels: sem Período consolidado", all(lbl != "Período consolidado" for lbl in all_labels))

    if len(em.get("labels") or []) >= 2:
        v.check("labels: ordenados (anual)", em["labels"] == sorted(em["labels"]), str(em["labels"]))

    try:
        import dash  # noqa: F401
    except ImportError:
        print("  [SKIP] testes de componentes Dash (dash nao instalado no ambiente)")
    else:
        section = build_executive_temporal_section(ind)
        v.check("section: html.Div renderizado", section is not None)
        section_html = str(section)
        v.check(
            "section: titulo Evolucao temporal dos indicadores",
            _EXECUTIVE_SECTION_TITLE in section_html,
        )
        section_titles = set(_walk_graph_titles(section))
        normalized_section_titles = {t.replace("<b>", "").replace("</b>", "") for t in section_titles}
        v.check(
            "section: 3 graficos executivos",
            _EXECUTIVE_TEMPORAL_TITLES <= normalized_section_titles,
            str(sorted(section_titles)),
        )
        section_ids = set(_walk_graph_ids(section))
        v.check(
            "section: 3 IDs de graficos",
            _EXECUTIVE_CHART_IDS <= section_ids,
            str(sorted(section_ids)),
        )

        from services.data_availability import resolve_visible_widgets
        from components.conditional_widgets import _format_kpi_value

        visible = resolve_visible_widgets("/", cycle=cycles[-1], indicators=ind)
        kpi_titles = {meta["title"] for _spec, meta in visible}
        v.check("KPIs visiveis: Emissoes totais", "Emissões totais" in kpi_titles, str(kpi_titles))
        v.check("KPIs visiveis: Producao total", "Produção total" in kpi_titles, str(kpi_titles))
        v.check("KPIs visiveis: Intensidade", "Intensidade de emissão" in kpi_titles, str(kpi_titles))
        v.check("KPIs visiveis: Status do periodo", "Status do período" in kpi_titles, str(kpi_titles))
        for _spec, meta in visible:
            if meta.get("title") == "Emissões totais":
                formatted = _format_kpi_value(meta)
                v.check("KPI emissoes formatado em t CO2e", "t CO" in formatted, formatted)
                break

        chart_data = build_dashboard_chart_series(ind, cycles)
        exec_components = build_dashboard_chart_components(chart_data, for_executive=True)
        full_components = build_dashboard_chart_components(chart_data, for_executive=False)
        exec_titles = set(_chart_titles(exec_components))
        full_titles = set(_chart_titles(full_components))

        v.check(
            "executivo: sem graficos temporais legados",
            not exec_titles & _LEGACY_EXECUTIVE_TEMPORAL_TITLES,
            str(exec_titles & _LEGACY_EXECUTIVE_TEMPORAL_TITLES),
        )
        v.check(
            "indicadores: mantem graficos legados",
            _titles_contain(full_titles, "Primeiro vs último período")
            or _titles_contain(full_titles, "Emissões totais por período"),
            str(sorted(full_titles)[:5]),
        )

    ctx = resolve_page_context(cycles[-1], gf, None)
    ind_ctx = build_dashboard_indicators(
        ctx.filtered_analysis_cycles or ctx.analysis_cycles,
        ctx.active_cycle,
        ctx.global_filter,
        [],
        ctx.all_cycles,
        temporal=ctx.temporal,
    )
    v.check("filtros: resolve_page_context + temporal intacto", "series" in ind_ctx)

    all_cycles = list_cycles()
    if all_cycles:
        annual = [c for c in all_cycles if c.get("property_id") == "FARM-ANNUAL-001"]
        if len(annual) >= 3:
            gf_seed = normalize_filter_state({"farm_id": "FARM-ANNUAL-001", "view_granularity": "auto"}, all_cycles)
            ctx_seed = resolve_page_context(annual[-1], gf_seed, None)
            ind_seed = build_dashboard_indicators(
                ctx_seed.filtered_analysis_cycles or ctx_seed.analysis_cycles,
                ctx_seed.active_cycle,
                ctx_seed.global_filter,
                [],
                ctx_seed.all_cycles,
                temporal=ctx_seed.temporal,
            )
            ts_seed = build_executive_temporal_series(ind_seed)
            em_labels = ts_seed["emissions"].get("labels") or []
            v.check("seed anual: >= 2 pontos emissões", len(em_labels) >= 2, str(len(em_labels)))
            v.check(
                "seed anual: eixo sem intervalo",
                not any(" a " in (lbl or "") for lbl in em_labels),
                str(em_labels[:5]),
            )

    print()
    if v.errors:
        print("Executive temporal validation: FAIL")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("Executive temporal validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
