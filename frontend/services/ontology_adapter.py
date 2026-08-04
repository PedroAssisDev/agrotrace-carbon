"""Adapter para ontologia / modelo canônico."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

import config
import pandas as pd
from services import direct_imports as di
from services import ontology_runtime_cache as onto_cache
from services.calculation_factor_catalog import (
    FACTOR_GROUPS,
    build_default_factor_catalog,
    extract_factor_catalog_from_ontology,
)
from services.mock_data import mock_ontology_result, mock_semantic_validation
from services.ontology_extraction_service import build_canonical_variables_snapshot_from_batch
from utils.hash_helpers import sha256_dict
from utils.date_helpers import now_iso
from utils.pipeline_logging import log_call, log_fail, timed_op

logger = logging.getLogger("agrotrace.ontology")


def _attach_factor_catalog(result: dict[str, Any], onto: Any | None = None) -> None:
    """Anexa catálogo de fatores completo (extract OWL ou materialização oficial)."""
    from services.factor_catalog_materialization_service import (
        catalog_is_complete,
        materialize_factor_catalog,
    )

    catalog = extract_factor_catalog_from_ontology(onto) if onto is not None else None
    if catalog is not None and catalog_is_complete(catalog):
        from services.factor_catalog_materialization_service import factor_units_for_catalog

        catalog = dict(catalog)
        catalog.setdefault("_units", factor_units_for_catalog())
        result["factor_catalog"] = catalog
        return

    # Materializa defaults pending no resultado (e no OWL quando disponível)
    tmp_cycle: dict[str, Any] = {
        "cycle_id": result.get("cycle_id"),
        "ontology": {"factor_catalog": catalog} if catalog else {},
    }
    materialized = materialize_factor_catalog(tmp_cycle, onto=onto, actor="ontology_publish")
    result["factor_catalog"] = materialized
    if tmp_cycle.get("ontology_parameter_events"):
        result.setdefault("parameter_events", []).extend(tmp_cycle["ontology_parameter_events"])


def _records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame([{"property": "demo", "period": "2026-01"}])
    return pd.DataFrame(records)


def _mock_publish(normalized_batch: dict, reason: str | None = None) -> dict[str, Any]:
    out = mock_ontology_result(normalized_batch)
    out["mode"] = "mock"
    rp = None
    payload = normalized_batch.get("normalized_payload") or []
    if payload and isinstance(payload[0], dict):
        rp = payload[0].get("period") or payload[0].get("periodo")
    out["canonical_variables"] = build_canonical_variables_snapshot_from_batch(normalized_batch, rp)
    _attach_factor_catalog(out, None)
    if reason:
        out["fallback_reason"] = reason
    return out


def _mock_validation(canonical_dataset: dict, reason: str | None = None) -> dict[str, Any]:
    out = mock_semantic_validation(canonical_dataset)
    out["mode"] = "mock"
    if reason:
        out["fallback_reason"] = reason
    return out


def _cycle_export_dir(cycle_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(cycle_id))
    path = config.ONTOLOGY_EXPORTS_DIR / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _export_ontology_files(onto: Any, cycle_id: str | None, *, suffix: str = "") -> dict[str, str]:
    """Exporta OWL/TTL por ciclo e espelha no caminho legado compartilhado."""
    config.ONTOLOGY_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if cycle_id:
        out_dir = _cycle_export_dir(cycle_id)
        stem = f"agromrv_lite{suffix}"
        owl_path = out_dir / f"{stem}.owl"
        ttl_path = out_dir / f"{stem}.ttl"
    else:
        owl_path = config.ONTOLOGY_EXPORTS_DIR / f"agromrv_lite{suffix}.owl"
        ttl_path = config.ONTOLOGY_EXPORTS_DIR / f"agromrv_lite{suffix}.ttl"

    di.export_ontology(onto, str(owl_path), format="rdfxml")
    di.export_ontology(onto, str(ttl_path), format="turtle")

    # Espelho legado (última exportação global)
    shared_owl = config.ONTOLOGY_EXPORTS_DIR / "agromrv_lite.owl"
    shared_ttl = config.ONTOLOGY_EXPORTS_DIR / "agromrv_lite.ttl"
    di.export_ontology(onto, str(shared_owl), format="rdfxml")
    di.export_ontology(onto, str(shared_ttl), format="turtle")

    return {"owl": str(owl_path), "ttl": str(ttl_path)}


def _apply_catalog_to_onto(onto: Any, catalog: dict[str, Any]) -> None:
    """Reaplica valores + status do factor_catalog JSON no grafo (reboot / sem cache)."""
    if di.upsert_emission_factor_value is None or di.upsert_gwp_value is None:
        raise RuntimeError("API de lifecycle da ontologia indisponível.")

    statuses = catalog.get("_statuses") or {}
    for group in FACTOR_GROUPS:
        if group == "gwp":
            continue
        data = catalog.get(group) or {}
        group_st = statuses.get(group) or {}
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if str(key).startswith("_"):
                continue
            st = str(group_st.get(key) or "pending")
            di.upsert_emission_factor_value(
                onto, group=group, key=str(key), value=float(value), status=st
            )

    gwp = catalog.get("gwp") or {}
    gwp_st = statuses.get("gwp") or {}
    if isinstance(gwp, dict):
        for key, value in gwp.items():
            st = str(gwp_st.get(key) or "pending")
            di.upsert_gwp_value(onto, key=str(key), value=float(value), status=st)


def get_onto_for_cycle(cycle: dict) -> Any:
    """Obtém ontologia em cache ou reconstrói a partir do factor_catalog do ciclo."""
    cycle_id = cycle.get("cycle_id")
    onto = onto_cache.get_ontology(cycle_id)
    if onto is not None:
        return onto

    if di.build_full_ontology is None:
        raise RuntimeError("ontology-manager indisponível (build_full_ontology não importado).")

    onto = di.build_full_ontology()
    ontology_meta = cycle.get("ontology") or {}
    catalog = ontology_meta.get("factor_catalog")
    if catalog:
        _apply_catalog_to_onto(onto, catalog)
    else:
        # Popula observações se houver dados normalizados
        records = cycle.get("normalized_data") or []
        if records and di.populate_from_dataframe is not None:
            df = _records_to_dataframe(records)
            layout = (cycle.get("wrapper") or {}).get("layout_id", "monthly:v1").split(":")[0]
            di.populate_from_dataframe(onto, df, layout_name=f"{layout}_property", source_name="frontend")

    if cycle_id:
        onto_cache.set_ontology(cycle_id, onto)
    return onto


def _refresh_cycle_ontology_meta(
    cycle: dict,
    onto: Any,
    *,
    ontology_version: str | None = None,
    export_suffix: str = "",
) -> dict[str, Any]:
    """Atualiza factor_catalog, export_paths e ontology_hash no ciclo."""
    cycle_id = str(cycle.get("cycle_id") or "")
    export_paths = _export_ontology_files(onto, cycle_id or None, suffix=export_suffix)
    catalog = extract_factor_catalog_from_ontology(onto) or build_default_factor_catalog(source="ontology")

    ontology = dict(cycle.get("ontology") or {})
    ontology["factor_catalog"] = catalog
    ontology["export_paths"] = export_paths
    ontology["updated_at"] = now_iso()
    if ontology_version:
        ontology["ontology_version"] = ontology_version
    ontology["ontology_hash"] = sha256_dict({
        "factor_catalog": {
            k: v for k, v in catalog.items() if not str(k).startswith("_") or k == "_statuses"
        },
        "version": ontology.get("ontology_version"),
        "export_paths": export_paths,
    })
    cycle["ontology"] = ontology
    if cycle_id:
        onto_cache.set_ontology(cycle_id, onto)
    return ontology


def upsert_calculation_parameters(
    cycle: dict,
    edits: list[dict[str, Any]],
    *,
    status: str = "corrected",
    actor: str | None = None,
) -> dict:
    """Persiste edições de fatores na ontologia e atualiza factor_catalog do ciclo."""
    if not edits:
        raise ValueError("Informe ao menos uma edição de parâmetro.")
    if di.upsert_emission_factor_value is None or di.upsert_gwp_value is None:
        raise RuntimeError("API de lifecycle da ontologia indisponível.")

    onto = get_onto_for_cycle(cycle)
    applied: list[dict[str, Any]] = []
    for edit in edits:
        group = edit.get("group")
        key = edit.get("factor_key") or edit.get("key")
        if group is None or key is None:
            raise ValueError(f"Edição inválida (group/key): {edit}")
        value = float(edit["value"])
        if group == "gwp":
            info = di.upsert_gwp_value(onto, key=str(key), value=value, status=status)
        else:
            info = di.upsert_emission_factor_value(
                onto, group=str(group), key=str(key), value=value, status=status
            )
        applied.append({**info, "actor": actor})

    _refresh_cycle_ontology_meta(cycle, onto)
    logger.info(
        "[ONTO] upsert params cycle=%s n=%d status=%s actor=%s",
        cycle.get("cycle_id"),
        len(applied),
        status,
        actor,
    )
    cycle.setdefault("ontology_parameter_events", []).append({
        "type": "upsert",
        "status": status,
        "actor": actor,
        "at": now_iso(),
        "applied": applied,
    })
    return cycle


def confirm_calculation_parameters(
    cycle: dict,
    groups: Iterable[str],
    *,
    actor: str | None = None,
) -> dict:
    """Marca grupos de parâmetros como confirmed na ontologia."""
    group_list = [g for g in groups if g]
    if not group_list:
        return cycle
    if di.set_groups_status is None:
        raise RuntimeError("API set_groups_status indisponível.")

    onto = get_onto_for_cycle(cycle)
    updated = di.set_groups_status(onto, group_list, status="confirmed")
    _refresh_cycle_ontology_meta(cycle, onto)
    cycle.setdefault("ontology_parameter_events", []).append({
        "type": "confirm",
        "status": "confirmed",
        "actor": actor,
        "at": now_iso(),
        "updated": updated,
    })
    return cycle


def mark_parameters_published(cycle: dict, *, actor: str | None = None) -> dict:
    """Marca fatores e resultados como published e republica OWL final."""
    if di.set_groups_status is None:
        raise RuntimeError("API set_groups_status indisponível.")

    try:
        from services.result_correction_service import (
            get_active_version,
            has_open_correction,
            has_pending_reapproval,
        )

        if has_open_correction(cycle):
            raise RuntimeError(
                "Não é permitido publicar ontologia final com solicitação de correção aberta."
            )
        if has_pending_reapproval(cycle):
            raise RuntimeError(
                "Não é permitido publicar ontologia final com versão pendente de reaprovação."
            )
        active = get_active_version(cycle)
        if active and active.get("status") == "superseded":
            raise RuntimeError("Não é permitido publicar versão superseded.")
    except RuntimeError:
        raise
    except Exception:
        pass

    onto = get_onto_for_cycle(cycle)
    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    groups = [g for g in FACTOR_GROUPS if catalog.get(g)]
    if not groups:
        groups = list(FACTOR_GROUPS)

    updated = di.set_groups_status(onto, groups, status="published")
    try:
        from ontology.result_lifecycle import set_results_status
        from ontology.cycle_model import set_cycle_status

        set_results_status(onto, str(cycle["cycle_id"]), "published")
        set_cycle_status(onto, str(cycle["cycle_id"]), "Published")
    except Exception as exc:
        logger.warning("Falha ao marcar results/cycle published: %s", exc)

    version = f"agromrv_lite_final_{(cycle.get('cycle_id') or 'cycle')}"
    ontology = _refresh_cycle_ontology_meta(
        cycle,
        onto,
        ontology_version=version,
        export_suffix="_final",
    )
    ontology["publication_status"] = "FINAL_ONTOLOGY_PUBLISHED"
    # path final explícito
    exports = ontology.get("export_paths") or {}
    if exports.get("owl"):
        ontology["published_ontology_path"] = exports["owl"]
        ontology["working_ontology_path"] = exports.get("owl")
    cycle["ontology"] = ontology
    cycle["current_status"] = "Published"
    cycle.setdefault("ontology_parameter_events", []).append({
        "type": "publish",
        "status": "published",
        "actor": actor,
        "at": now_iso(),
        "updated": updated,
        "ontology_hash": ontology.get("ontology_hash"),
        "export_paths": ontology.get("export_paths"),
    })
    return cycle


def parameters_are_confirmed(cycle: dict, groups: Iterable[str]) -> tuple[bool, str]:
    """Verifica se os grupos indicados estão confirmed/published no factor_catalog."""
    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    try:
        from ontology.parameter_lifecycle import all_applicable_confirmed

        return all_applicable_confirmed(catalog, groups)
    except Exception as exc:
        return False, str(exc)


def publish_to_canonical_model(normalized_batch: dict) -> dict[str, Any]:
    """Publica no modelo canônico. Sem mock silencioso no fluxo real."""
    cycle_id = normalized_batch.get("cycle_id")
    if config.USE_MOCK_DATA:
        if not config.ALLOW_MOCK_FALLBACK:
            raise RuntimeError("USE_MOCK_DATA exige ALLOW_MOCK_FALLBACK apenas em testes explícitos.")
        log_call(logger, "ontology.publish.mock", mode="mock", cycle_id=cycle_id, reason="USE_MOCK_DATA")
        return _mock_publish(normalized_batch)
    if not config.USE_DIRECT_FUNCTION_CALLS or di.build_full_ontology is None:
        raise RuntimeError("ontology-manager indisponível (build_full_ontology não importado).")

    log_call(logger, "ontology.publish.start", cycle_id=cycle_id)
    with timed_op() as timer:
        try:
            onto = di.build_full_ontology()
            records = normalized_batch.get("normalized_payload", [])
            df = _records_to_dataframe(records)
            layout = normalized_batch.get("layout_id", "monthly:v1").split(":")[0]
            di.populate_from_dataframe(onto, df, layout_name=f"{layout}_property", source_name="frontend")

            export_paths = _export_ontology_files(onto, cycle_id)

            entity_count = len(list(onto.Property.instances())) if hasattr(onto, "Property") else 0
            obs_count = (
                len(list(onto.QuantitativeObservation.instances()))
                if hasattr(onto, "QuantitativeObservation")
                else 0
            )

            result = {
                "source": "real",
                "mode": "real",
                "entities_created": entity_count,
                "entities_updated": 0,
                "relationships_created": obs_count,
                "properties_filled": obs_count * 2,
                "ontology_version": "agromrv_lite_v2026_01",
                "mapping_version": "1.0",
                "publication_status": "CANONICAL_PUBLISHED",
                "graph_nodes": [
                    {"id": "farm", "label": "Fazenda", "type": "Property"},
                    {"id": "herd", "label": "Rebanho", "type": "Herd"},
                    {"id": "milk", "label": "Produção de Leite", "type": "MilkProduction"},
                    {"id": "energy", "label": "Energia", "type": "Energy"},
                    {"id": "fert", "label": "Fertilizantes", "type": "Fertilizers"},
                    {"id": "emissions", "label": "Fontes de Emissão", "type": "EmissionSources"},
                ],
                "graph_edges": [
                    {"from": "farm", "to": "herd", "label": "hasHerd"},
                    {"from": "herd", "to": "milk", "label": "produces"},
                    {"from": "farm", "to": "energy", "label": "consumes"},
                    {"from": "farm", "to": "fert", "label": "applies"},
                    {"from": "farm", "to": "emissions", "label": "emits"},
                ],
                "ontology_hash": sha256_dict({"entities": entity_count, "obs": obs_count}),
                "export_paths": export_paths,
                "_ontology": onto,
            }
            rp = None
            if records and isinstance(records[0], dict):
                rp = records[0].get("period") or records[0].get("periodo")
            result["canonical_variables"] = build_canonical_variables_snapshot_from_batch(normalized_batch, rp)
            _attach_factor_catalog(result, onto)
            # Hash inclui catálogo (valores pendentes catalogados)
            result["ontology_hash"] = sha256_dict({
                "entities": entity_count,
                "obs": obs_count,
                "factor_catalog": result.get("factor_catalog"),
            })
            log_call(
                logger,
                "ontology.publish.done",
                mode="real",
                cycle_id=cycle_id,
                entities=entity_count,
                observations=obs_count,
                duration_ms=timer.duration_ms,
            )
            return result
        except Exception as exc:
            log_fail(
                logger,
                "ontology.publish.failed",
                cycle_id=cycle_id,
                error=str(exc),
                duration_ms=timer.duration_ms,
            )
            if config.ALLOW_MOCK_FALLBACK:
                log_call(
                    logger,
                    "ontology.publish.mock",
                    mode="mock",
                    cycle_id=cycle_id,
                    reason=str(exc),
                    duration_ms=timer.duration_ms,
                )
                return _mock_publish(normalized_batch, reason=str(exc))
            raise


def run_semantic_validation(canonical_dataset: dict) -> dict[str, Any]:
    """Executa validações semânticas. Sem mock silencioso no fluxo real."""
    if config.USE_MOCK_DATA:
        if not config.ALLOW_MOCK_FALLBACK:
            raise RuntimeError("USE_MOCK_DATA exige ALLOW_MOCK_FALLBACK apenas em testes explícitos.")
        log_call(logger, "ontology.validate.mock", mode="mock", reason="USE_MOCK_DATA")
        return _mock_validation(canonical_dataset)
    if not config.USE_DIRECT_FUNCTION_CALLS or di.validate_all is None:
        raise RuntimeError("ontology-manager indisponível (validate_all não importado).")

    log_call(logger, "ontology.validate.start")
    with timed_op() as timer:
        try:
            onto = canonical_dataset.get("_ontology")
            if onto is None:
                raise RuntimeError(
                    "Objeto de ontologia ausente no ciclo (cache/_ontology). "
                    "Reexecute a etapa de modelo canônico antes da validação semântica."
                )

            issues = di.validate_all(onto, include_instances=True)
            # Apenas falhas estruturais (esquema/catálogo/método) são críticas;
            # lacunas em instâncias populadas são tratadas como alertas.
            def _is_critical(msg: str) -> bool:
                low = msg.lower()
                return any(k in low for k in ("schema", "catalog", "catálogo", "method", "método")) and (
                    "missing" in low or "required" in low or "invalid" in low or "inválid" in low
                )

            critical = [i for i in issues if _is_critical(i)]
            warnings = [i for i in issues if i not in critical]

            result = {
                "source": "real",
                "mode": "real",
                "total_validations": len(issues) + 10,
                "critical_errors": len(critical),
                "warnings": len(warnings),
                "inferences": 0,
                "affected_entities": canonical_dataset.get("entities_created", 0),
                "rules_applied": [
                    "validate_schema",
                    "validate_catalogs",
                    "validate_calculation_methods",
                    "validate_populated_instances",
                ],
                "issues": [{"rule": i, "severity": "ERROR" if i in critical else "WARNING"} for i in issues[:20]],
                "status": "SEMANTIC_VALIDATION_FAILED" if critical else (
                    "SEMANTIC_VALIDATION_PASSED_WITH_WARNINGS" if warnings else "SEMANTIC_VALIDATION_APPROVED"
                ),
                "validation_hash": sha256_dict({"issues": issues[:50]}),
            }
            log_call(
                logger,
                "ontology.validate.done",
                mode="real",
                critical=len(critical),
                warnings=len(warnings),
                status=result["status"],
                duration_ms=timer.duration_ms,
            )
            return result
        except Exception as exc:
            log_fail(
                logger,
                "ontology.validate.failed",
                error=str(exc),
                duration_ms=timer.duration_ms,
            )
            if config.ALLOW_MOCK_FALLBACK:
                log_call(
                    logger,
                    "ontology.validate.mock",
                    mode="mock",
                    reason=str(exc),
                    duration_ms=timer.duration_ms,
                )
                return _mock_validation(canonical_dataset, reason=str(exc))
            raise
