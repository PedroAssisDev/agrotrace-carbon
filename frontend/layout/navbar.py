"""Navbar superior."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from components.global_filters import GlobalFilters
from config import APP_SUBTITLE, APP_TITLE
from services.filter_service import get_available_filter_options
from utils.global_filter import DEFAULT_GLOBAL_FILTER


def create_navbar() -> dbc.Navbar:
    filter_options = get_available_filter_options()
    brand = html.Div([
        html.Span(APP_TITLE, className="navbar-brand-title d-block"),
        html.Span(APP_SUBTITLE, className="navbar-brand-subtitle d-block"),
    ])
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand(brand, className="d-flex align-items-center flex-shrink-0"),
                html.Div(
                    GlobalFilters(filter_options, DEFAULT_GLOBAL_FILTER),
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
