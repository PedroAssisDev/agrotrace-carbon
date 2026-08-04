"""Workspace de consultas SQL de proveniência na Auditoria Técnica."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.audit.provenance_schema_explorer import ProvenanceSchemaExplorer
from services.provenance_query_templates import DEFAULT_PLACEHOLDER_SQL, template_options
from services.provenance_sql_validator import DEFAULT_MAX_ROWS


def _context_badges(ctx) -> list:
    cycle = ctx.active_cycle or {}
    badges = [
        dbc.Badge("Somente leitura", color="info", className="me-1"),
        dbc.Badge("Modo auditoria", color="secondary", className="me-1"),
        dbc.Badge(f"Limite: {DEFAULT_MAX_ROWS} linhas", color="light", text_color="dark", className="me-1"),
        dbc.Badge("provenance.db", color="light", text_color="dark", className="me-1"),
    ]
    if ctx.farm_name or ctx.farm_id:
        badges.append(dbc.Badge(f"Fazenda: {ctx.farm_name or ctx.farm_id}", color="primary", className="me-1"))
    if cycle.get("cycle_id"):
        badges.append(dbc.Badge(f"Ciclo: {cycle['cycle_id']}", color="primary", className="me-1"))
    if ctx.period_display_label or ctx.period:
        badges.append(dbc.Badge(f"Período: {ctx.period_display_label or ctx.period}", color="light", text_color="dark", className="me-1"))
    if ctx.cycle_status:
        badges.append(dbc.Badge(f"Status: {ctx.cycle_status}", color="light", text_color="dark", className="me-1"))
    return badges


def ProvenanceSqlWorkspace(ctx, schema: dict) -> html.Div:
    placeholder = DEFAULT_PLACEHOLDER_SQL
    if ctx.active_cycle.get("pipeline_run_id"):
        placeholder = placeholder.replace("{{pipeline_run_id}}", str(ctx.active_cycle["pipeline_run_id"]))

    return html.Div([
        html.Div([
            html.H5("Consultas de Proveniência", className="section-title mb-1"),
            html.P(
                "Consulta técnica somente leitura para investigar eventos, arquivos, cálculos, "
                "hashes e rastreabilidade do ciclo ativo.",
                className="text-aux small mb-2",
            ),
            html.Div(_context_badges(ctx), className="d-flex flex-wrap gap-1 mb-3"),
        ], className="prov-query-header"),

        dbc.Alert(
            "Somente consultas SELECT ou WITH são permitidas. Comandos de escrita e múltiplas instruções são bloqueados.",
            color="warning",
            className="small py-2 prov-readonly-alert",
        ),

        ProvenanceSchemaExplorer(schema),

        dbc.Card([
            dbc.CardHeader("Templates de consulta"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(
                        dcc.Dropdown(
                            id="ta-prov-template-select",
                            options=template_options(),
                            placeholder="Selecione um template…",
                            clearable=True,
                        ),
                        md=8,
                    ),
                    dbc.Col(
                        dbc.Button("Usar template", id="ta-prov-apply-template", color="outline-primary", size="sm"),
                        md=4,
                        className="d-flex align-items-center",
                    ),
                ], className="g-2 mb-2"),
                html.P(
                    "O template preenche o editor; não executa automaticamente.",
                    className="text-muted small mb-0",
                ),
            ]),
        ], className="mb-3 prov-template-card"),

        dbc.Card([
            dbc.CardHeader("Filtros auxiliares (locais)"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dbc.Input(id="ta-prov-filter-event-type", placeholder="Tipo de evento", size="sm"), md=3),
                    dbc.Col(dbc.Input(id="ta-prov-filter-entity-type", placeholder="Tipo de entidade", size="sm"), md=3),
                    dbc.Col(dbc.Input(id="ta-prov-filter-artifact", placeholder="ID artefato", size="sm"), md=3),
                    dbc.Col(dbc.Input(id="ta-prov-filter-result-set", placeholder="ID result set", size="sm"), md=3),
                ], className="g-2 mb-2"),
                dbc.Row([
                    dbc.Col(dbc.Input(id="ta-prov-filter-status", placeholder="Status", size="sm"), md=2),
                    dbc.Col(dbc.Input(id="ta-prov-filter-hash", placeholder="Hash (parcial)", size="sm"), md=3),
                    dbc.Col(dbc.Input(id="ta-prov-filter-entity-id", placeholder="ID entidade", size="sm"), md=3),
                    dbc.Col(dbc.Input(id="ta-prov-filter-date-from", type="date", size="sm"), md=2),
                    dbc.Col(dbc.Input(id="ta-prov-filter-date-to", type="date", size="sm"), md=2),
                ], className="g-2"),
                html.Div([
                    dbc.Button("Sugerir cláusulas no editor", id="ta-prov-apply-filters", color="outline-secondary", size="sm", className="mt-2 me-2"),
                ]),
            ]),
        ], className="mb-3 prov-filters-card"),

        dbc.Card([
            dbc.CardHeader("Editor SQL"),
            dbc.CardBody([
                dbc.Textarea(
                    id="ta-prov-sql-input",
                    value=placeholder,
                    rows=10,
                    className="prov-query-editor font-monospace",
                    style={"fontSize": "0.85rem"},
                ),
                html.Div([
                    dbc.Button("Executar consulta", id="ta-prov-run-query", color="primary", size="sm", className="me-2 mt-2"),
                    dbc.Button("Limpar", id="ta-prov-clear-sql", color="outline-secondary", size="sm", className="me-2 mt-2"),
                    dbc.Button("Formatar SQL", id="ta-prov-format-sql", color="outline-secondary", size="sm", className="me-2 mt-2"),
                    dcc.Clipboard(
                        id="ta-prov-copy-sql",
                        target_id="ta-prov-sql-input",
                        title="Copiar SQL",
                        style={"display": "inline-block", "marginTop": "0.5rem", "marginRight": "0.5rem"},
                    ),
                    dbc.Input(
                        id="ta-prov-limit-input",
                        type="number",
                        min=1,
                        max=DEFAULT_MAX_ROWS,
                        value=100,
                        size="sm",
                        style={"width": "100px", "display": "inline-block"},
                        className="d-inline-block mt-2 me-2",
                    ),
                    html.Span("linhas máx.", className="small text-muted mt-2 me-2"),
                ]),
            ]),
        ], className="mb-3"),

        html.Div(id="ta-prov-query-meta", className="mb-2"),

        dbc.Card([
            dbc.CardHeader([
                html.Span("Resultado", className="me-2"),
                dbc.Button("Exportar CSV", id="ta-prov-export-csv", color="outline-primary", size="sm", className="float-end"),
                dcc.Clipboard(
                    id="ta-prov-copy-result",
                    target_id="ta-prov-results-table",
                    title="Copiar resultado",
                    style={"float": "right", "marginRight": "0.5rem", "marginTop": "0.2rem"},
                ),
            ]),
            dbc.CardBody([
                html.Div(id="ta-prov-results-table"),
            ]),
        ], className="mb-3"),

        dbc.Card([
            dbc.CardHeader("Histórico de consultas"),
            dbc.CardBody(html.Div(id="ta-prov-history-list", children=html.P("Nenhuma consulta executada ainda.", className="text-muted small"))),
        ]),
    ], className="prov-sql-workspace")
