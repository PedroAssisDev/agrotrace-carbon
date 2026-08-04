"""Formulário reutilizável de upload de dados brutos."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.hash_viewer import HashViewer
from config import LAYOUT_OPTIONS, SAMPLE_DATA_DIR
from utils.global_filter import default_upload_period, default_upload_property, normalize_global_filter


def RawUploadForm(cycle: dict, global_filter: dict, filter_options: dict | None = None) -> list:
    """Controles de upload bruto (IDs estáveis para callbacks em pipeline.py)."""
    raw = cycle.get("raw_file") or {}
    gf = normalize_global_filter(global_filter)
    sample_files = [f.name for f in SAMPLE_DATA_DIR.glob("*.csv")] if SAMPLE_DATA_DIR.exists() else []
    return [
        dbc.Row([
            dbc.Col(dbc.Input(id="upload-property", placeholder="Propriedade", value=default_upload_property(gf, cycle)), md=3),
            dbc.Col(dbc.Input(
                id="upload-period",
                placeholder="Período (2026-01)",
                value=default_upload_period(gf) if gf.get("period") else cycle.get("reporting_period", "2026-01"),
            ), md=2),
            dbc.Col(dbc.Select(
                id="upload-layout",
                options=[{"label": k, "value": v} for k, v in LAYOUT_OPTIONS.items()],
                value=cycle.get("layout_id") or "monthly:v1",
            ), md=2),
            dbc.Col(dbc.Input(id="upload-user", placeholder="Enviado por", value=cycle.get("uploaded_by", "")), md=2),
            dbc.Col(dbc.Select(
                id="upload-sample",
                placeholder="CSV de exemplo",
                options=[{"label": f, "value": f} for f in sample_files],
            ), md=3),
        ], className="mb-2 g-2"),
        dcc.Upload(
            id="upload-data",
            children=html.Div([
                html.I(className="fas fa-cloud-upload-alt upload-zone-icon"),
                html.Div("Arraste um CSV ou clique para selecionar", className="card-title"),
                html.Small(
                    "Após o upload, o sistema processa automaticamente até o resultado preliminar.",
                    className="text-aux",
                ),
            ], className="upload-zone"),
            multiple=False,
        ),
        dbc.Button(
            "Importar e processar automaticamente",
            id="btn-register-raw",
            color="success",
            size="sm",
            className="ms-2 btn-agro-primary",
        ),
        html.Hr(),
        HashViewer({"sha256": raw.get("sha256", "")} if raw.get("sha256") else None),
    ]
