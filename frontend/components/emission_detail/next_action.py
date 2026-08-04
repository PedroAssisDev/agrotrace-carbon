"""Próxima ação — fluxo para Revisão e Aprovação."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.cards import AlertBox, SectionHeader
from services.cycle_status_service import ManagerialStatus


def EmissionNextAction(st: ManagerialStatus, *, has_calculation: bool) -> html.Div:
    if not has_calculation:
        return html.Div([
            SectionHeader("Próxima ação"),
            AlertBox(
                "Execute o cálculo de emissões antes de visualizar o detalhamento completo.",
                variant="info",
            ),
        ], className="emission-detail-section mb-4")

    actions: list = []
    if st.key in ("data_integrated", "calculation_pending", "calculation_preliminary"):
        actions.append(html.P("Este resultado ainda precisa de revisão humana.", className="mb-2"))
        actions.append(dbc.Button("Enviar para Revisão e Aprovação", href="/approval", className="btn-agro-primary me-2", size="sm"))
    elif st.key == "pending_approval":
        actions.append(AlertBox("Resultado aguardando aprovação.", variant="pending", className="small"))
        actions.append(dbc.Button("Ir para Revisão e Aprovação", href="/approval", className="btn-agro-primary ms-2", size="sm"))
    elif st.key in ("approved", "published", "evidence_generated", "integrity_verified"):
        actions.append(AlertBox("Resultado aprovado. Consulte publicação e auditoria técnica.", variant="success", className="small"))
        actions.append(dbc.Button("Ver Auditoria Técnica", href="/technical-audit", color="secondary", outline=True, size="sm", className="ms-2"))
    else:
        actions.append(html.P(st.next_action or "Consulte o status do ciclo.", className="text-aux"))

    return html.Div([
        SectionHeader("Próxima ação"),
        html.Div(actions, className="d-flex flex-wrap align-items-center gap-2"),
    ], className="emission-detail-section mb-4")
