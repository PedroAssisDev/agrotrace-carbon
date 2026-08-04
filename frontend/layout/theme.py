"""Tema e estilos do AgroTrace Carbon."""

import dash_bootstrap_components as dbc

THEME = dbc.themes.FLATLY

SIDEBAR_WIDTH = "16rem"

COLORS = {
    "primary": "#1F4D3A",
    "primary_dark": "#163D2E",
    "primary_light": "#2F6B4F",
    "primary_soft": "#DDEBE3",
    "primary_muted": "#EEF7F1",
    "primary_light_bg": "#DDEBE3",
    "secondary": "#0F766E",
    "accent": "#A3B18A",
    "accent_soft": "#F1F5E8",
    "petrol": "#123C4A",
    "petrol_muted": "#2F5061",
    "bg": "#F6F8F5",
    "bg_page": "#F6F8F5",
    "surface": "#FFFFFF",
    "surface_muted": "#EEF3EF",
    "border": "#D8E0DA",
    "border_strong": "#B7C4BB",
    "text": "#111827",
    "text_secondary": "#374151",
    "text_muted": "#6B7280",
    "text_card_title": "#374151",
    "card": "#FFFFFF",
    "warning": "#B7791F",
    "warning_light": "#FFF4D6",
    "danger": "#C62828",
    "danger_light": "#FDECEC",
    "info": "#2563EB",
    "info_light": "#EAF2FF",
    "audit": "#6D28D9",
    "audit_light": "#F3E8FF",
    "mock": "#B45309",
    "grid": "#E5E7EB",
    "zeroline": "#D1D5DB",
    "zebra": "#F8FAF8",
    "table_header": "#EEF3EF",
    "status_success": "#14532D",
    "status_success_bg": "#E6F4EA",
    "status_warning": "#78350F",
    "status_warning_bg": "#FFF4D6",
    "status_danger": "#7F1D1D",
    "status_danger_bg": "#FDECEC",
    "status_info": "#1E3A8A",
    "status_info_bg": "#EAF2FF",
    "status_neutral": "#334155",
    "status_neutral_bg": "#EEF2F6",
}

CHART_FONT = dict(
    family='Inter, "Segoe UI", Roboto, Arial, sans-serif',
    color="#111827",
    size=13,
)

EMISSION_SOURCE_COLORS = {
    "Fermentação entérica": "#1F4D3A",
    "Manejo de dejetos": "#8B6914",
    "Fertilizantes": "#A3B18A",
    "Energia": "#123C4A",
    "Total GEE — CO₂e": "#1F2933",
    "Blockchain/auditoria": "#6D28D9",
    "Erro/divergência": "#C62828",
}

CHART_PALETTE = [
    COLORS["primary"],
    COLORS["secondary"],
    COLORS["accent"],
    COLORS["petrol"],
    COLORS["warning"],
    COLORS["info"],
    COLORS["audit"],
]

TYPOGRAPHY = {
    "page_title": "1.875rem",
    "page_subtitle": "0.9375rem",
    "section_title": "1.3125rem",
    "card_title": "0.9375rem",
    "metric_value": "1.75rem",
    "body": "0.9375rem",
    "aux": "0.8125rem",
    "badge": "0.6875rem",
}

CONTENT_STYLE = {
    "minHeight": "calc(100vh - 4.25rem)",
}

NAVBAR_STYLE = {
    "backgroundColor": COLORS["card"],
    "borderBottom": f"1px solid {COLORS['border']}",
}
