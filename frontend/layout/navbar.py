"""Navbar superior."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from components.global_filters import GlobalFilters
from config import APP_SUBTITLE, APP_TITLE
from utils.global_filter import DEFAULT_GLOBAL_FILTER


def create_navbar(filter_options: dict[str, Any] | None = None) -> dbc.Navbar:
    """Navbar com filtros. ``filter_options`` deve vir do layout (evita double load)."""
    options = filter_options if filter_options is not None else {}
    brand = html.Div([
        html.Span(APP_TITLE, className="navbar-brand-title d-block"),
        html.Span(APP_SUBTITLE, className="navbar-brand-subtitle d-block"),
    ])
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(brand, className="d-flex align-items-center flex-shrink-0"),
                html.Div(
                    GlobalFilters(options, DEFAULT_GLOBAL_FILTER),
                    className="navbar-global-filters ms-auto",
                ),
            ],
            fluid=True,
            className="d-flex align-items-center justify-content-between flex-wrap py-2",
        ),
        color="light",
        dark=False,
        id="app-navbar",
        className="app-navbar",
    )
