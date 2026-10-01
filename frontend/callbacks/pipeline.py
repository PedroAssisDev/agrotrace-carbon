"""Callbacks de pipeline — upload, demo e verificação."""

from __future__ import annotations

import base64
import logging

from dash import ALL, Input, Output, State, callback, ctx, no_update

from config import LAYOUT_OPTIONS, SAMPLE_DATA_DIR
from services import local_orchestrator
from services.mock_data import MOCK_FARM, mock_full_cycle
from services.cycle_status_service import resolve_managerial_status
from services.farm_registry_service import FarmRegistryError, resolve_or_register_farm
from services.filter_service import refresh_filter_options
from services.pipeline_context import append_demo_warning, get_selected_farm, resolve_pipeline_property
from utils.cycle_helpers import cycle_store_summary, ensure_full_cycle, strip_private_keys
from utils.file_helpers import (
    get_cycle,
    list_cycles,
    save_cycle,
    save_raw_file,
    save_uploaded_content,
)
from utils.global_filter import default_upload_period, normalize_filter_state, normalize_global_filter
from utils.callback_logging import log_callback, log_filter_summary
from utils.pipeline_logging import timed_op

logger = logging.getLogger("agrotrace.upload")


def _layout_name_from_value(layout_value: str | None) -> str:
    if not layout_value:
        return "monthly"
    if layout_value in LAYOUT_OPTIONS:
        return layout_value
    if ":" in layout_value:
        return layout_value.split(":", 1)[0]
    return layout_value


def _build_upload_feedback(result: dict) -> dict:
    if result.get("errors"):
        msg = result["errors"][-1].get("message", "Erro no processamento do arquivo.")
        return {"message": msg, "variant": "danger"}
    st = resolve_managerial_status(result)
    if st.key == "pending_approval":
        return {
            "message": "Arquivo processado até cálculo preliminar. Aguardando aprovação.",
            "variant": "pending",
        }
    return {"message": "Arquivo recebido e processamento iniciado.", "variant": "info"}


def _resolve_effective_farm(
    global_filter: dict,
    catalog: list,
    farm_name_input: str | None,
    *,
    farm_tab: str | None = None,
) -> tuple[str | None, str | None]:
    """Na aba cadastro prioriza nome digitado; senão usa filtro global."""
    name = (farm_name_input or "").strip()
    if farm_tab == "farm-register":
        if not name:
            return None, None
        entry = resolve_or_register_farm(name)
        return entry["property_id"], entry["name"]

    farm_id = get_selected_farm(global_filter)
    if farm_id:
        resolved_id, resolved_name = resolve_pipeline_property(
            farm_id, catalog, MOCK_FARM["property_id"], MOCK_FARM["name"]
        )
        if resolved_id:
            return resolved_id, resolved_name

    if not name:
        return None, None
    entry = resolve_or_register_farm(name)
    return entry["property_id"], entry["name"]


def _sync_stores_after_upload(
    global_filter: dict | None,
    property_id: str,
    property_name: str,
    cycle_id: str | None,
) -> tuple[dict, dict]:
    """Atualiza filtro global e opções após upload, preservando janela analítica."""
    all_cycles = list_cycles()
    prev = normalize_global_filter(global_filter or {})
    raw = {
        "farm_id": property_id,
        "farm_name": property_name,
        "cycle_id": cycle_id,
        "analysis_period_start": prev.get("analysis_period_start"),
        "analysis_period_end": prev.get("analysis_period_end"),
        "view_granularity": prev.get("view_granularity"),
        "data_mode": prev.get("data_mode"),
    }
    normalized = normalize_filter_state(raw, all_cycles, context_cycle_id=cycle_id)
    options = refresh_filter_options(normalized)
    log_filter_summary("[UPLOAD] sync_stores_after_upload", normalized)
    return normalized, options


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Output("upload-feedback-store", "data", allow_duplicate=True),
    Output("global-filter-store", "data", allow_duplicate=True),
    Output("filter-options-store", "data", allow_duplicate=True),
    Input("upload-data", "contents", allow_optional=True),
    Input("upload-sample", "value", allow_optional=True),
    State("upload-data", "filename", allow_optional=True),
    State("de-farm-name", "value", allow_optional=True),
    State("de-farm-tabs", "active_tab", allow_optional=True),
    State("upload-period", "value", allow_optional=True),
    State("upload-layout", "value", allow_optional=True),
    State("upload-user", "value", allow_optional=True),
    State("cycle-store", "data"),
    State("global-filter-store", "data"),
    State("filter-options-store", "data"),
    prevent_initial_call=True,
)
@log_callback("register_raw")
def register_raw(
    contents,
    sample,
    filename,
    farm_name_input,
    farm_tab,
    period,
    layout_value,
    uploaded_by,
    cycle,
    global_filter,
    filter_options,
):
    if not contents and not sample:
        return no_update, no_update, no_update, no_update
    gf = normalize_global_filter(global_filter)
    catalog = (filter_options or {}).get("properties") or []
    if not catalog:
        catalog = refresh_filter_options(gf).get("properties") or []

    try:
        effective_id, effective_name = _resolve_effective_farm(
            gf, catalog, farm_name_input, farm_tab=farm_tab
        )
    except FarmRegistryError as exc:
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({"step": "raw_data", "message": str(exc)})
        return cycle, {"message": str(exc), "variant": "danger"}, no_update, no_update

    if effective_id is None:
        msg = "Selecione uma fazenda existente no filtro global ou informe o nome na aba Cadastrar nova fazenda."
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({"step": "raw_data", "message": msg})
        return cycle, {"message": msg, "variant": "danger"}, no_update, no_update

    farm_id = get_selected_farm(gf)
    effective_period = period or default_upload_period(gf)
    layout_name = _layout_name_from_value(layout_value)
    layout_id = layout_value or LAYOUT_OPTIONS.get(layout_name, f"{layout_name}:v1")
    frequency = gf.get("granularity") or "monthly"

    logger.info(
        "[UPLOAD] start farm=%s period=%s layout=%s filename=%s sample=%s gf_farm=%s",
        effective_id,
        effective_period,
        layout_id,
        filename,
        sample,
        gf.get("farm_id"),
    )

    try:
        with timed_op() as timer:
            if contents and filename:
                _, content_string = contents.split(",", 1)
                decoded = base64.b64decode(content_string)
                raw_meta = save_uploaded_content(
                    decoded,
                    property_id=effective_id,
                    reporting_period=effective_period,
                    original_filename=filename,
                )
            elif sample:
                src = SAMPLE_DATA_DIR / sample
                raw_meta = save_raw_file(src, property_id=effective_id, reporting_period=effective_period)
            else:
                return no_update, no_update, no_update, no_update

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
            normalized, options = _sync_stores_after_upload(
                global_filter,
                effective_id,
                effective_name,
                result.get("cycle_id"),
            )
            logger.info(
                "[UPLOAD] done cycle=%s pipeline_run_id=%s reporting_period=%s status=%s duration_ms=%.1f",
                result.get("cycle_id"),
                result.get("pipeline_run_id"),
                result.get("reporting_period"),
                result.get("current_status"),
                timer.duration_ms,
            )
        used_demo_warning = not farm_id and not (farm_name_input or "").strip()
        return (
            cycle_store_summary(append_demo_warning(result, used_demo_warning)),
            _build_upload_feedback(result),
            normalized,
            options,
        )
    except Exception as exc:
        logger.exception("Erro no upload/pipeline automática: %s", exc)
        cycle = cycle or {}
        cycle.setdefault("errors", []).append({"step": "raw_data", "message": str(exc)})
        return cycle, {"message": str(exc), "variant": "danger"}, no_update, no_update


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-verify-intact", "n_clicks", allow_optional=True),
    Input("btn-verify-tamper", "n_clicks", allow_optional=True),
    State("verify-cycle-select", "value", allow_optional=True),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def run_verify_cb(n_ok, n_bad, selected_cycle_id, cycle):
    triggered = ctx.triggered_id
    if not cycle or triggered not in {"btn-verify-intact", "btn-verify-tamper"}:
        return no_update
    tamper = triggered == "btn-verify-tamper"
    cycle = ensure_full_cycle(cycle)
    if selected_cycle_id and selected_cycle_id != cycle.get("cycle_id"):
        loaded = get_cycle(selected_cycle_id)
        if loaded:
            cycle = loaded
    from services.blockchain_view_service import is_blockchain_unlocked
    if not cycle.get("evidence_package"):
        if not is_blockchain_unlocked(cycle):
            logger.warning(
                "verify skipped cycle=%s reason=no_evidence_and_blockchain_locked",
                cycle.get("cycle_id"),
            )
            return no_update
        cycle = local_orchestrator.run_evidence_step(cycle)
        cycle = local_orchestrator.run_anchoring_step(cycle)
    result = strip_private_keys(local_orchestrator.run_verification_step(cycle, tamper=tamper))
    save_cycle(result)
    return cycle_store_summary(result)


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-run-full-pipeline", "n_clicks", allow_optional=True),
    prevent_initial_call=True,
)
def run_full_pipeline_cb(n):
    """Demo removida — use seed_test_scenarios.py / fluxo operacional."""
    return no_update


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-load-demo", "n_clicks", allow_optional=True),
    prevent_initial_call=True,
)
def load_demo_cb(n):
    """Demo mock removida do runtime."""
    return no_update


@callback(
    Output("cycle-store", "data", allow_duplicate=True),
    Input("btn-run-calculation", "n_clicks"),
    State("cycle-store", "data"),
    prevent_initial_call=True,
)
def run_calculation_cb(n, cycle):
    if not n or not cycle:
        return no_update
    cycle = ensure_full_cycle(cycle)
    try:
        return cycle_store_summary(local_orchestrator.run_calculation_step(cycle))
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
    cycle = ensure_full_cycle(cycle)
    return cycle_store_summary(mark_pending_approval(cycle))


def register(_app) -> None:
    pass
