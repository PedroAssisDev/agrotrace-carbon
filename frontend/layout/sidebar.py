"""Menu lateral — gestão de sustentabilidade + auditoria técnica."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from utils.random_background import logo_url

MANAGERIAL_NAV = [
    ("/", "fas fa-chart-line", "Painel Executivo"),
    ("/data-entry", "fas fa-file-upload", "Entrada de Dados"),
    ("/calculations", "fas fa-calculator", "Cálculos de Emissão"),
    ("/approval", "fas fa-user-check", "Revisão e Aprovação"),
    ("/indicators", "fas fa-chart-bar", "Análise Geral"),
    ("/previsoes", "fas fa-chart-area", "Previsões"),
]

TECHNICAL_NAV = [
    ("/technical-audit", "fas fa-shield-alt", "Auditoria Técnica"),
]

SETTINGS_NAV = [
    ("/settings", "fas fa-cog", "Configurações"),
]


def _nav_links(items: list[tuple[str, str, str]]) -> list:
    return [
        dbc.NavLink([html.I(className=f"{icon} me-2"), label], href=path, active="exact")
        for path, icon, label in items
    ]


def create_sidebar() -> html.Div:
    logo = logo_url()
    if logo:
        brand_block = html.Div(html.Img(src=logo, alt="AgroTrace Carbon", className="sidebar-logo"), className="sidebar-brand")
    else:
        brand_block = html.Div(html.Div("AgroTrace Carbon", className="sidebar-brand-title"), className="sidebar-brand")

    return html.Div(
        [
            brand_block,
            html.Hr(className="mx-3 my-2"),
            html.Small("Gestão", className="sidebar-group-label sidebar-group-label--managerial px-3 d-block"),
            dbc.Nav(_nav_links(MANAGERIAL_NAV), vertical=True, pills=True, className="px-2 sidebar-nav"),
            html.Hr(className="mx-3 my-2"),
            html.Small("Auditoria", className="sidebar-group-label sidebar-group-label--technical px-3 d-block"),
            dbc.Nav(_nav_links(TECHNICAL_NAV), vertical=True, pills=True, className="px-2 sidebar-nav"),
            html.Hr(className="mx-3 my-2"),
            dbc.Nav(_nav_links(SETTINGS_NAV), vertical=True, pills=True, className="px-2 sidebar-nav"),
            html.Hr(className="mx-3 my-3"),
            html.Small("Gestão de sustentabilidade agropecuária", className="sidebar-footer px-3 d-block"),
        ],
        id="app-sidebar",
        className="app-sidebar",
    )
