"""Botão padronizado AgroTrace."""

from __future__ import annotations

import dash_bootstrap_components as dbc

_VARIANT_CLASS = {
    "primary": "btn-agro-primary",
    "secondary": "btn-agro-secondary",
    "danger": "btn-agro-danger",
    "approve": "btn-agro-approve",
    "reject": "btn-agro-reject",
}


def AgroButton(
    label: str,
    *,
    variant: str = "primary",
    id: str | None = None,
    href: str | None = None,
    outline: bool = False,
    size: str = "sm",
    **kwargs,
):
    """Wrapper de dbc.Button com classes do design system (texto sempre escuro)."""
    cls = _VARIANT_CLASS.get(variant, "btn-agro-primary")
    extra = kwargs.pop("className", "")
    className = f"{cls} {extra}".strip()
    props = dict(id=id, size=size, className=className, color="link", **kwargs)
    if href:
        props["href"] = href
    if outline and variant in ("danger", "reject"):
        props["className"] = f"{className} btn-agro-reject".strip()
    return dbc.Button(label, **props)
