"""Workspace de consultas SQL de proveniência na Auditoria Técnica."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.audit.provenance_schema_explorer import ProvenanceSchemaExplorer
from services.provenance_query_templates import DEFAULT_PLACEHOLDER_SQL, template_options
from services.provenance_sql_validator import DEFAULT_MAX_ROWS


def _context_badges() -> list:
    return [
        dbc.Badge("Somente leitura", color="info", className="me-1"),
        dbc.Badge(f"Limite: {DEFAULT_MAX_ROWS} linhas", color="light", text_color="dark", className="me-1"),
    ]


def _filter_field(label: str, control) -> html.Div:
    return html.Div([
        html.Label(label, className="form-label small text-muted mb-1"),
        control,
    ], className="prov-filter-field")


def ProvenanceSqlWorkspace(ctx, schema: dict) -> html.Div:
    placeholder = DEFAULT_PLACEHOLDER_SQL
    if ctx.active_cycle.get("pipeline_run_id"):
        placeholder = placeholder.replace("{{pipeline_run_id}}", str(ctx.active_cycle["pipeline_run_id"]))

    workbench = dbc.Card([
        dbc.CardHeader("Consulta"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(
                    dcc.Dropdown(
                        id="ta-prov-template-select",
                        options=template_options(),
                        placeholder="Selecione um template…",
                        clearable=True,
                    ),
                    md=9,
                ),
                dbc.Col(
                    dbc.Button(
                        "Usar template",
                        id="ta-prov-apply-template",
                        color="outline-primary",
                        size="sm",
                        className="w-100",
                    ),
                    md=3,
                    className="d-flex align-items-center",
                ),
            ], className="g-2 mb-2"),
            html.P(
                "O template preenche o editor; não executa automaticamente.",
                className="text-muted small mb-3",
            ),
            dbc.Textarea(
                id="ta-prov-sql-input",
                value=placeholder,
                rows=12,
                className="prov-query-editor font-monospace",
            ),
            html.Div([
                html.Div([
                    dbc.Button(
                        "Executar consulta",
                        id="ta-prov-run-query",
                        color="primary",
                        size="sm",
                        className="me-2",
                    ),
                    html.Label("Máx. linhas", className="small text-muted me-1 mb-0"),
                    dbc.Input(
                        id="ta-prov-limit-input",
                        type="number",
                        min=1,
                        max=DEFAULT_MAX_ROWS,
                        value=100,
                        size="sm",
                        className="prov-limit-input",
                    ),
                ], className="prov-toolbar-primary d-flex align-items-center flex-wrap gap-1"),
                html.Div([
                    dbc.Button("Limpar", id="ta-prov-clear-sql", color="outline-secondary", size="sm", className="me-1"),
                    dbc.Button("Formatar SQL", id="ta-prov-format-sql", color="outline-secondary", size="sm", className="me-1"),
                    dcc.Clipboard(
                        id="ta-prov-copy-sql",
                        target_id="ta-prov-sql-input",
                        title="Copiar SQL",
                        className="prov-clipboard-btn",
                    ),
                ], className="prov-toolbar-secondary d-flex align-items-center flex-wrap gap-1"),
            ], className="prov-query-toolbar mt-3"),
        ]),
    ], className="mb-3 prov-workbench-card")

    results_card = dbc.Card([
        dbc.CardHeader([
            html.Span("Resultado", className="me-2"),
            html.Div([
                dcc.Clipboard(
                    id="ta-prov-copy-result",
                    target_id="ta-prov-results-table",
                    title="Copiar resultado",
                    className="prov-clipboard-btn me-2",
                ),
                dbc.Button("Exportar CSV", id="ta-prov-export-csv", color="outline-primary", size="sm"),
            ], className="d-inline-flex align-items-center float-end"),
        ]),
        dbc.CardBody([
            html.Div(id="ta-prov-results-table"),
        ]),
    ], className="mb-3 prov-results-card")

    history_accordion = dbc.Accordion([
        dbc.AccordionItem(
            html.Div(id="ta-prov-history-list", children=html.P(
                "Nenhuma consulta executada ainda.",
                className="text-muted small mb-0",
            )),
            title="Histórico de consultas",
            item_id="prov-history",
        ),
    ], start_collapsed=True, always_open=False, className="mb-3 prov-secondary-accordion")

    filters_body = html.Div([
        html.P(
            "Sugere cláusulas AND no editor. Use colunas compatíveis com a consulta atual.",
            className="text-muted small mb-3",
        ),
        dbc.Row([
            dbc.Col(_filter_field(
                "Tipo de evento",
                dbc.Input(id="ta-prov-filter-event-type", placeholder="ex.: FILE_INGESTED", size="sm"),
            ), md=3),
            dbc.Col(_filter_field(
                "Tipo de entidade",
                dbc.Input(id="ta-prov-filter-entity-type", placeholder="aggregate_kind", size="sm"),
            ), md=3),
            dbc.Col(_filter_field(
                "ID artefato",
                dbc.Input(id="ta-prov-filter-artifact", placeholder="source_artifact_id", size="sm"),
            ), md=3),
            dbc.Col(_filter_field(
                "ID result set",
                dbc.Input(id="ta-prov-filter-result-set", placeholder="calculation_result_set_id", size="sm"),
            ), md=3),
        ], className="g-2 mb-2"),
        dbc.Row([
            dbc.Col(_filter_field(
                "Status",
                dbc.Input(id="ta-prov-filter-status", placeholder="status", size="sm"),
            ), md=2),
            dbc.Col(_filter_field(
                "Hash (parcial)",
                dbc.Input(id="ta-prov-filter-hash", placeholder="trecho do hash", size="sm"),
            ), md=3),
            dbc.Col(_filter_field(
                "ID entidade",
                dbc.Input(id="ta-prov-filter-entity-id", placeholder="aggregate_id", size="sm"),
            ), md=3),
            dbc.Col(_filter_field(
                "De",
                dbc.Input(id="ta-prov-filter-date-from", type="date", size="sm"),
            ), md=2),
            dbc.Col(_filter_field(
                "Até",
                dbc.Input(id="ta-prov-filter-date-to", type="date", size="sm"),
            ), md=2),
        ], className="g-2 mb-3"),
        dbc.Button(
            "Sugerir cláusulas no editor",
            id="ta-prov-apply-filters",
            color="outline-secondary",
            size="sm",
        ),
    ])

    filters_accordion = dbc.Accordion([
        dbc.AccordionItem(
            filters_body,
            title="Cláusulas auxiliares",
            item_id="prov-filters",
        ),
    ], start_collapsed=True, always_open=False, className="mb-3 prov-secondary-accordion prov-filters-card")

    return html.Div([
        html.Div([
            html.H5("Consultas de Proveniência", className="section-title mb-1"),
            html.P(
                "Consulta técnica somente leitura para investigar eventos, arquivos, cálculos, "
                "hashes e rastreabilidade do ciclo ativo.",
                className="text-aux small mb-2",
            ),
            html.Div(_context_badges(), className="d-flex flex-wrap gap-1 mb-2"),
        ], className="prov-query-header"),

        dbc.Alert(
            "Somente consultas SELECT ou WITH são permitidas. Comandos de escrita e múltiplas instruções são bloqueados.",
            color="warning",
            className="small py-2 mb-3 prov-readonly-alert",
        ),

        workbench,
        html.Div(id="ta-prov-query-meta", className="mb-2"),
        results_card,
        history_accordion,
        filters_accordion,
        ProvenanceSchemaExplorer(schema),
    ], className="prov-sql-workspace")
