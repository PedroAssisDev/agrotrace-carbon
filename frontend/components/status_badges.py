"""Badge de status."""

from __future__ import annotations

from dash import html

from services.cycle_state import STATUS_LABELS
from utils.constants import STATUS_VARIANTS


def _resolve_variant(status: str) -> str:
    return STATUS_VARIANTS.get(status, STATUS_VARIANTS.get(status.upper(), "pendente"))


def _resolve_label(status: str) -> str:
    if not status:
        return STATUS_LABELS.get("PENDING", "Pendente")
    return STATUS_LABELS.get(status, STATUS_LABELS.get(status.upper(), status))


def StatusBadge(status: str, *, label: str | None = None) -> html.Span:
    variant = _resolve_variant(status)
    text = label if label is not None else _resolve_label(status)
    return html.Span(text, className=f"badge-status badge-status-{variant} me-1")


def FilterBadge(text: str) -> html.Span:
    return html.Span(text, className="badge-status badge-status-dados-reais align-middle")
