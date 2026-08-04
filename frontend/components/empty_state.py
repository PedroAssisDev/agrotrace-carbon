"""Estados vazios reutilizáveis."""

from __future__ import annotations

from dash import html
import dash_bootstrap_components as dbc

DEFAULT_MESSAGE = (
    "Nenhum dado encontrado para a propriedade e período selecionados. "
    "Execute um ciclo de emissão ou ajuste os filtros."
)

EMPTY_NO_FARM = {
    "title": "Nenhuma fazenda selecionada",
    "message": "Selecione uma fazenda para visualizar os dados.",
    "icon": "fas fa-tractor",
}

EMPTY_NO_FARM_CYCLES = {
    "title": "Nenhum ciclo encontrado",
    "message": "Nenhum ciclo encontrado para esta fazenda.",
    "icon": "fas fa-seedling",
}

EMPTY_NO_CYCLES = {
    "title": "Nenhum ciclo encontrado",
    "message": (
        "Não há ciclos de emissão para os filtros atuais. "
        "Cadastre uma fazenda, importe dados e execute um ciclo."
    ),
    "icon": "fas fa-seedling",
}

EMPTY_NO_PENDING_APPROVAL = {
    "title": "Nenhum cálculo pendente",
    "message": (
        "Não há cálculos aguardando revisão humana no momento. "
        "Execute um cálculo preliminar e envie para aprovação quando estiver pronto."
    ),
    "icon": "fas fa-user-check",
}

EMPTY_NO_INDICATOR_DATA = {
    "title": "Nenhum dado para este indicador",
    "message": (
        "Os indicadores oficiais dependem de um cálculo aprovado e publicado. "
        "Conclua a revisão humana para liberar os valores desta aba."
    ),
    "icon": "fas fa-chart-bar",
}

EMPTY_BLOCKCHAIN_LOCKED = {
    "title": "Evidências técnicas bloqueadas",
    "message": (
        "A geração de pacote de evidências e ancoragem só é liberada após "
        "a publicação final da ontologia aprovada."
    ),
    "icon": "fas fa-lock",
}


def EmptyState(
    title: str,
    message: str,
    *,
    icon: str = "fas fa-inbox",
    action_label: str | None = None,
    action_href: str | None = None,
) -> html.Div:
    children: list = [
        html.I(className=f"{icon} empty-state-icon"),
        html.Div(title, className="empty-state-title"),
        html.Div(message, className="empty-state-message"),
    ]
    if action_label and action_href:
        children.append(
            dbc.Button(action_label, href=action_href, size="sm", className="btn-agro-primary")
        )
    return html.Div(children, className="empty-state-card")


def EmptyFilterState(message: str | None = None, *, no_farm: bool = False, no_farm_cycles: bool = False):
    if no_farm:
        preset = EMPTY_NO_FARM
        action_label = None
        action_href = None
    elif no_farm_cycles:
        preset = EMPTY_NO_FARM_CYCLES
        action_label = None
        action_href = None
    else:
        preset = EMPTY_NO_CYCLES
        action_label = "Ir para Cálculos"
        action_href = "/calculations"
    return html.Div(
        EmptyState(
            preset["title"],
            message or preset["message"],
            icon=preset["icon"],
            action_label=action_label,
            action_href=action_href,
        ),
        className="empty-state-container",
    )
