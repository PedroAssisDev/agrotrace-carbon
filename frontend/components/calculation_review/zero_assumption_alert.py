"""Alerta de zero assumido."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html


def ZeroAssumptionAlert(item: dict) -> html.Div:
    if not item:
        return html.Div()
    zeros = item.get("zero_assumptions") or []
    unconfirmed = [z for z in zeros if not z.get("confirmed")]
    if not unconfirmed and item.get("status") != "COM_ZERO_ASSUMIDO":
        return html.Div()

    items = []
    for z in unconfirmed or zeros:
        items.append(html.Li([
            html.Strong(z.get("variable", "—")),
            f" — valor usado: {z.get('value_used', 0)} ({z.get('expected_unit', '—')})",
            html.Br(),
            html.Small(z.get("reason", ""), className="text-aux"),
        ]))

    return dbc.Alert([
        html.Strong("Zero assumido — confirmação necessária", className="d-block mb-1"),
        html.Ul(items, className="mb-0 small"),
        html.Small(
            "Aprovar com zero confirma explicitamente que a ausência de dado é aceitável.",
            className="text-aux d-block mt-2",
        ),
    ], color="warning", className="cr-zero-alert")
