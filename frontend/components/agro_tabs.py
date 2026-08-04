"""Abas padronizadas AgroTrace."""

from __future__ import annotations

import dash_bootstrap_components as dbc


def AgroTabs(tabs: list, *, id: str | None = None, active_tab: str | None = None, **kwargs):
    """Wrapper de dbc.Tabs com classe agro-tabs."""
    extra = kwargs.pop("className", "")
    className = f"agro-tabs {extra}".strip()
    props = dict(children=tabs, className=className, **kwargs)
    if id:
        props["id"] = id
    if active_tab:
        props["active_tab"] = active_tab
    return dbc.Tabs(**props)
