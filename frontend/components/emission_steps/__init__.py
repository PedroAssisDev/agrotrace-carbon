"""Builders de conteúdo por etapa do wizard de emissão."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.hash_viewer import HashViewer
from components.tables import DataTable
from components.upload_form import RawUploadForm
from config import LAYOUT_OPTIONS
from utils.formatting import format_co2e, format_intensity


def wrapper_step_content(cycle: dict) -> list:
    w = cycle.get("wrapper") or {}
    return [
        dbc.Select(
            id="wizard-layout-select",
            options=[{"label": k, "value": k} for k in LAYOUT_OPTIONS],
            value="monthly",
            size="sm",
            className="mb-2 form-select-narrow-sm",
        ),
        html.P(f"Layout: {w.get('layout_id', '—')} • {w.get('rows_valid', 0)} linhas válidas", className="small"),
    ]


def normalization_content(cycle: dict) -> list:
    rows = cycle.get("normalized_data") or []
    preview = rows[:5]
    scalar_cols = [k for k in (preview[0].keys() if preview else []) if not str(k).startswith("_")]
    return [DataTable(preview, columns=scalar_cols or None)]


def ontology_content(cycle: dict) -> list:
    ont = cycle.get("ontology") or {}
    return [
        html.P(f"Entidades: {ont.get('entities_created', 0)} • Relações: {ont.get('relationships_created', 0)}", className="small"),
        html.P(f"Versão: {ont.get('ontology_version', '—')}", className="small"),
    ]


def semantic_content(cycle: dict) -> list:
    v = cycle.get("semantic_validation") or {}
    return [
        html.P(
            f"Validações: {v.get('total_validations', 0)} • Críticos: {v.get('critical_errors', 0)} • Alertas: {v.get('warnings', 0)}",
            className="small",
        ),
    ]


def calculation_content(cycle: dict) -> list:
    c = cycle.get("calculation") or {}
    return [
        html.P(f"Total: {format_co2e(c.get('co2e_total_kg', 0))}", className="mb-1"),
        html.P(f"Intensidade: {format_intensity(c.get('co2e_intensity_per_milk_liter', 0))}", className="small"),
    ]


def approval_content(cycle: dict) -> list:
    approval = cycle.get("approval") or {}
    return [
        html.P(
            "A aprovação humana é feita exclusivamente em Revisão e Aprovação.",
            className="small text-muted mb-2",
        ),
        html.P(f"Decisão atual: {approval.get('decision', 'Pendente')}", className="small"),
        dbc.Button("Ir para Revisão e Aprovação", href="/approval", color="primary", outline=True, size="sm"),
    ]


def step_children(step_id: str, cycle: dict, global_filter: dict, filter_options: dict) -> list | None:
    builders = {
        "raw_data": lambda c: RawUploadForm(c, global_filter, filter_options),
        "wrapper": wrapper_step_content,
        "normalization": normalization_content,
        "ontology": ontology_content,
        "semantic": semantic_content,
        "calculation": calculation_content,
        "approval": approval_content,
        "publication": lambda c: [html.P((c.get("publication") or {}).get("ontology_version", "—"), className="small")],
        "evidence": lambda c: [
            HashViewer(c.get("hashes")),
            html.P(f"Merkle: {(c.get('evidence_package') or {}).get('merkle_root', '—')[:20]}…", className="small mt-2"),
        ],
        "blockchain": lambda c: [html.P(f"Tx: {(c.get('anchoring') or {}).get('transaction_id', '—')}", className="small")],
        "verification": lambda c: [html.P((c.get("integrity") or {}).get("final_status", "Aguardando verificação"), className="small")],
    }
    fn = builders.get(step_id)
    return fn(cycle) if fn else None
