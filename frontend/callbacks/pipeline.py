"""Callbacks de pipeline — upload, wizard, demo e verificação."""

from __future__ import annotations

import base64
import json
import logging

from dash import ALL, MATCH, Input, Output, State, callback, ctx, html, no_update

import config
from components.cards import AlertBox
from config import LAYOUT_OPTIONS, SAMPLE_DATA_DIR
from services import local_orchestrator
from services.mock_data import MOCK_FARM, mock_full_cycle
from services.pipeline_context import append_demo_warning, get_selected_farm, resolve_pipeline_property
from utils.cycle_helpers import strip_private_keys
from utils.file_helpers import get_cycle, save_cycle, save_raw_file
from utils.global_filter import default_upload_period, normalize_global_filter

logger = logging.getLogger("agrotrace.app")


def _layout_name_from_value(layout_value: str | None) -> str:
    if not layout_value:
        return "monthly"
    if layout_value in LAYOUT_OPTIONS:
        return layout_value
    if ":" in layout_value:
        return layout_value.split(":", 1)[0]
    return layout_value


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-register-raw", "n_clicks", allow_optional=True),
    Input("upload-data", "contents", allow_optional=True),
    State("upload-data", "filename", allow_optional=True),
    State("upload-sample", "value", allow_optional=True),
    State("upload-property", "value", allow_optional=True),
    State("upload-period", "value", allow_optional=True),
    State("upload-layout", "value", allow_optional=True),
    State("upload-user", "value", allow_optional=True),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("filter-options-store", "data"),
    prevent_initial_call=True,
)
def register_raw(
    n_clicks,
    contents,
    filename,
    sample,
    property_id,
    period,
    layout_value,
    uploaded_by,
    cycle,
    global_filter,
    filter_options,
):
    if not n_clicks and not contents and not sample:
        return no_update
    gf = normalize_global_filter(global_filter)
    catalog = (filter_options or {}).get("properties") or []
    farm_id = get_selected_farm(gf)
    resolved_id, resolved_name = resolve_pipeline_property(
        farm_id, catalog, MOCK_FARM["property_id"], MOCK_FARM["name"]
    )
    if resolved_id is None:
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({
            "step": "raw_data",
            "message": "Selecione uma fazenda no filtro global para registrar o arquivo.",
        })
        return cycle
    effective_id = property_id or resolved_id
    effective_name = resolved_name
    effective_period = period or default_upload_period(gf)
    layout_name = _layout_name_from_value(layout_value)
    layout_id = layout_value or LAYOUT_OPTIONS.get(layout_name, f"{layout_name}:v1")
    frequency = gf.get("granularity") or "monthly"

    try:
        if contents and filename:
            _, content_string = contents.split(",", 1)
            decoded = base64.b64decode(content_string)
            tmp = config.RAW_ORIGINALS_DIR / f"_upload_{filename}"
            tmp.write_bytes(decoded)
            raw_meta = save_raw_file(
                tmp,
                property_id=effective_id,
                reporting_period=effective_period,
                original_filename=filename,
            )
        elif sample:
            src = SAMPLE_DATA_DIR / sample
            raw_meta = save_raw_file(src, property_id=effective_id, reporting_period=effective_period)
        else:
            return no_update

        result = strip_private_keys(local_orchestrator.run_auto_pipeline_after_ingestion(
            raw_meta,
            property_id=effective_id,
            property_name=effective_name,
            reporting_period=effective_period,
            layout_name=layout_name,
            layout_id=layout_id,
            frequency=frequency,
            uploaded_by=uploaded_by or "frontend@agrotrace",
        ))
        save_cycle(result)
        return append_demo_warning(result, not farm_id)
    except Exception as exc:
        logger.exception("Erro no upload/pipeline automática: %s", exc)
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({"step": "raw_data", "message": str(exc)})
        return cycle


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input({"type": "btn-wizard-step", "step": ALL}, "n_clicks"),
    State("cycle-store", "data"),
    State("wizard-layout", "data"),
    prevent_initial_call=True,
)
def run_wizard_step(_n_clicks, cycle, layout):
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return no_update
    if not any(_n_clicks):
        return no_update

    step_id = triggered.get("step")
    if not cycle or not step_id:
        return no_update

    if step_id == "approval":
        return no_update
    kwargs: dict = {}
    if step_id in ("wrapper", "normalization"):
        kwargs["layout_name"] = layout or "monthly"
    if step_id == "verification":
        kwargs["tamper"] = False

    try:
        return strip_private_keys(local_orchestrator.run_step(cycle, step_id, **kwargs))
    except Exception as exc:
        logger.exception("Erro na etapa %s: %s", step_id, exc)
        cycle.setdefault("errors", []).append({"step": step_id, "message": str(exc)})
        return cycle


@callback(
    Output({"type": "wizard-detail", "step": MATCH}, "children"),
    Input({"type": "btn-wizard-detail", "step": MATCH}, "n_clicks"),
    State("cycle-store", "data"),
    State({"type": "btn-wizard-detail", "step": MATCH}, "id"),
    prevent_initial_call=True,
)
def show_step_detail(n, cycle, btn_id):
    if not n or not cycle or not btn_id:
        return no_update
    step_id = btn_id.get("step")
    payload_map = {
        "raw_data": cycle.get("raw_file"),
        "wrapper": cycle.get("wrapper"),
        "normalization": {"rows": len(cycle.get("normalized_data", [])), "preview": (cycle.get("normalized_data") or [])[:3]},
        "ontology": cycle.get("ontology"),
        "semantic": cycle.get("semantic_validation"),
        "calculation": cycle.get("calculation"),
        "approval": cycle.get("approval"),
        "publication": cycle.get("publication"),
        "evidence": cycle.get("evidence_package"),
        "blockchain": cycle.get("anchoring"),
        "verification": cycle.get("integrity"),
    }
    data = payload_map.get(step_id)
    if not data:
        return AlertBox("Nenhum dado para esta etapa ainda.", variant="secondary", className="small")
    return html.Pre(json.dumps(data, indent=2, ensure_ascii=False, default=str)[:4000], className="small payload-viewer")


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-verify-intact", "n_clicks", allow_optional=True),
    Input("btn-verify-tamper", "n_clicks", allow_optional=True),
    State("verify-cycle-select", "value", allow_optional=True),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def run_verify_cb(n_ok, n_bad, selected_cycle_id, cycle):
    if not cycle or (not n_ok and not n_bad):
        return no_update
    if selected_cycle_id and selected_cycle_id != cycle.get("cycle_id"):
        loaded = get_cycle(selected_cycle_id)
        if loaded:
            cycle = loaded
    if not cycle.get("evidence_package"):
        from services.blockchain_view_service import is_blockchain_unlocked
        if is_blockchain_unlocked(cycle):
            cycle = local_orchestrator.run_evidence_step(cycle)
            cycle = local_orchestrator.run_anchoring_step(cycle)
    return strip_private_keys(local_orchestrator.run_verification_step(cycle, tamper=bool(n_bad)))


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-run-full-pipeline", "n_clicks", allow_optional=True),
    State("cycle-store", "data"),
    State("upload-sample", "value", allow_optional=True),
    State("global-filter-store", "data"),
    State("filter-options-store", "data"),
    prevent_initial_call=True,
)
def run_full_pipeline_cb(n, cycle, sample, global_filter, filter_options):
    if not n:
        return no_update
    gf = normalize_global_filter(global_filter)
    catalog = (filter_options or {}).get("properties") or []
    farm_id = get_selected_farm(gf)
    property_id, property_name = resolve_pipeline_property(
        farm_id, catalog, MOCK_FARM["property_id"], MOCK_FARM["name"]
    )
    if property_id is None:
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({
            "step": "raw_data",
            "message": "Selecione uma fazenda no filtro global para executar a pipeline.",
        })
        return cycle
    sample = sample or "monthly_report.csv"
    src = SAMPLE_DATA_DIR / sample
    if not src.exists():
        src = SAMPLE_DATA_DIR / "calculate_data_mensal.csv"
    reporting_period = (cycle or {}).get("reporting_period") or default_upload_period(gf)
    raw_meta = save_raw_file(src, property_id=property_id, reporting_period=reporting_period)
    result = strip_private_keys(local_orchestrator.run_full_pipeline(
        raw_meta,
        property_id=property_id,
        property_name=property_name,
        reporting_period=reporting_period,
        layout_name="monthly",
    ))
    result["demo_mode"] = True
    save_cycle(result)
    return append_demo_warning(result, not farm_id)


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-load-demo", "n_clicks", allow_optional=True),
    State("global-filter-store", "data"),
    State("filter-options-store", "data"),
    prevent_initial_call=True,
)
def load_demo_cb(n, global_filter, filter_options):
    if not n:
        return no_update
    gf = normalize_global_filter(global_filter)
    farm_id = get_selected_farm(gf)
    catalog = (filter_options or {}).get("properties") or []
    demo = mock_full_cycle()
    if farm_id:
        demo["property_id"] = farm_id
        for p in catalog:
            if p.get("property_id") == farm_id:
                demo["property_name"] = p.get("name") or demo.get("property_name")
                break
    save_cycle(demo)
    return demo


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-integrate-data", "n_clicks"),
    State("cycle-store", "data"),
    State("wizard-layout", "data"),
    prevent_initial_call=True,
)
def integrate_data_cb(n, cycle, layout):
    """Reprocessamento manual opcional (legado)."""
    if not n or not cycle:
        return no_update
    try:
        cycle = strip_private_keys(local_orchestrator.run_wrapper_step(cycle, layout_name=layout or "monthly"))
        cycle = strip_private_keys(local_orchestrator.run_ontology_step(cycle))
        cycle = strip_private_keys(local_orchestrator.run_semantic_step(cycle))
        return cycle
    except Exception as exc:
        logger.exception("Erro na integração: %s", exc)
        cycle.setdefault("errors", []).append({"step": "integration", "message": str(exc)})
        return cycle


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-run-calculation", "n_clicks"),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def run_calculation_cb(n, cycle):
    if not n or not cycle:
        return no_update
    try:
        return strip_private_keys(local_orchestrator.run_calculation_step(cycle))
    except Exception as exc:
        logger.exception("Erro no cálculo: %s", exc)
        cycle.setdefault("errors", []).append({"step": "calculation", "message": str(exc)})
        return cycle


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-send-for-review", "n_clicks"),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def send_for_review_cb(n, cycle):
    if not n or not cycle:
        return no_update
    from services.cycle_status_service import mark_pending_approval
    return strip_private_keys(mark_pending_approval(cycle))


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-approve", "n_clicks"),
    Input("btn-reject", "n_clicks"),
    Input("btn-request-correction", "n_clicks"),
    State("approval-user", "value"),
    State("approval-justification", "value"),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def approval_decision_cb(n_ok, n_reject, n_corr, user, justification, cycle):
    if not cycle or not any((n_ok, n_reject, n_corr)):
        return no_update
    triggered = ctx.triggered_id
    decision_map = {
        "btn-approve": "APPROVED",
        "btn-reject": "REJECTED",
        "btn-request-correction": "CORRECTION_REQUESTED",
    }
    decision = decision_map.get(triggered, "APPROVED")
    approval = {
        "decision": decision,
        "approver": user or "Revisor",
        "justification": justification or "",
    }
    try:
        if decision == "APPROVED":
            result = strip_private_keys(local_orchestrator.run_auto_pipeline_after_approval(cycle, approval))
        else:
            result = strip_private_keys(local_orchestrator.run_approval_step(cycle, approval=approval))
        save_cycle(result)
        return result
    except Exception as exc:
        logger.exception("Erro na aprovação: %s", exc)
        cycle.setdefault("errors", []).append({"step": "approval", "message": str(exc)})
        return cycle


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-publish", "n_clicks"),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def publish_approved_cb(n, cycle):
    """Publicação manual — apenas wizard técnico / legado."""
    if not n or not cycle:
        return no_update
    try:
        cycle = strip_private_keys(local_orchestrator.run_publication_step(cycle))
        cycle = strip_private_keys(local_orchestrator.run_evidence_step(cycle))
        cycle = strip_private_keys(local_orchestrator.run_anchoring_step(cycle))
        cycle = strip_private_keys(local_orchestrator.run_verification_step(cycle))
        save_cycle(cycle)
        return cycle
    except Exception as exc:
        logger.exception("Erro na publicação: %s", exc)
        cycle.setdefault("errors", []).append({"step": "publication", "message": str(exc)})
        return cycle


def register(_app) -> None:
    pass
