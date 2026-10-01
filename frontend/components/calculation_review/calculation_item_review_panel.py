"""Painel de detalhe do item selecionado."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.calculation_review.calculation_approval_actions import CalculationApprovalActions
from components.calculation_review.calculation_factor_selector import CalculationFactorSelector
from components.calculation_review.zero_assumption_alert import ZeroAssumptionAlert
from components.status_badges import StatusBadge
from services.calculation_input_mapping_service import list_compatible_alternatives
from services.calculation_review_service import format_item_result_display, get_review_item
from utils.formatting import format_kg_co2e


def _result_block(item: dict) -> html.Div:
    is_total = item.get("gas") == "CO2e" or item.get("formula_id") == "total_ghg_co2e"
    co2e_kg = item.get("co2e_kg")
    if co2e_kg is None and is_total:
        co2e_kg = item.get("result_value")

    if is_total:
        return html.Div([
            html.Small("Total CO₂e", className="text-aux d-block"),
            html.Strong(format_item_result_display(item), className="cr-detail-result d-block"),
            html.Span(
                format_kg_co2e(co2e_kg) if co2e_kg is not None else "—",
                className="small text-aux",
            ),
            html.P(item.get("formula", "—"), className="small text-aux mb-0 mt-2 cr-detail-formula"),
        ], className="cr-detail-result-block p-2 mb-2")

    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Small("Resultado (massa do gás)", className="text-aux d-block"),
                html.Strong(format_item_result_display(item), className="cr-detail-result"),
            ], md=6),
            dbc.Col([
                html.Small("Equivalente CO₂e", className="text-aux d-block"),
                html.Strong(
                    format_kg_co2e(co2e_kg) if co2e_kg is not None else "—",
                    className="cr-detail-result",
                ),
            ], md=6),
        ], className="g-2 mb-1"),
        html.P(item.get("formula", "—"), className="small text-aux mb-0 cr-detail-formula"),
    ], className="cr-detail-result-block p-2 mb-2")


def _input_variables_table(input_vars: list[dict]) -> html.Div:
    if not input_vars:
        return html.P("Nenhuma variável de entrada mapeada.", className="small text-muted mb-0")

    return html.Table(
        html.Tbody([
            html.Tr([
                html.Th("Variável", className="small"),
                html.Th("Valor", className="small text-end"),
                html.Th("Unidade", className="small"),
            ]),
            *[
                html.Tr([
                    html.Td(iv.get("ontology_var") or iv.get("variable") or "—", className="small"),
                    html.Td(
                        iv.get("value") if iv.get("value") is not None else "—",
                        className="small text-end font-monospace",
                    ),
                    html.Td(iv.get("unit") or "—", className="small text-muted"),
                ])
                for iv in input_vars
            ],
        ]),
        className="table table-sm table-bordered cr-input-vars-table mb-0",
    )


def CalculationItemReviewPanel(cycle: dict, item_id: str | None) -> html.Div:
    item = get_review_item(cycle, item_id) if item_id else None
    if not item:
        return dbc.Card(dbc.CardBody([
            html.P("Selecione um cálculo na tabela à esquerda.", className="text-muted small mb-0"),
        ]), className="agro-card cr-detail-panel h-100")

    missing = item.get("missing_variables") or []
    input_vars = item.get("input_variables") or []
    has_fallback = any(iv.get("origin") == "normalized_fallback" for iv in input_vars)
    decided = item.get("review_decision")

    header = html.Div([
        html.H6(item.get("formula_name", "Detalhe"), className="card-title mb-0"),
        StatusBadge(item.get("status", "AWAITING_REVIEW")),
    ], className="d-flex justify-content-between align-items-center mb-2")

    sections: list = [header, _result_block(item)]

    if decided:
        sections.append(html.Div([
            html.Small([
                html.Strong("Decisão: "), item.get("review_decision"),
                " · ",
                html.Strong("Revisor: "), item.get("reviewed_by") or "—",
            ], className="text-aux"),
        ], className="mb-2"))

    if has_fallback:
        sections.append(dbc.Alert(
            "Algumas variáveis vieram do dado normalizado (fallback). Confirme antes de aprovar.",
            color="warning",
            className="small py-2 mb-2",
        ))

    sections.append(ZeroAssumptionAlert(item))
    # Ações no topo — antes do conteúdo longo
    sections.append(CalculationApprovalActions(item, cycle))

    inputs_body: list = [_input_variables_table(input_vars)]
    if missing:
        alts_lines = []
        for m in missing[:3]:
            ov = m.get("ontology_var") or m.get("variable", "")
            alts = list_compatible_alternatives(cycle, ov, m.get("expected_unit"))
            alt_names = ", ".join(a.get("ontology_var", a.get("variable", "")) for a in alts[:3]) or "nenhuma"
            alts_lines.append(html.Li(f"{ov} — alternativas: {alt_names}", className="small"))
        inputs_body.append(html.Div([
            html.H6([
                html.I(className="fas fa-exclamation-triangle me-1", **{"aria-hidden": "true"}),
                "Variáveis ausentes",
            ], className="small section-label mb-2 mt-2"),
            html.Ul(alts_lines, className="mb-0 ps-3"),
        ], className="cr-detail-section cr-detail-section--warning mt-2"))

    n_inputs = len(input_vars)
    sections.append(dbc.Accordion([
        dbc.AccordionItem(
            html.Div(inputs_body),
            title=f"Entradas usadas ({n_inputs})",
        ),
        dbc.AccordionItem(
            CalculationFactorSelector(cycle, item),
            title="Fatores / recálculo",
        ),
    ], start_collapsed=True, className="cr-detail-accordion mt-2"))

    return dbc.Card(
        dbc.CardBody(sections, className="cr-detail-panel-body"),
        className="agro-card cr-detail-panel h-100",
    )
