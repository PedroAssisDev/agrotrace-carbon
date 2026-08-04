"""Callbacks específicos da tela Entrada de Dados."""

from __future__ import annotations

from dash import Input, Output, callback

_HIDDEN = {"display": "none"}
_VISIBLE = {}


def _styles_for_tab(active_tab: str | None) -> tuple[dict, dict, dict, dict, dict]:
    """register_header, existing_header, alert, context, monitoring."""
    if active_tab == "farm-register":
        return _VISIBLE, _HIDDEN, _HIDDEN, _HIDDEN, _HIDDEN
    return _HIDDEN, _VISIBLE, _VISIBLE, _VISIBLE, _VISIBLE


@callback(
    Output("de-farm-register-header", "style"),
    Output("de-farm-existing-header", "style"),
    Output("de-farm-existing-alert", "style"),
    Output("de-farm-context-section", "style"),
    Output("de-farm-monitoring-section", "style"),
    Input("de-farm-tabs", "active_tab"),
    prevent_initial_call=True,
)
def on_farm_tab_change(active_tab: str | None):
    """Modo cadastro: só formulário + upload; modo existente: fluxo completo."""
    return _styles_for_tab(active_tab)


def register(_app) -> None:
    pass
