"""Configurações — somente leitura."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

import config
from components.page_header import PageHeader
from services import direct_imports as di
from services.gwp import resolve_gwp
from utils.global_filter import format_filter_badge, normalize_global_filter


def _display_gwp() -> dict:
    try:
        return resolve_gwp()
    except Exception:
        return {"error": "calculation-service indisponível"}


def _settings_card(title: str, body) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="settings-section-title"),
            body,
        ]),
        className="agro-card mb-3",
    )


def layout(
    cycle: dict,
    global_filter: dict | None = None,
    filter_options: dict | None = None,
    context_cycle_id: str | None = None,
) -> html.Div:
    gf = normalize_global_filter(global_filter)
    options = filter_options or {}
    catalog = options.get("properties") or []
    periods = options.get("periods") or []
    avail = di.availability()
    return html.Div([
        PageHeader(
            "Configurações",
            "Modos, módulos integrados e caminhos do protótipo (somente leitura).",
            gf,
            filter_options,
        ),
        _settings_card("Filtro global ativo", html.Div([
            html.P(format_filter_badge(gf, options), className="text-aux mb-1"),
            html.P(
                f"Propriedades disponíveis: {len(catalog)} • Períodos disponíveis: {len(periods)}",
                className="text-aux mb-0",
            ),
        ])),
        _settings_card(
            "Propriedades cadastradas",
            html.Ul(
                [html.Li(f"{p.get('name')} ({p.get('property_id')}) — {p.get('municipality', '')}/{p.get('state', '')}") for p in catalog]
                or [html.Li("Nenhuma propriedade no catálogo.")],
                className="mb-0",
            ),
        ),
        dbc.Row([
            dbc.Col(_settings_card("Modos de integração", html.Ul([
                html.Li(f"USE_MOCK_DATA: {config.USE_MOCK_DATA}"),
                html.Li(f"USE_DIRECT_FUNCTION_CALLS: {config.USE_DIRECT_FUNCTION_CALLS}"),
                html.Li(f"ALLOW_MOCK_FALLBACK: {config.ALLOW_MOCK_FALLBACK}"),
                html.Li(f"PRESENTATION_MODE: {config.PRESENTATION_MODE}"),
            ], className="mb-0")), md=6),
            dbc.Col(_settings_card("Módulos reais", html.Ul([
                html.Li(f"{k}: {'disponível' if v else 'indisponível (mock)'}") for k, v in avail.items()
            ], className="mb-0")), md=6),
        ], className="g-3 mb-0"),
        _settings_card("Caminhos", html.Pre(
            f"""WORKSPACE:        {config.WORKSPACE_ROOT}
Dados frontend:   {config.DATA_DIR}
Proveniência DB:  {config.PROV_DB_PATH}
Blockchain DB:    {config.BLOCKCHAIN_DB_PATH}
Ontologia export: {config.ONTOLOGY_EXPORTS_DIR}
Evidências:       {config.EVIDENCE_PACKAGES_DIR}
Logo:             {config.LOGO_PATH}
Backgrounds:      {config.AUTH_BACKGROUNDS_DIR}
""",
            className="settings-paths-pre mb-0",
        )),
        _settings_card(
            "Blockchain pós-publicação final",
            html.P(
                "O blockchain-service só é acionado após aprovação e APPROVED_RESULT_PUBLISHED "
                "(alias legado: FINAL_ONTOLOGY_PUBLISHED)."
                "Antes disso, apenas o traceability-service registra proveniência.",
                className="text-aux mb-0",
            ),
        ),
        _settings_card(
            "Versão do frontend",
            html.P(f"{config.APP_TITLE} — entry point main.py", className="text-aux mb-0"),
        ),
        _settings_card(
            "GWP padrão (IPCC AR4)",
            html.Pre(str(_display_gwp()), className="settings-paths-pre mb-0"),
        ),
    ], className="page-settings page-content-inner")
