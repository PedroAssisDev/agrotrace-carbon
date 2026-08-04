"""Grafo de ontologia com Plotly."""

from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc

from components.charts import apply_chart_theme
from layout.theme import COLORS


def OntologyGraphViewer(nodes: list[dict] | None = None, edges: list[dict] | None = None) -> dcc.Graph:
    nodes = nodes or [
        {"id": "farm", "label": "Fazenda", "type": "Property"},
        {"id": "herd", "label": "Rebanho", "type": "Herd"},
        {"id": "milk", "label": "Produção de Leite", "type": "MilkProduction"},
        {"id": "energy", "label": "Energia", "type": "Energy"},
        {"id": "fert", "label": "Fertilizantes", "type": "Fertilizers"},
        {"id": "emissions", "label": "Fontes de Emissão", "type": "EmissionSources"},
    ]
    edges = edges or [
        {"from": "farm", "to": "herd"}, {"from": "herd", "to": "milk"},
        {"from": "farm", "to": "energy"}, {"from": "farm", "to": "fert"},
        {"from": "farm", "to": "emissions"},
    ]

    positions = {
        "farm": (0, 0),
        "herd": (-1, -1),
        "milk": (-2, -2),
        "energy": (1, -1),
        "fert": (2, -1),
        "emissions": (0, -2),
    }

    edge_x, edge_y = [], []
    for e in edges:
        x0, y0 = positions.get(e["from"], (0, 0))
        x1, y1 = positions.get(e["to"], (0, 0))
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x = [positions[n["id"]][0] for n in nodes]
    node_y = [positions[n["id"]][1] for n in nodes]
    labels = [n["label"] for n in nodes]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(color=COLORS["border"], width=1),
        hoverinfo="none", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=labels, textposition="top center",
        marker=dict(size=30, color=COLORS["primary"]),
        hovertext=[n.get("type", "") for n in nodes],
        showlegend=False,
    ))
    apply_chart_theme(fig, title="Grafo Ontológico", height=350, xaxis=dict(visible=False), yaxis=dict(visible=False))

    return dcc.Graph(figure=fig, config={"displayModeBar": False}, className="dashboard-chart")
