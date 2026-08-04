"""Formulário reutilizável de upload de dados brutos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.hash_viewer import HashViewer
from config import LAYOUT_OPTIONS, SAMPLE_DATA_DIR
from utils.global_filter import default_upload_period, default_upload_property, normalize_global_filter

_LAYOUT_LABELS = {
    "intraday": "Intradiário",
    "monthly": "Produção mensal",
    "annual": "Produção anual",
}


def _layout_select_options() -> list[dict]:
    return [
        {"label": _LAYOUT_LABELS.get(key, key), "value": val}
        for key, val in LAYOUT_OPTIONS.items()
    ]


def _default_layout_id(cycle: dict, gf: dict) -> str:
    gran = gf.get("granularity") or gf.get("calculation_base_granularity") or ""
    if gran == "annual":
        return LAYOUT_OPTIONS["annual"]
    if gran == "daily":
        return LAYOUT_OPTIONS["intraday"]
    return cycle.get("layout_id") or LAYOUT_OPTIONS["monthly"]


def _hidden_callback_fields(gf: dict, cycle: dict) -> html.Div:
    """Campos ocultos para compatibilidade com callbacks (wizard / demo)."""
    sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
    return html.Div([
        dbc.Input(
            id="upload-property",
            value=default_upload_property(gf, cycle),
            style={"display": "none"},
        ),
        dbc.Input(id="upload-user", value=cycle.get("uploaded_by") or "frontend@agrotrace", style={"display": "none"}),
        dbc.Select(
            id="upload-sample",
            options=[{"label": f, "value": f} for f in sample_files],
            style={"display": "none"},
        ),
    ], style={"display": "none"})


def RawUploadForm(
    cycle: dict,
    global_filter: dict,
    filter_options: dict | None = None,
    *,
    show_hash: bool = True,
    mode: str = "full",
) -> list:
    """Controles de upload bruto (IDs estáveis para callbacks em pipeline.py)."""
    raw = cycle.get("raw_file") or {}
    gf = normalize_global_filter(global_filter)
    period_value = default_upload_period(gf) if gf.get("period") else cycle.get("reporting_period", "2026-01")
    layout_value = _default_layout_id(cycle, gf)

    upload_zone = dcc.Upload(
        id="upload-data",
        children=html.Div([
            html.I(className="fas fa-cloud-upload-alt upload-zone-icon"),
            html.Div("Arraste um CSV ou clique para selecionar", className="card-title"),
            html.Small(
                "O processamento até o resultado preliminar é automático."
                if mode == "managerial"
                else "Após o upload, o sistema processa automaticamente até o resultado preliminar.",
                className="text-aux",
            ),
        ], className="upload-zone"),
        multiple=False,
    )

    if mode == "managerial":
        items = [
            dbc.Row([
                dbc.Col([
                    html.Small("Período do arquivo", className="gf-label d-block"),
                    dbc.Input(
                        id="upload-period",
                        placeholder="Ex.: 2026-01",
                        value=period_value,
                        size="sm",
                    ),
                ], md=5),
                dbc.Col([
                    html.Small("Tipo de layout", className="gf-label d-block"),
                    dbc.Select(
                        id="upload-layout",
                        options=_layout_select_options(),
                        value=layout_value,
                        size="sm",
                    ),
                ], md=5),
            ], className="mb-3 g-2"),
            upload_zone,
            _hidden_callback_fields(gf, cycle),
        ]
    else:
        sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
        items = [
            dbc.Row([
                dbc.Col(dbc.Input(id="upload-property", placeholder="Propriedade", value=default_upload_property(gf, cycle)), md=3),
                dbc.Col(dbc.Input(
                    id="upload-period",
                    placeholder="Período (2026-01)",
                    value=period_value,
                ), md=2),
                dbc.Col(dbc.Select(
                    id="upload-layout",
                    options=[{"label": k, "value": v} for k, v in LAYOUT_OPTIONS.items()],
                    value=layout_value,
                ), md=2),
                dbc.Col(dbc.Input(id="upload-user", placeholder="Enviado por", value=cycle.get("uploaded_by", "")), md=2),
                dbc.Col(dbc.Select(
                    id="upload-sample",
                    placeholder="CSV de exemplo",
                    options=[{"label": f, "value": f} for f in sample_files],
                ), md=3),
            ], className="mb-2 g-2"),
            upload_zone,
        ]

    if show_hash:
        items.extend([
            html.Hr(),
            HashViewer({"sha256": raw.get("sha256", "")} if raw.get("sha256") else None),
        ])
    return items
