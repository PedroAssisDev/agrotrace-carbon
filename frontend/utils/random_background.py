"""Branding — logo da aplicação."""

from __future__ import annotations

from config import LOGO_PATH


def logo_url() -> str | None:
    """Retorna URL do logo."""
    if LOGO_PATH.exists():
        return "/ws-assets/logo/Logo.png"
    return None
