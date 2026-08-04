"""DTOs de UI para gestao dinamica de modelos na pagina Previsoes."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.cards import AlertBox, SectionHeader
from components.status_badges import FilterBadge
from services.model_training_adapter import global_retrain_warning, slot_options

_STATUS_LABEL = {
    "available": ("Disponivel", "success"),
    "missing": ("Ausente", "warning"),
    "ineligible": ("Inelegivel", "secondary"),
    "stale": ("Desatualizado", "warning"),
    "training": ("Em treinamento", "info"),
    "failed": ("Falhou", "danger"),
}


def status_badge(status: str) -> html.Span:
    label, variant = _STATUS_LABEL.get(status, (status or "—", "secondary"))
    return html.Span(label, className=f"badge-status badge-status-{variant} me-1")


def build_models_header(report: dict[str, Any] | None, property_label: str) -> html.Div:
    report = report or {}
    summary = report.get("data_summary") or {}
    models = report.get("models") or []
    counts = {}
    for item in models:
        st = item.get("status") or "unknown"
        counts[st] = counts.get(st, 0) + 1
    overall = "Disponivel"
    if counts.get("training"):
        overall = "Em treinamento"
    elif counts.get("failed") and not counts.get("available"):
        overall = "Falhou"
    elif counts.get("missing") or counts.get("stale"):
        overall = "Pendencias"
    elif counts.get("ineligible") and not counts.get("available"):
        overall = "Inelegivel"

    cards = [
        _mini_stat("Propriedade", property_label),
        _mini_stat("Ultimo periodo mensal", summary.get("property_last_monthly_period") or summary.get("last_monthly_period") or "—"),
        _mini_stat("Registros mensais (prop.)", str(summary.get("property_monthly_records", 0))),
        _mini_stat("Registros anuais (prop.)", str(summary.get("property_annual_records", 0))),
        _mini_stat("Status geral", overall),
        _mini_stat("Atualizado em", (report.get("updated_at") or "—")[:19].replace("T", " ")),
    ]
    children: list = [SectionHeader("Gestao de modelos", "Disponibilidade e treinamento sob demanda.")]
    if not report.get("source_ok", True):
        children.append(
            AlertBox(
                report.get("source_error") or "Fonte de dados de treinamento indisponivel.",
                variant="danger",
            )
        )
    children.append(dbc.Row([dbc.Col(c, md=4, className="mb-2") for c in cards], className="g-2"))
    return html.Div(children)


def build_model_cards(report: dict[str, Any] | None) -> html.Div:
    models = (report or {}).get("models") or []
    if not models:
        return AlertBox("Nenhum status de modelo disponivel.", variant="info")

    groups = {
        "Regressao mensal": [],
        "Regressao anual": [],
        "Serie temporal mensal": [],
    }
    for item in models:
        if item.get("family") == "regression" and item.get("granularity") == "monthly":
            groups["Regressao mensal"].append(item)
        elif item.get("family") == "regression" and item.get("granularity") == "annual":
            groups["Regressao anual"].append(item)
        else:
            groups["Serie temporal mensal"].append(item)

    sections = []
    for title, items in groups.items():
        cols = [dbc.Col(_model_card(item), md=6, className="mb-2") for item in items]
        sections.append(html.Div([html.H6(title, className="mt-3 mb-2"), dbc.Row(cols, className="g-2")]))
    return html.Div(sections)


def _model_card(item: dict[str, Any]) -> dbc.Card:
    target_label = (
        "Producao de leite"
        if "milk" in str(item.get("target"))
        else "Emissoes de GEE"
    )
    body = [
        html.Div(
            [status_badge(item.get("status") or ""), html.Strong(target_label)],
            className="d-flex align-items-center gap-2 mb-2",
        ),
        html.Small(
            f"Escopo: {item.get('scope')} · Granularidade: {item.get('granularity')}",
            className="text-aux d-block",
        ),
        html.Small(
            f"Elegivel: {'sim' if item.get('eligible') else 'nao'}",
            className="text-aux d-block",
        ),
        html.Small(
            f"Modelo ativo: {item.get('active_model_id') or '—'}",
            className="d-block",
        ),
        html.Small(
            f"Versao: {item.get('active_version') or '—'} · Algoritmo: {item.get('algorithm') or '—'}",
            className="d-block",
        ),
        html.Small(
            f"Metrica: {item.get('selection_metric') or '—'} = {item.get('selection_score') if item.get('selection_score') is not None else '—'}",
            className="d-block",
        ),
        html.Small(
            f"Periodo treino: {item.get('training_period_start') or '—'} → {item.get('training_period_end') or '—'}",
            className="d-block",
        ),
        html.Small(f"Registros: {item.get('record_count') if item.get('record_count') is not None else '—'}", className="d-block"),
    ]
    if item.get("reason"):
        body.append(html.Small(item["reason"], className="text-aux d-block mt-1"))
    return dbc.Card(dbc.CardBody(body), className="agro-card h-100")


def build_action_bar(report: dict[str, Any] | None) -> html.Div:
    models = (report or {}).get("models") or []
    has_missing = any(m.get("status") == "missing" and m.get("eligible") for m in models)
    has_stale = any(m.get("status") == "stale" and m.get("eligible") for m in models)
    training = any(m.get("status") == "training" for m in models)
    disabled = training or not (report or {}).get("source_ok", True)

    return html.Div(
        [
            SectionHeader("Acoes", "O frontend apenas solicita; o treinamento ocorre no model-training-service."),
            dbc.ButtonGroup(
                [
                    dbc.Button("Criar modelos ausentes", id="fc-ensure-missing", color="success", disabled=disabled or not has_missing),
                    dbc.Button("Atualizar desatualizados", id="fc-retrain-stale", color="warning", disabled=disabled or not has_stale),
                    dbc.Button("Retreinar modelos", id="fc-open-retrain-modal", color="primary", outline=True, disabled=disabled),
                    dbc.Button("Treinamento personalizado", id="fc-toggle-custom", color="secondary", outline=True, disabled=disabled),
                ],
                className="flex-wrap",
            ),
            html.Div(id="fc-training-action-feedback", className="mt-2"),
        ],
        className="mb-3",
    )


def build_custom_panel(report: dict[str, Any] | None, property_id: str) -> html.Div:
    models = {
        f"{m.get('family')}|{m.get('granularity')}|{m.get('target')}|{m.get('property_id')}": m
        for m in ((report or {}).get("models") or [])
    }
    options = []
    for opt in slot_options():
        key_pid = property_id if opt["family"] == "time_series" else None
        key = f"{opt['family']}|{opt['granularity']}|{opt['target']}|{key_pid}"
        item = models.get(key) or {}
        disabled = item.get("status") in {"ineligible", "training"}
        label = opt["label"]
        if item.get("status") == "ineligible" and item.get("reason"):
            label = f"{label} ({item['reason']})"
        options.append({"label": label, "value": opt["id"], "disabled": disabled})

    return html.Div(
        [
            SectionHeader("Treinamento personalizado", "Selecione slots elegiveis e configuracoes seguras."),
            dbc.Checklist(options=options, value=[], id="fc-slot-checklist", className="mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Perfil de candidatos", className="form-label small"),
                            dcc.Dropdown(
                                id="fc-candidate-profile",
                                options=[
                                    {"label": "Padrao (core)", "value": "core"},
                                    {"label": "Ampliado (extended)", "value": "extended"},
                                ],
                                value="core",
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Metrica", className="form-label small"),
                            dcc.Dropdown(
                                id="fc-selection-metric",
                                options=[
                                    {"label": "MAE", "value": "mae"},
                                    {"label": "RMSE", "value": "rmse"},
                                ],
                                value="mae",
                                clearable=False,
                            ),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Melhoria minima sobre baseline", className="form-label small"),
                            dbc.Input(id="fc-min-improvement", type="number", min=0, step=0.01, value=0),
                        ],
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Label("Ativar nova versao apos sucesso", className="form-label small"),
                            dbc.Checklist(
                                id="fc-activate-after",
                                options=[{"label": "Sim", "value": "yes"}],
                                value=["yes"],
                                switch=True,
                            ),
                        ],
                        md=3,
                    ),
                ],
                className="g-2 mt-2",
            ),
            dbc.Button("Executar treinamento personalizado", id="fc-run-custom", color="primary", className="mt-3"),
        ],
        id="fc-custom-panel",
        style={"display": "none"},
        className="agro-card p-3 mb-3",
    )


def build_retrain_modal() -> dbc.Modal:
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirmar retreinamento")),
            dbc.ModalBody(
                [
                    html.P(id="fc-retrain-modal-summary"),
                    AlertBox(global_retrain_warning(), variant="warning"),
                    html.Div(id="fc-retrain-modal-details"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancelar", id="fc-retrain-cancel", color="secondary", outline=True, className="me-2"),
                    dbc.Button("Confirmar retreinamento", id="fc-retrain-confirm", color="danger"),
                ]
            ),
        ],
        id="fc-retrain-modal",
        is_open=False,
        centered=True,
    )


def build_run_panel(run: dict[str, Any] | None) -> html.Div:
    if not run:
        return html.Div(id="fc-run-panel")
    return html.Div(
        [
            SectionHeader("Execucao em andamento / recente", "Acompanhe o estagio real do treinamento."),
            html.P(
                [
                    FilterBadge(str(run.get("status") or "—")),
                    html.Span(f"  Etapa: {run.get('current_stage') or '—'}", className="ms-2"),
                ]
            ),
            html.Small(f"Inicio: {(run.get('started_at') or '—')[:19].replace('T', ' ')}", className="d-block"),
            html.Small(f"Fim: {(run.get('finished_at') or '—')[:19].replace('T', ' ') if run.get('finished_at') else '—'}", className="d-block"),
            html.Small(f"Criados: {len(run.get('models_created') or [])} · Ignorados: {len(run.get('models_skipped') or [])} · Falhas: {len(run.get('models_failed') or [])}", className="d-block"),
            html.Small(run.get("error_summary") or "", className="text-aux d-block") if run.get("error_summary") else None,
            build_run_result_summary(run) if run.get("status") in {"completed", "partial", "failed"} else None,
        ],
        id="fc-run-panel",
        className="agro-card p-3 mb-3",
    )


def build_run_result_summary(run: dict[str, Any]) -> html.Div:
    created = run.get("models_created") or []
    lines = []
    for item in created:
        lines.append(
            html.Li(
                f"{item.get('model') or 'modelo'} · vencedor={item.get('winner') or '—'} · "
                f"baseline={item.get('baseline') or '—'} · ativado={'sim' if item.get('activated') else 'candidato'}"
            )
        )
    return html.Div(
        [
            html.Strong("Resumo"),
            html.Ul(lines) if lines else html.P("Nenhum modelo criado nesta execucao.", className="small mb-0"),
        ],
        className="mt-2",
    )


def build_history_table(runs: list[dict[str, Any]] | None) -> html.Div:
    runs = runs or []
    if not runs:
        return html.Div(
            [SectionHeader("Historico de treinamentos", "Ultimas execucoes desta propriedade."), html.P("Nenhuma execucao registrada.", className="text-aux small")],
            className="mb-3",
        )
    header = html.Tr([html.Th("Data"), html.Th("Modo"), html.Th("Status"), html.Th("Criados"), html.Th("Ignorados"), html.Th("Falhas")])
    rows = []
    for run in runs[:10]:
        rows.append(
            html.Tr(
                [
                    html.Td((run.get("started_at") or "—")[:19].replace("T", " ")),
                    html.Td(run.get("mode") or "—"),
                    html.Td(run.get("status") or "—"),
                    html.Td(str(len(run.get("models_created") or []))),
                    html.Td(str(len(run.get("models_skipped") or []))),
                    html.Td(str(len(run.get("models_failed") or []))),
                ]
            )
        )
    return html.Div(
        [
            SectionHeader("Historico de treinamentos", "Ultimas execucoes desta propriedade."),
            dbc.Table([html.Thead(header), html.Tbody(rows)], bordered=True, hover=True, size="sm", className="mb-0"),
        ],
        className="mb-3",
    )


def infer_cta_for_family(report: dict[str, Any] | None, family: str, granularity: str | None = None) -> html.Div:
    models = [
        m
        for m in ((report or {}).get("models") or [])
        if m.get("family") == family and (granularity is None or m.get("granularity") == granularity)
    ]
    if not models:
        return html.Div()
    if any(m.get("status") == "training" for m in models):
        return AlertBox("Ha treinamento em andamento para estes modelos. Inferencia pausada para o escopo em conflito.", variant="info")
    if all(m.get("status") == "ineligible" for m in models):
        reasons = "; ".join(m.get("reason") or "" for m in models if m.get("reason"))
        return AlertBox(f"Modelos inelegiveis. {reasons}", variant="warning")
    if any(m.get("status") == "missing" for m in models):
        return AlertBox(
            "Modelos ausentes. Use a aba Modelos → Criar modelos ausentes.",
            variant="warning",
        )
    if any(m.get("status") == "stale" for m in models):
        return AlertBox(
            "Modelos desatualizados. Voce pode prever com o modelo atual ou atualizar na aba Modelos.",
            variant="warning",
        )
    return html.Div()


def _mini_stat(title: str, value: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([html.Small(title, className="text-aux d-block"), html.Strong(value)]),
        className="agro-card",
    )
