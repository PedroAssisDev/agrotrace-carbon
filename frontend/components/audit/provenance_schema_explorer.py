"""Explorador de esquema do banco de proveniência."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def ProvenanceSchemaExplorer(schema: dict) -> html.Div:
    contexts = schema.get("contexts") or {}
    tables = schema.get("tables") or []
    table_by_name = {t["name"]: t for t in tables}
    source = schema.get("source", "static")
    db_exists = schema.get("db_exists", False)

    badges = [
        dbc.Badge(f"Fonte: {source}", color="secondary", className="me-1"),
    ]
    if not db_exists:
        badges.append(dbc.Badge("DB ausente — allowlist estática", color="warning", className="me-1"))

    items: list = []
    for ctx_name in ("pipeline", "prov_core", "semantic", "calculation", "audit", "reporting", "other"):
        table_names = contexts.get(ctx_name) or []
        if not table_names:
            continue
        body_parts: list = []
        for tname in sorted(table_names):
            meta = table_by_name.get(tname, {"name": tname, "columns": [], "foreign_keys": []})
            cols = meta.get("columns") or []
            if cols:
                col_lines = [
                    html.Li(
                        f"{c['name']} ({c.get('type', 'TEXT')})"
                        + (" PK" if c.get("primary_key") else ""),
                        className="small",
                    )
                    for c in cols
                ]
            else:
                col_lines = [html.Li("Colunas indisponíveis (DB offline)", className="small text-muted")]

            fks = meta.get("foreign_keys") or []
            fk_block = None
            if fks:
                fk_block = html.Ul([
                    html.Li(
                        f"{fk['from_column']} → {fk['to_table']}.{fk['to_column']}",
                        className="small text-aux",
                    )
                    for fk in fks
                ], className="mb-0")

            body_parts.append(html.Div([
                html.Strong(tname, className="prov-schema-table-name"),
                html.Ul(col_lines, className="mb-1"),
                fk_block,
            ], className="prov-schema-table-block mb-2"))

        items.append(
            dbc.AccordionItem(body_parts, title=f"{ctx_name} ({len(table_names)})", item_id=f"schema-{ctx_name}")
        )

    accordion = dbc.Accordion(
        items,
        id="ta-prov-schema-accordion",
        start_collapsed=True,
        always_open=False,
        className="prov-schema-accordion",
    ) if items else html.P("Nenhuma tabela no escopo.", className="text-muted small")

    return html.Div([
        html.Div([
            html.H6("Explorador de esquema", className="section-subtitle d-inline me-2"),
            *badges,
        ], className="mb-2"),
        html.P(
            "Tabelas consultáveis de proveniência, pipeline, semântica, cálculo e auditoria.",
            className="text-aux small mb-2",
        ),
        accordion,
    ], className="prov-schema-explorer mb-3")
