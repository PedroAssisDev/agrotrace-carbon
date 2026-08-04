"""Painel de recuperação/verificação do artefato bruto (RF002)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils.hash_helpers import truncate_hash


def _raw_options(cycle: dict) -> list[dict]:
    raw = cycle.get("raw_file") or {}
    if not raw and not cycle.get("data_entries"):
        return []

    options: list[dict] = []
    if raw:
        label = raw.get("original_filename") or "Arquivo bruto original"
        value = raw.get("artifact_id") or raw.get("sha256") or "raw_file"
        options.append({"label": label, "value": str(value)})

    for entry in cycle.get("data_entries") or []:
        if not isinstance(entry, dict):
            continue
        eid = entry.get("artifact_id") or entry.get("entry_id") or entry.get("sha256")
        if not eid:
            continue
        options.append({
            "label": entry.get("original_filename") or str(eid),
            "value": str(eid),
        })
    return options


def _meta_preview(cycle: dict) -> dict:
    raw = cycle.get("raw_file") or {}
    return {
        "original_filename": raw.get("original_filename") or "—",
        "artifact_id": raw.get("artifact_id") or "—",
        "tipo": raw.get("file_extension") or "—",
        "size": raw.get("file_size_bytes") if raw.get("file_size_bytes") is not None else "—",
        "uploaded_at": raw.get("uploaded_at") or "—",
        "cycle_id": cycle.get("cycle_id") or "—",
        "sha256": truncate_hash(raw.get("sha256") or "", 16),
        "property_id": raw.get("property_id") or cycle.get("property_id") or "—",
        "reporting_period": raw.get("reporting_period") or cycle.get("reporting_period") or "—",
    }


def RawArtifactPanel(cycle: dict) -> html.Div:
    """Seleção, metadados seguros, verificação e download do original."""
    options = _raw_options(cycle)
    if not options:
        return html.Div(
            "Nenhum artefato bruto associado a este ciclo.",
            className="empty-state mb-3",
        )

    preview = _meta_preview(cycle)
    default_value = options[0]["value"]

    return html.Div([
        html.H5("Recuperação do dado bruto", className="section-title mb-2"),
        html.P(
            "Recupera o conteúdo original preservado pelo save-file, verifica o SHA-256 "
            "e permite baixar uma cópia — sem expor caminhos de armazenamento.",
            className="text-aux small mb-3",
        ),
        dbc.Row([
            dbc.Col([
                html.Label("Artefato", className="form-label small"),
                dbc.Select(
                    id="ta-raw-artifact-select",
                    options=options,
                    value=default_value,
                    size="sm",
                ),
            ], md=6),
            dbc.Col([
                html.Label("Ações", className="form-label small d-block"),
                dbc.ButtonGroup([
                    dbc.Button(
                        "Verificar integridade",
                        id="ta-raw-verify-btn",
                        size="sm",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Baixar original",
                        id="ta-raw-download-btn",
                        size="sm",
                        color="secondary",
                        outline=True,
                        n_clicks=0,
                    ),
                ]),
            ], md=6),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col([html.Small("Nome original", className="text-muted d-block"), html.Strong(preview["original_filename"])], md=3),
            dbc.Col([html.Small("artifact_id", className="text-muted d-block"), html.Code(str(preview["artifact_id"])[:36])], md=3),
            dbc.Col([html.Small("Tipo / tamanho", className="text-muted d-block"), html.Span(f"{preview['tipo']} · {preview['size']} bytes")], md=3),
            dbc.Col([html.Small("Recebido em", className="text-muted d-block"), html.Span(preview["uploaded_at"])], md=3),
        ], className="mb-2 g-2 small"),
        dbc.Row([
            dbc.Col([html.Small("cycle_id", className="text-muted d-block"), html.Code(str(preview["cycle_id"]))], md=3),
            dbc.Col([html.Small("Propriedade / período", className="text-muted d-block"), html.Span(f"{preview['property_id']} · {preview['reporting_period']}")], md=3),
            dbc.Col([html.Small("SHA-256 registrado", className="text-muted d-block"), html.Code(preview["sha256"])], md=6),
        ], className="mb-3 g-2 small"),
        dcc.Store(id="ta-raw-verify-store"),
        html.Div(id="ta-raw-verify-result"),
    ], className="audit-raw-artifact-panel mb-4 p-3 border rounded")
