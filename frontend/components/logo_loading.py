"""Overlay global de carregamento — card centralizado com spinner discreto."""

from __future__ import annotations

from dash import html

from config import APP_TITLE
from utils.random_background import logo_url


def create_global_loading_overlay(
    *,
    title: str = "Atualizando dados...",
    subtitle: str = "Aguarde enquanto os dados são processados.",
) -> html.Div:
    """Retorna o overlay fixo exibido enquanto callbacks Dash estão em execução."""
    logo = logo_url()
    brand_node = (
        html.Img(
            src=logo,
            alt=APP_TITLE,
            className="global-loading-brand",
        )
        if logo
        else None
    )

    card_children: list = []
    if brand_node is not None:
        card_children.append(brand_node)
    card_children.extend(
        [
            html.Div(className="global-loading-spinner"),
            html.P(title, className="global-loading-title"),
            html.P(subtitle, className="global-loading-subtitle"),
        ]
    )

    return html.Div(
        html.Div(card_children, className="global-loading-card"),
        id="global-loading-overlay",
        className="global-loading-overlay",
        **{"aria-hidden": "true", "aria-live": "polite", "role": "status"},
    )
