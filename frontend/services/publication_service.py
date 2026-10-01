"""Publicação final tipada — manifesto imutável do ciclo aprovado.

Responsabilidade: validar aprovação, montar manifesto canônico, calcular hash
estável, persistir em ``frontend/data/publications/`` e retornar contrato tipado
para o orquestrador / pacote de evidências.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import config
from services.calculation_approval_service import can_finalize
from services.domain_catalog import (
    PUBLICATION_MILESTONE,
    OrganizationalGranularity,
    TemporalGranularity,
    normalize_organizational,
    normalize_temporal,
)
from utils.date_helpers import now_iso
from utils.hash_helpers import sha256_dict
from utils.pipeline_logging import ids_from_cycle, log_call, timed_op, truncate

logger = logging.getLogger("agrotrace.publication")

MANIFEST_SCHEMA_VERSION = "1.0.0"


class PredictionNotPublishableError(ValueError):
    """Predições não podem ser publicadas como resultados observados (RF011 / RN-03)."""


def _reject_prediction_input(cycle: dict) -> None:
    """Guarda de domínio: rejeita Prediction / payloads preditivos na publicação."""
    from services.forecast_inference.types import Prediction, is_prediction_payload

    if isinstance(cycle, Prediction) or is_prediction_payload(cycle):
        raise PredictionNotPublishableError(
            "Prediction não pode ser publicada como resultado observado/calculado (RF011/RN-03)"
        )
    # Explicit injection probes
    for key in ("prediction", "forecast_result", "predicted_results"):
        val = cycle.get(key) if isinstance(cycle, dict) else None
        if is_prediction_payload(val):
            raise PredictionNotPublishableError(
                f"Campo '{key}' contém Prediction e não pode integrar a publicação oficial"
            )
    forecast = (cycle.get("forecast") if isinstance(cycle, dict) else None) or {}
    if isinstance(forecast, dict) and forecast.get("publish_as_calculation"):
        raise PredictionNotPublishableError(
            "forecast.publish_as_calculation é proibido — predição ≠ CalculationResult"
        )
    approved = (cycle.get("approved_results") if isinstance(cycle, dict) else None) or {}
    if is_prediction_payload(approved):
        raise PredictionNotPublishableError(
            "approved_results não pode ser um payload de Prediction"
        )


@dataclass
class PublicationManifest:
    publication_id: str
    cycle_id: str
    farm_id: str
    property_id: str
    lot_id: str | None
    animal_id: str | None
    organizational_granularity: str
    period_start: str
    period_end: str
    temporal_granularity: str
    original_file_ref: str | None
    original_file_hash: str | None
    normalized_ref: str | None
    normalized_hash: str | None
    wrapper_version: str | None
    ontology_ref: str | None
    ontology_hash: str | None
    ontology_version: str | None
    validations: dict[str, Any]
    approved_results: dict[str, Any]
    calculation_params: dict[str, Any]
    emission_factors: dict[str, Any]
    gwp: dict[str, float]
    factor_source: str | None
    units: dict[str, str]
    review_decisions: list[dict[str, Any]]
    reviewers: list[str]
    approved_at: str
    published_at: str
    publication_hash: str
    schema_version: str = MANIFEST_SCHEMA_VERSION
    status: str = "PUBLISHED"
    methodology: str | None = None
    version_manifest: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _period_bounds(reporting_period: str, temporal: TemporalGranularity) -> tuple[str, str]:
    rp = str(reporting_period or "").strip()
    if temporal == TemporalGranularity.ANNUAL and len(rp) == 4 and rp.isdigit():
        return f"{rp}-01-01", f"{rp}-12-31"
    if temporal == TemporalGranularity.MONTHLY and len(rp) >= 7:
        y, m = rp[:4], rp[5:7]
        return f"{y}-{m}-01", f"{y}-{m}-28"
    if temporal == TemporalGranularity.DAILY and len(rp) >= 10:
        return rp[:10], rp[:10]
    return rp, rp


def _hashable_core(payload: dict[str, Any]) -> dict[str, Any]:
    """Campos que entram no hash canônico (sem published_at volátil)."""
    skip = {"published_at", "publication_hash", "publication_id"}
    return {k: v for k, v in payload.items() if k not in skip}


def _stable_publication_id(cycle_id: str, content_hash: str) -> str:
    """ID determinístico a partir do ciclo + hash do conteúdo aprovado."""
    seed = f"{cycle_id}:{content_hash}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def build_publication_manifest(cycle: dict) -> PublicationManifest:
    """Monta e valida o manifesto a partir do ciclo aprovado."""
    _reject_prediction_input(cycle)
    ok, msg = can_finalize(cycle)
    approval = cycle.get("approval") or {}
    if approval.get("decision") != "APPROVED":
        # can_finalize cobre revisão por item; exige também decisão de arquivo
        if not ok:
            raise ValueError(msg)
        raise ValueError("Decisão de aprovação geral ausente ou não APPROVED.")
    if not ok:
        raise ValueError(msg)

    calc = cycle.get("calculation") or {}
    ontology = cycle.get("ontology") or {}
    raw = cycle.get("raw_file") or {}
    wrapper = cycle.get("wrapper") or {}
    semantic = cycle.get("semantic_validation") or {}
    review = cycle.get("calculation_review") or {}
    items = review.get("items") or []

    temporal = normalize_temporal(
        cycle.get("granularity")
        or (calc.get("temporal") or {}).get("scope")
        or cycle.get("frequency"),
        default=TemporalGranularity.MONTHLY,
    )
    org = normalize_organizational(
        cycle.get("organizational_granularity"),
        default=OrganizationalGranularity.PROPERTY,
    )
    period = str(cycle.get("reporting_period") or "")
    period_start, period_end = _period_bounds(period, temporal)

    gwp = dict(calc.get("gwp") or {})
    if not gwp:
        raise ValueError("GWP ausente no resultado de cálculo; publicação exige GWP explícito.")

    factors = dict(calc.get("factors_used") or {})
    approved_results = {
        "co2e_total_kg": calc.get("co2e_total_kg"),
        "co2e_intensity_per_milk_liter": calc.get("co2e_intensity_per_milk_liter"),
        "ch4_enteric_kg": calc.get("ch4_enteric_kg"),
        "ch4_manure_kg": calc.get("ch4_manure_kg"),
        "n2o_fertilizer_kg": calc.get("n2o_fertilizer_kg"),
        "co2_energy_kg": calc.get("co2_energy_kg"),
        "by_source": calc.get("by_source"),
        "by_gas": calc.get("by_gas"),
        "preliminary_hash": calc.get("preliminary_hash"),
        "subcalculations": [
            {
                "calculation_item_id": it.get("calculation_item_id"),
                "formula_name": it.get("formula_name"),
                "status": it.get("status"),
                "result_value": it.get("result_value"),
            }
            for it in items
            if it.get("status") in {
                "APPROVED",
                "APPROVED_WITH_ZERO",
                "APPROVED_WITH_MANUAL_ADJUSTMENT",
                "NOT_APPLICABLE",
            }
        ],
    }

    review_decisions = [
        {
            "calculation_item_id": it.get("calculation_item_id"),
            "formula_name": it.get("formula_name"),
            "status": it.get("status"),
            "reviewed_by": it.get("reviewed_by"),
            "reviewed_at": it.get("reviewed_at"),
            "justification": it.get("justification"),
        }
        for it in items
    ]

    reviewers = sorted({
        *(it.get("reviewed_by") for it in items if it.get("reviewed_by")),
        approval.get("approver"),
        review.get("finalized_by"),
    } - {None, ""})

    owl_paths = (ontology.get("export_paths") or {})
    ontology_ref = owl_paths.get("owl") or owl_paths.get("ttl")

    draft = {
        "cycle_id": cycle.get("cycle_id"),
        "farm_id": cycle.get("property_id"),
        "property_id": cycle.get("property_id"),
        "lot_id": cycle.get("lot_id"),
        "animal_id": cycle.get("animal_id"),
        "organizational_granularity": org.value,
        "period_start": period_start,
        "period_end": period_end,
        "temporal_granularity": temporal.value,
        "original_file_ref": raw.get("stored_path"),
        "original_file_hash": raw.get("sha256"),
        "normalized_ref": wrapper.get("normalized_file"),
        "normalized_hash": wrapper.get("content_hash"),
        "wrapper_version": wrapper.get("layout_version") or wrapper.get("layout_id"),
        "ontology_ref": ontology_ref,
        "ontology_hash": ontology.get("ontology_hash"),
        "ontology_version": ontology.get("ontology_version"),
        "validations": {
            "status": semantic.get("status"),
            "critical_errors": semantic.get("critical_errors"),
            "warnings": semantic.get("warnings"),
            "validation_hash": semantic.get("validation_hash"),
        },
        "approved_results": approved_results,
        "calculation_params": {
            "method": calc.get("method"),
            "temporal": calc.get("temporal"),
            "inputs": calc.get("inputs"),
            "data_source": calc.get("data_source"),
        },
        "emission_factors": factors,
        "gwp": gwp,
        "factor_source": (calc.get("method") or {}).get("code"),
        "units": {
            "emissions": "kg",
            "co2e": "kg CO2e",
            "intensity": "kg CO2e / L milk",
        },
        "review_decisions": review_decisions,
        "reviewers": reviewers,
        "approved_at": approval.get("approved_at") or review.get("finalized_at") or now_iso(),
        "methodology": calc.get("methodology"),
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status": "PUBLISHED",
    }

    try:
        from services.version_manifest_service import attach_version_manifest

        draft["version_manifest"] = attach_version_manifest(cycle)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PUB] version_manifest skipped: %s", type(exc).__name__)

    content_hash = sha256_dict(_hashable_core(draft))
    publication_id = _stable_publication_id(str(cycle.get("cycle_id")), content_hash)

    # Idempotência: se já existe manifesto idêntico, reutilizar
    existing = cycle.get("publication") or {}
    if (
        existing.get("publication_hash") == content_hash
        and existing.get("status") == "PUBLISHED"
        and existing.get("publication_id")
    ):
        logger.info(
            "[PUB] idempotent reuse publication_id=%s hash=%s…",
            existing.get("publication_id"),
            content_hash[:12],
        )
        return PublicationManifest(
            publication_id=str(existing["publication_id"]),
            published_at=existing.get("published_at") or now_iso(),
            publication_hash=content_hash,
            **{k: draft[k] for k in draft if k not in {"schema_version", "status"}},
            schema_version=MANIFEST_SCHEMA_VERSION,
            status="PUBLISHED",
        )

    if existing.get("status") == "PUBLISHED" and existing.get("publication_hash") and existing.get("publication_hash") != content_hash:
        raise ValueError(
            "Ciclo já publicado com hash diferente. "
            "Altere a revisão ou crie um novo ciclo para republicar."
        )

    published_at = now_iso()
    return PublicationManifest(
        publication_id=publication_id,
        published_at=published_at,
        publication_hash=content_hash,
        **{k: draft[k] for k in draft if k not in {"schema_version", "status"}},
        schema_version=MANIFEST_SCHEMA_VERSION,
        status="PUBLISHED",
    )


def persist_manifest(manifest: PublicationManifest) -> Path:
    config.ensure_data_dirs()
    config.PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PUBLICATIONS_DIR / f"{manifest.cycle_id}_{manifest.publication_id}.json"
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False, sort_keys=True, default=str),
        encoding="utf-8",
    )
    logger.info("[PUB] saved %s hash=%s…", path.name, manifest.publication_hash[:12])
    return path


def publish_approved_cycle(cycle: dict) -> dict[str, Any]:
    """Operação oficial de publicação — retorna dict serializável para o ciclo."""
    from services.ontology_adapter import mark_parameters_published

    _reject_prediction_input(cycle)
    log_call(logger, "publication.start", **ids_from_cycle(cycle))
    with timed_op() as timer:
        # Republica OWL final com parâmetros published antes do manifesto
        reviewer = (cycle.get("calculation_review") or {}).get("finalized_by") or (
            (cycle.get("approval") or {}).get("approver")
        )
        cycle = mark_parameters_published(cycle, actor=reviewer)

        manifest = build_publication_manifest(cycle)
        path = persist_manifest(manifest)
        out = manifest.to_dict()
        out["manifest_path"] = str(path)
        # Compatibilidade com gates legados — preferir hash/versão da ontologia final
        ontology = cycle.get("ontology") or {}
        out["ontology_hash"] = (
            ontology.get("ontology_hash")
            or manifest.ontology_hash
            or manifest.publication_hash
        )
        out["ontology_version"] = (
            ontology.get("ontology_version")
            or manifest.ontology_version
            or f"published_{manifest.temporal_granularity}"
        )
        out["ontology_ref"] = ((ontology.get("export_paths") or {}).get("owl")
                               or manifest.ontology_ref)
        out["milestone"] = PUBLICATION_MILESTONE
        out["factor_catalog"] = ontology.get("factor_catalog")
        log_call(
            logger,
            "publication.done",
            **ids_from_cycle(cycle),
            publication_id=truncate(out.get("publication_id")),
            publication_hash=truncate(out.get("publication_hash")),
            duration_ms=timer.duration_ms,
        )
    # Best-effort: mantém a fonte de treino alinhada aos ciclos publicados.
    try:
        from services.model_training_adapter import refresh_training_source

        refresh_training_source(force=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PUB] refresh training source failed: %s", exc)
    return out


def evidence_input_from_publication(cycle: dict) -> dict[str, Any]:
    """Entrada mínima (não sensível) para o pacote de evidências."""
    pub = cycle.get("publication") or {}
    return {
        "cycle_id": cycle.get("cycle_id"),
        "publication_id": pub.get("publication_id"),
        "publication_hash": pub.get("publication_hash"),
        "original_file_hash": pub.get("original_file_hash"),
        "normalized_hash": pub.get("normalized_hash"),
        "ontology_hash": pub.get("ontology_hash"),
        "property_id": pub.get("property_id") or cycle.get("property_id"),
        "period_start": pub.get("period_start"),
        "period_end": pub.get("period_end"),
        "temporal_granularity": pub.get("temporal_granularity"),
        "organizational_granularity": pub.get("organizational_granularity"),
        "approved_co2e_total_kg": (pub.get("approved_results") or {}).get("co2e_total_kg"),
        "gwp": pub.get("gwp"),
        "schema_version": pub.get("schema_version"),
    }
