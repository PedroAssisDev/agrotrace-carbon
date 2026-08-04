"""Editor de fatores de emissão na revisão por cálculo."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from services.calculation_factor_mapping_service import (
    build_factor_baseline,
    build_factor_rows_for_display,
    get_default_factor_methodology,
    get_factor_groups_for_formula,
    resolve_item_factor_methodology,
)


def _factors_table(rows: list[dict]) -> html.Div:
    if not rows:
        return html.P("Nenhum fator mapeado para este cálculo.", className="small text-muted mb-0")

    return html.Table(
        html.Tbody([
            html.Tr([
                html.Th("Grupo", className="small"),
                html.Th("Chave", className="small"),
                html.Th("Valor", className="small text-end"),
            ]),
            *[
                html.Tr([
                    html.Td(r.get("grupo") or "—", className="small"),
                    html.Td(r.get("chave") or "—", className="small text-muted"),
                    html.Td(
                        dbc.Input(
                            id={"type": "cr-factor-input", "group": r["group"], "key": r["factor_key"]},
                            type="number",
                            value=r.get("valor"),
                            step="any",
                            size="sm",
                            className="text-end font-monospace cr-factor-input",
                        ),
                        className="p-1",
                    ),
                ])
                for r in rows
            ],
        ]),
        className="table table-sm table-bordered cr-factor-table mb-0",
    )


def CalculationFactorSelector(cycle: dict, item: dict) -> html.Div:
    if not item:
        return html.Div()

    if not get_factor_groups_for_formula(item.get("formula_id") or ""):
        return html.Div()

    factor_rows = build_factor_rows_for_display(cycle, item)
    if not factor_rows:
        return html.Div()

    methodology = resolve_item_factor_methodology(item, cycle)
    default_meth = methodology.get("default") or get_default_factor_methodology(cycle)
    display_meth = methodology.get("applied") or default_meth
    has_custom = bool(methodology.get("applied"))

    return html.Div([
        html.H6("Fatores da fórmula", className="small mb-2"),
        _factors_table(factor_rows),
        html.Div([
            html.Small("Metodologia dos fatores", className="text-aux d-block mb-1"),
            dbc.Input(
                id="cr-factor-methodology",
                type="text",
                value=display_meth,
                disabled=not has_custom,
                size="sm",
                className="mb-1",
            ),
            html.Small(
                "Padrão IPCC. O campo é habilitado ao alterar algum fator.",
                className="text-muted d-block",
            ),
        ], className="mt-3"),
        dcc.Store(
            id="cr-factor-baseline-store",
            data={
                "baseline": build_factor_baseline(factor_rows),
                "default_methodology": default_meth,
                "applied_methodology": methodology.get("applied"),
            },
        ),
        dbc.Button(
            "Aplicar fatores e recalcular",
            id="cr-btn-apply-factors",
            color="outline-primary",
            size="sm",
            className="mt-2",
        ),
    ], className="cr-factor-selector")
