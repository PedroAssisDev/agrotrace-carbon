"""Visualizador de pacote de evidências."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.hash_viewer import HashViewer
from components.payload_viewer import PayloadViewer


def EvidencePackageViewer(evidence: dict | None) -> html.Div:
    if not evidence:
        return html.Div("Nenhum pacote de evidência criado.", className="empty-state")

    return dbc.Tabs([
        dbc.Tab(label="Resumo", children=dbc.Card(dbc.CardBody([
            html.P([html.Strong("Evidence Package ID: "), evidence.get("evidence_package_id", "—")]),
            html.P([html.Strong("Pipeline Execution ID: "), evidence.get("pipeline_execution_id", "—")]),
            html.P([html.Strong("Calculation Execution ID: "), evidence.get("calculation_execution_id", "—")]),
            html.P([html.Strong("Período: "), evidence.get("reporting_period", "—")]),
            html.P([html.Strong("Metodologia: "), evidence.get("methodology", "—")]),
            html.P([html.Strong("Merkle Root: "), html.Span(evidence.get("merkle_root", "—"), className="hash-mono")]),
            HashViewer(evidence.get("hashes", {})),
        ]), className="mt-2 agro-card")),
        dbc.Tab(label="Payload ancorado", children=html.Div(PayloadViewer(evidence, "Payload ancorado"), className="mt-2")),
    ], className="agro-tabs")
