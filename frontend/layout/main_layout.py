"""Layout principal da aplicação."""

from __future__ import annotations

from dash import dcc, html

import config
from components.logo_loading import create_global_loading_overlay
from layout.navbar import create_navbar
from layout.sidebar import create_sidebar
from layout.theme import CONTENT_STYLE
from services.filter_service import get_available_filter_options
from utils.global_filter import DEFAULT_GLOBAL_FILTER


def _app_root_class() -> str:
    classes = ["app-root"]
    if config.PRESENTATION_MODE:
        classes.append("presentation-mode")
    return " ".join(classes)


def create_main_layout() -> html.Div:
    filter_options = get_available_filter_options()

    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="cycle-store"),
            dcc.Store(id="global-filter-store", data=DEFAULT_GLOBAL_FILTER, storage_type="session"),
            dcc.Store(id="filter-options-store", data=filter_options),
            dcc.Store(id="context-cycle-id", data=None),
            dcc.Store(id="wizard-layout", data="monthly"),
            dcc.Store(id="upload-feedback-store", data=None),
            dcc.Store(id="cr-selected-item-store", data=None),
            dcc.Store(id="ta-active-tab-store", data="ta-summary"),
            create_sidebar(),
            html.Div(
                id="app-main",
                className="app-main",
                children=[
                    create_navbar(),
                    html.Div(
                        id="page-content",
                        className="page-content",
                        style=CONTENT_STYLE,
                    ),
                ],
            ),
            create_global_loading_overlay(),
        ],
        id="app-root",
        className=_app_root_class(),
    )
