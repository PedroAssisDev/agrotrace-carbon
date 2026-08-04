"""Seleção/cadastro de fazenda — Entrada de Dados."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.agro_tabs import AgroTabs
from components.cards import SectionHeader
from services.page_context import PageContext


def FarmSelector(ctx: PageContext, filter_options: dict | None = None) -> dbc.Card:
    """Duas abas: fazenda existente (filtro global) ou cadastro de nova fazenda."""
    farm_name = ctx.farm_name or "—"
    farm_id = ctx.farm_id or "—"
    default_tab = "farm-register" if ctx.no_farm_selected else "farm-existing"

    existing_tab = dbc.Tab([
        html.P(
            "Use o seletor de propriedade no filtro global (barra superior) para escolher "
            "uma fazenda já cadastrada. Os arquivos enviados abaixo serão associados a ela.",
            className="text-aux small mb-3",
        ),
        dbc.Row([
            dbc.Col([
                html.Small("Fazenda", className="gf-label d-block"),
                dbc.Input(value=farm_name, disabled=True, size="sm"),
            ], md=5),
            dbc.Col([
                html.Small("Identificação", className="gf-label d-block"),
                dbc.Input(value=farm_id, disabled=True, size="sm"),
            ], md=3),
            dbc.Col([
                html.Small("Período associado ao arquivo", className="gf-label d-block"),
                dbc.Input(
                    value=ctx.period_display_label or ctx.period or "—",
                    disabled=True,
                    size="sm",
                ),
            ], md=4),
        ], className="g-2"),
    ], label="Fazenda existente", tab_id="farm-existing")

    register_tab = dbc.Tab([
        html.P(
            "Preencha os dados da nova fazenda e envie o arquivo CSV na área abaixo. "
            "O cadastro e o processamento até o cálculo preliminar ocorrem automaticamente.",
            className="text-aux small mb-3",
        ),
        dbc.Row([
            dbc.Col([
                html.Small("Nome da fazenda", className="gf-label d-block"),
                dbc.Input(
                    id="de-farm-name",
                    placeholder="Ex.: Fazenda Boa Vista Leiteira",
                    value="",
                    size="sm",
                ),
            ], md=4),
            dbc.Col([
                html.Small("Código/identificação (opcional)", className="gf-label d-block"),
                dbc.Input(id="de-farm-code", placeholder="Gerado automaticamente se vazio", size="sm"),
            ], md=3),
            dbc.Col([
                html.Small("Município", className="gf-label d-block"),
                dbc.Input(id="de-farm-city", placeholder="Município", size="sm"),
            ], md=3),
            dbc.Col([
                html.Small("UF", className="gf-label d-block"),
                dbc.Input(id="de-farm-uf", placeholder="UF", maxLength=2, size="sm"),
            ], md=2),
        ], className="g-2 mb-2"),
        dbc.Row([
            dbc.Col(dbc.Select(
                id="de-farm-production",
                options=[
                    {"label": "Leite", "value": "leite"},
                    {"label": "Corte", "value": "corte"},
                    {"label": "Mista", "value": "mista"},
                    {"label": "Experimental/sensorial", "value": "experimental"},
                    {"label": "Outra", "value": "outra"},
                ],
                placeholder="Tipo de produção",
                size="sm",
            ), md=4),
        ], className="g-2"),
        html.P(
            "Depois de preencher os dados, envie o CSV na seção Importar arquivo. "
            "Quando o processamento terminar, a fazenda ficará disponível no filtro global.",
            className="text-aux small mb-0 mt-2",
        ),
    ], label="Cadastrar nova fazenda", tab_id="farm-register")

    return dbc.Card(dbc.CardBody([
        SectionHeader("Fazenda", "Escolha uma fazenda existente ou cadastre uma nova para importar dados."),
        AgroTabs([existing_tab, register_tab], id="de-farm-tabs", active_tab=default_tab),
    ]), className="agro-card mb-3")
