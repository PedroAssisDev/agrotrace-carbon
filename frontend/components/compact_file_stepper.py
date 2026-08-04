"""Stepper compacto por arquivo — Entrada de Dados."""

from __future__ import annotations

from dash import html

from services.cycle_state import is_step_done


def _step_status(cycle: dict, step_id: str) -> str:
    return (cycle.get("steps") or {}).get(step_id, {}).get("status", "PENDING")


def _phase_done(cycle: dict, phase_key: str) -> bool:
    if phase_key == "received":
        return bool(cycle.get("raw_file"))
    if phase_key == "preserved":
        return is_step_done(cycle, "raw_data")
    if phase_key == "hash":
        return bool((cycle.get("raw_file") or {}).get("sha256"))
    if phase_key == "normalized":
        return is_step_done(cycle, "wrapper") or is_step_done(cycle, "normalization")
    if phase_key == "validated":
        return is_step_done(cycle, "semantic")
    if phase_key == "calculated":
        return is_step_done(cycle, "calculation") or bool(cycle.get("calculation"))
    if phase_key == "pending":
        approval = _step_status(cycle, "approval")
        current = cycle.get("current_status", "")
        return approval in {"AWAITING_APPROVAL", "PENDING"} or current == "AWAITING_HUMAN_APPROVAL"
    return False


def _phase_error(cycle: dict, phase_key: str) -> bool:
    step_map = {
        "received": "raw_data",
        "preserved": "raw_data",
        "hash": "raw_data",
        "normalized": "wrapper",
        "validated": "semantic",
        "calculated": "calculation",
        "pending": "approval",
    }
    step_id = step_map.get(phase_key, "")
    if step_id and _step_status(cycle, step_id) == "ERROR":
        return True
    return bool(cycle.get("errors")) and phase_key in {"received", "preserved", "hash"}


COMPACT_PHASES: list[tuple[str, str]] = [
    ("received", "Recebido"),
    ("preserved", "Preservado"),
    ("hash", "Hash gerado"),
    ("normalized", "Normalizado"),
    ("validated", "Validado"),
    ("calculated", "Calculado"),
    ("pending", "Aguardando aprovação"),
]


def CompactFileStepper(cycle: dict | None, *, compact: bool = False) -> html.Div:
    """Stepper horizontal compacto refletindo o estado real do ciclo/arquivo."""
    if not cycle or not cycle.get("cycle_id"):
        return html.Div("Nenhum arquivo selecionado.", className="empty-state small")

    active_idx = len(COMPACT_PHASES)
    for i, (key, _label) in enumerate(COMPACT_PHASES):
        if not _phase_done(cycle, key):
            active_idx = i
            break

    steps: list = []
    for i, (key, label) in enumerate(COMPACT_PHASES):
        cls = "compact-step"
        if _phase_error(cycle, key):
            cls += " compact-step--error"
        elif _phase_done(cycle, key):
            cls += " compact-step--done"
        elif i == active_idx:
            cls += " compact-step--active"
        steps.append(html.Div([
            html.Span(str(i + 1), className="compact-step-circle"),
            html.Span(label, className="compact-step-label"),
        ], className=cls))

    row_cls = "compact-stepper compact-stepper--inline" if compact else "compact-stepper"
    return html.Div(steps, className=row_cls)
