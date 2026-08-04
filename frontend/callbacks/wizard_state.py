"""Callbacks que espelham controles do wizard em dcc.Store."""

from __future__ import annotations

from dash import Input, Output, callback, no_update


@callback(
    Output("wizard-layout", "data"),
    Input("wizard-layout-select", "value", allow_optional=True),
    prevent_initial_call=True,
)
def sync_wizard_layout(value):
    return value if value else no_update


def register(_app) -> None:
    pass
