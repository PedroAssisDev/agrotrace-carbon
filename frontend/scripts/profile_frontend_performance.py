#!/usr/bin/env python3
"""Profiling headless de performance do frontend AgroTrace Carbon.

Uso:
    cd frontend
    python scripts/profile_frontend_performance.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from config import CYCLES_DIR, DB_DIR  # noqa: E402
from services import provenance_adapter  # noqa: E402
from services.dashboard_service import (  # noqa: E402
    build_dashboard_chart_components,
    build_dashboard_chart_series,
    build_dashboard_indicators,
)
from services.emission_source_breakdown_service import build_source_ranking  # noqa: E402
from services.page_context import resolve_page_context  # noqa: E402
from utils.file_helpers import get_cycle, invalidate_cycle_cache, list_cycles  # noqa: E402
from utils.global_filter import DEFAULT_GLOBAL_FILTER, normalize_filter_state  # noqa: E402

from pages import (  # noqa: E402
    approval_review,
    dashboard,
    data_entry,
    emission_calculations,
    sustainability_indicators,
    technical_audit,
)
from pages.technical_audit_sections import (  # noqa: E402
    build_provenance_section,
    build_summary_section,
    build_timeline_section,
)


def _timed(label: str, fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return result, elapsed_ms


def _cycles_size_stats() -> dict[str, float]:
    files = list(CYCLES_DIR.glob("*.json"))
    if not files:
        return {"count": 0, "total_mb": 0.0, "avg_kb": 0.0, "max_kb": 0.0}
    sizes = [f.stat().st_size for f in files]
    total = sum(sizes)
    return {
        "count": len(files),
        "total_mb": total / (1024 * 1024),
        "avg_kb": (total / len(sizes)) / 1024,
        "max_kb": max(sizes) / 1024,
    }


def _pick_sample_context(all_cycles: list[dict]) -> tuple[dict, dict, str | None]:
    gf = normalize_filter_state(DEFAULT_GLOBAL_FILTER, all_cycles)
    if not all_cycles:
        return {}, gf, None
    sample = all_cycles[0]
    farm_id = sample.get("property_id")
    if farm_id:
        gf = normalize_filter_state(
            {
                **DEFAULT_GLOBAL_FILTER,
                "farm_id": farm_id,
                "farm_name": sample.get("property_name"),
                "cycle_id": sample.get("cycle_id"),
            },
            all_cycles,
            context_cycle_id=sample.get("cycle_id"),
        )
    return sample, gf, sample.get("cycle_id")


def _count_charts(node: Any) -> int:
    if node is None:
        return 0
    try:
        from dash import dcc
        if isinstance(node, dcc.Graph):
            return 1
    except Exception:
        pass
    if hasattr(node, "children"):
        children = node.children
        if children is None:
            return 0
        if not isinstance(children, (list, tuple)):
            children = [children]
        return sum(_count_charts(c) for c in children)
    return 0


def _count_tables(node: Any) -> int:
    if node is None:
        return 0
    try:
        from dash import dash_table
        if isinstance(node, dash_table.DataTable):
            return 1
    except Exception:
        pass
    if hasattr(node, "children"):
        children = node.children
        if children is None:
            return 0
        if not isinstance(children, (list, tuple)):
            children = [children]
        return sum(_count_tables(c) for c in children)
    return 0


def main() -> int:
    timings: list[tuple[str, float]] = []
    size_stats = _cycles_size_stats()

    invalidate_cycle_cache()
    _, list_ms_cold = _timed("list_cycles_cold", list_cycles)
    timings.append(("list_cycles (cold)", list_ms_cold))

    _, list_ms_hot = _timed("list_cycles_hot", list_cycles)
    timings.append(("list_cycles (hot/cache)", list_ms_hot))

    all_cycles, _ = _timed("list_cycles_data", list_cycles)
    sample_cycle, gf, ctx_id = _pick_sample_context(all_cycles)

    if sample_cycle.get("cycle_id"):
        _, get_ms = _timed("get_cycle", lambda: get_cycle(sample_cycle["cycle_id"]))
        timings.append(("get_cycle", get_ms))

    ctx, ctx_ms = _timed(
        "resolve_page_context",
        lambda: resolve_page_context(sample_cycle, gf, ctx_id),
    )
    timings.append(("resolve_page_context", ctx_ms))

    work_cycles = ctx.filtered_analysis_cycles or ctx.analysis_cycles or all_cycles[:3]
    events = provenance_adapter.list_events_for_context(
        gf, all_cycles, ctx.active_cycle, cycles_in_context=work_cycles, context_cycle_id=ctx_id,
    )

    indicators = {}
    if work_cycles:
        indicators, ind_ms = _timed(
            "build_dashboard_indicators",
            lambda: build_dashboard_indicators(
                work_cycles, ctx.active_cycle, gf, events, all_cycles, temporal=ctx.temporal,
            ),
        )
        timings.append(("build_dashboard_indicators", ind_ms))

        _, chart_series_ms = _timed(
            "build_dashboard_chart_series",
            lambda: build_dashboard_chart_series(indicators, work_cycles),
        )
        timings.append(("build_dashboard_chart_series", chart_series_ms))
        chart_series = build_dashboard_chart_series(indicators, work_cycles)

        _, chart_comp_ms = _timed(
            "build_dashboard_chart_components",
            lambda: build_dashboard_chart_components(chart_series, for_executive=True),
        )
        timings.append(("build_dashboard_chart_components", chart_comp_ms))

        if ctx.active_cycle.get("cycle_id"):
            _, src_ms = _timed(
                "build_source_ranking",
                lambda: build_source_ranking(work_cycles),
            )
            timings.append(("build_source_ranking", src_ms))

    page_defs = [
        ("dashboard_render", lambda: dashboard.layout(sample_cycle, gf, {}, ctx_id)),
        ("indicators_render", lambda: sustainability_indicators.layout(sample_cycle, gf, {}, ctx_id)),
        ("technical_audit_render", lambda: technical_audit.layout(sample_cycle, gf, {}, ctx_id)),
        ("approval_render", lambda: approval_review.layout(sample_cycle, gf, {}, ctx_id)),
        ("data_entry_render", lambda: data_entry.layout(sample_cycle, gf, {}, ctx_id, None)),
        ("calculations_render", lambda: emission_calculations.layout(sample_cycle, gf, {}, ctx_id)),
    ]

    page_metrics: dict[str, dict[str, Any]] = {}
    for name, fn in page_defs:
        layout_node, ms = _timed(name, fn)
        timings.append((name, ms))
        page_metrics[name] = {
            "ms": ms,
            "charts": _count_charts(layout_node),
            "tables": _count_tables(layout_node),
        }

    if ctx.active_cycle.get("cycle_id"):
        for label, fn in [
            ("technical_audit_summary_section", lambda: build_summary_section(ctx)),
            ("technical_audit_timeline_section", lambda: build_timeline_section(ctx)),
            ("technical_audit_provenance_section", lambda: build_provenance_section(ctx)),
        ]:
            _, ms = _timed(label, fn)
            timings.append((label, ms))

    prov_count = len(events) if events else 0
    timings.sort(key=lambda x: x[1], reverse=True)

    print("=" * 40)
    print("AGROTRACE PERFORMANCE PROFILE")
    print("=" * 40)
    print(f"cycles_count: {int(size_stats['count'])}")
    print(f"cycles_total_size_mb: {size_stats['total_mb']:.2f}")
    print(f"cycles_avg_size_kb: {size_stats['avg_kb']:.1f}")
    print(f"cycles_max_size_kb: {size_stats['max_kb']:.1f}")
    print(f"list_cycles_ms_cold: {list_ms_cold:.1f}")
    print(f"list_cycles_ms_hot: {list_ms_hot:.1f}")
    print(f"resolve_page_context_ms: {ctx_ms:.1f}")
    print(f"dashboard_render_ms: {page_metrics.get('dashboard_render', {}).get('ms', 0):.1f}")
    print(f"indicators_render_ms: {page_metrics.get('indicators_render', {}).get('ms', 0):.1f}")
    print(f"technical_audit_render_ms: {page_metrics.get('technical_audit_render', {}).get('ms', 0):.1f}")
    print(f"approval_render_ms: {page_metrics.get('approval_render', {}).get('ms', 0):.1f}")
    print(f"data_entry_render_ms: {page_metrics.get('data_entry_render', {}).get('ms', 0):.1f}")
    print(f"calculations_render_ms: {page_metrics.get('calculations_render', {}).get('ms', 0):.1f}")
    print(f"provenance_events_count: {prov_count}")
    print(f"provenance_db_kb: {(DB_DIR / 'provenance.db').stat().st_size / 1024:.1f}" if (DB_DIR / 'provenance.db').exists() else "provenance_db_kb: 0")
    print()
    print("Top 10 funções mais lentas:")
    for i, (label, ms) in enumerate(timings[:10], 1):
        print(f"  {i}. {label}: {ms:.1f} ms")
    print()
    print("Gráficos / tabelas por tela:")
    for key, meta in page_metrics.items():
        print(f"  - {key}: charts={meta['charts']} tables={meta['tables']} ({meta['ms']:.1f} ms)")
    print()
    print("Gargalos prováveis:")
    if list_ms_cold > 100:
        print("  - GARGALO: list_cycles() lê e parseia todos os JSONs de ciclo no cold start")
    if list_ms_hot < list_ms_cold * 0.5:
        print("  - OK: cache de list_cycles reduz tempo em chamadas repetidas")
    if page_metrics.get("technical_audit_render", {}).get("ms", 0) > page_metrics.get("dashboard_render", {}).get("ms", 0):
        print("  - GARGALO: Auditoria Técnica monta múltiplas abas/seções de uma vez")
    if page_metrics.get("indicators_render", {}).get("ms", 0) > 500:
        print("  - ATENÇÃO: Análise Geral agrega indicadores + gráficos para todas as abas")
    if size_stats["total_mb"] > 10:
        print(f"  - GARGALO: volume total de ciclos JSON ({size_stats['total_mb']:.1f} MB) amplifica leituras repetidas")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
