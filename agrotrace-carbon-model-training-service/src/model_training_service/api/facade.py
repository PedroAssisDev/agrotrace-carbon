"""Fachada pública programática do model-training-service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from model_training_service.api.availability import AvailabilityService
from model_training_service.api.contracts import (
    ModelAvailabilityReport,
    ModelSlot,
    TrainModelsRequest,
    TrainingRunRecord,
)
from model_training_service.api.data_source import load_configured_source
from model_training_service.api.eligibility import EligibilityService
from model_training_service.api.executor import TrainingRunExecutor
from model_training_service.api.registry_reader import RegistryReader
from model_training_service.api.run_store import TrainingRunStore
from model_training_service.api.slots import validate_request_slots
from model_training_service.config import (
    ALLOWED_CANDIDATE_PROFILES,
    ALLOWED_SELECTION_METRICS,
    load_config,
)
from model_training_service.domain.enums import (
    ModelAvailabilityStatus,
    TrainingMode,
    VersionStatus,
)
from model_training_service.domain.errors import (
    DataSourceUnavailableError,
    InvalidTrainingRequestError,
)
from model_training_service.data.validation import normalize_approved_results
from model_training_service.orchestration.training_service import ModelTrainingService
from model_training_service.registry.active_index import ActiveModelIndex


class ModelTrainingFacade:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        config_path: str | Path | None = None,
        *,
        background: bool = True,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            default = (
                Path(__file__).resolve().parents[3] / "configs" / "training.yaml"
            )
            self.config = load_config(config_path or default)
        artifacts = Path(self.config["paths"]["artifacts_dir"])
        self.registry = RegistryReader(artifacts)
        self.run_store = TrainingRunStore(artifacts / "training_runs.db")
        self.eligibility = EligibilityService(self.config)
        self.availability = AvailabilityService(
            self.config, self.registry, self.run_store, self.eligibility
        )
        self.executor = TrainingRunExecutor(
            self.config, self.run_store, background=background
        )
        self.active_index = ActiveModelIndex(artifacts)

    def get_model_availability(self, property_id: str) -> ModelAvailabilityReport:
        data, source_ok, source_error = self._load_normalized()
        return self.availability.build_report(
            property_id,
            data,
            source_ok=source_ok,
            source_error=source_error,
        )

    def get_training_eligibility(self, property_id: str) -> dict[str, Any]:
        report = self.get_model_availability(property_id)
        return {
            "property_id": property_id,
            "source_ok": report.source_ok,
            "source_error": report.source_error,
            "items": [
                {
                    "slot": {
                        "family": m.family,
                        "scope": m.scope,
                        "granularity": m.granularity,
                        "target": m.target,
                        "property_id": m.property_id,
                    },
                    "eligible": m.eligible,
                    "reason": m.reason,
                    "record_count": m.record_count,
                }
                for m in report.models
            ],
        }

    def ensure_models(
        self,
        property_id: str,
        *,
        candidate_profile: str = "core",
        selection_metric: str = "mae",
        minimum_improvement_over_baseline: float = 0.0,
        activate_after_success: bool = True,
    ) -> TrainingRunRecord:
        request = TrainModelsRequest(
            property_id=property_id,
            mode=TrainingMode.ENSURE_MISSING.value,
            candidate_profile=candidate_profile,
            selection_metric=selection_metric,
            minimum_improvement_over_baseline=minimum_improvement_over_baseline,
            activate_after_success=activate_after_success,
        )
        return self.train_models(request)

    def retrain_models(self, request: TrainModelsRequest) -> TrainingRunRecord:
        if request.mode == TrainingMode.ENSURE_MISSING.value:
            request.mode = TrainingMode.RETRAIN_SELECTED.value
        return self.train_models(request)

    def train_models(self, request: TrainModelsRequest) -> TrainingRunRecord:
        self._validate_safe_config(request)
        report = self.get_model_availability(request.property_id)
        if not report.source_ok:
            raise DataSourceUnavailableError(
                report.source_error or "Fonte de dados indisponível."
            )

        slots = self._resolve_slots(request, report)
        validate_request_slots(request.property_id, slots)
        # Conflito explícito antes de criar run
        for slot in slots:
            existing = self.run_store.find_lock_run(slot.logical_key())
            if existing:
                from model_training_service.domain.errors import TrainingConflictError

                raise TrainingConflictError(
                    f"Treinamento já em andamento para {slot.label()}.",
                    run_id=existing,
                )
        request.slots = slots
        return self.executor.start(request, slots)

    def get_training_run(self, run_id: str) -> TrainingRunRecord:
        return self.run_store.get_run(run_id)

    def list_training_runs(self, property_id: str | None = None) -> list[TrainingRunRecord]:
        return self.run_store.list_runs(property_id)

    def activate_model_version(self, model_id: str) -> dict[str, Any]:
        for entry in self.registry.read_all():
            if entry.get("model_id") != model_id:
                continue
            family = entry.get("model_family")
            if family == "regression":
                key = f"regression|{entry.get('granularity')}|{entry.get('target')}|global"
            else:
                key = (
                    f"time_series|monthly|{entry.get('property_id')}|{entry.get('target')}"
                )
            previous = self.active_index.get(key)
            self.active_index.set_active(
                key,
                model_id=str(entry["model_id"]),
                version=str(entry["version"]),
                artifact_dir=str(entry["artifact_dir"]),
                training_run_id=entry.get("training_run_id"),
                supersedes=(previous or {}).get("model_id"),
                metadata={**entry, "status": VersionStatus.ACTIVE.value},
            )
            return {"activated": True, "logical_key": key, "model_id": model_id}
        raise InvalidTrainingRequestError(f"Modelo não encontrado no registry: {model_id}")

    def train_all_sync(
        self,
        raw_data=None,
        data_source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compatibilidade CLI: treina tudo de forma síncrona."""
        if raw_data is None:
            raw_data, data_source = load_configured_source(
                self.config, override=data_source
            )
        service = ModelTrainingService(self.config)
        return service.run(raw_data, data_source=data_source)

    def _resolve_slots(
        self, request: TrainModelsRequest, report: ModelAvailabilityReport
    ) -> list[ModelSlot]:
        by_key = {
            ModelSlot(
                family=m.family,
                scope=m.scope,
                granularity=m.granularity,
                target=m.target,
                property_id=m.property_id,
            ).logical_key(): m
            for m in report.models
        }
        mode = request.mode

        if mode == TrainingMode.ENSURE_MISSING.value:
            selected = []
            for m in report.models:
                if m.status == ModelAvailabilityStatus.MISSING.value and m.eligible:
                    selected.append(
                        ModelSlot(
                            family=m.family,
                            scope=m.scope,
                            granularity=m.granularity,
                            target=m.target,
                            property_id=m.property_id,
                        )
                    )
                elif m.status == ModelAvailabilityStatus.INELIGIBLE.value:
                    continue
            if not selected:
                # still allow empty? better raise controlled
                raise InvalidTrainingRequestError(
                    "Não há modelos ausentes elegíveis para criar."
                )
            return selected

        if mode == TrainingMode.RETRAIN_STALE.value:
            selected = [
                ModelSlot(
                    family=m.family,
                    scope=m.scope,
                    granularity=m.granularity,
                    target=m.target,
                    property_id=m.property_id,
                )
                for m in report.models
                if m.status == ModelAvailabilityStatus.STALE.value and m.eligible
            ]
            if not selected:
                raise InvalidTrainingRequestError("Não há modelos desatualizados elegíveis.")
            return selected

        if mode == TrainingMode.RETRAIN_SELECTED.value:
            if not request.slots:
                raise InvalidTrainingRequestError(
                    "RETRAIN_SELECTED exige slots selecionados."
                )
            selected = []
            for slot in request.slots:
                item = by_key.get(slot.logical_key())
                if item is None:
                    raise InvalidTrainingRequestError(f"Slot inválido: {slot.label()}")
                if not item.eligible and item.status == ModelAvailabilityStatus.INELIGIBLE.value:
                    raise InvalidTrainingRequestError(
                        f"Slot inelegível: {slot.label()} — {item.reason}"
                    )
                # TRAINING é tratado via lock em train_models (TrainingConflictError)
                selected.append(slot)
            return selected

        raise InvalidTrainingRequestError(f"Modo inválido: {mode}")

    def _validate_safe_config(self, request: TrainModelsRequest) -> None:
        if request.candidate_profile not in ALLOWED_CANDIDATE_PROFILES:
            raise InvalidTrainingRequestError(
                f"candidate_profile inválido: {request.candidate_profile}"
            )
        metric = str(request.selection_metric).lower()
        if metric not in ALLOWED_SELECTION_METRICS:
            raise InvalidTrainingRequestError(f"selection_metric inválida: {metric}")
        request.selection_metric = metric
        try:
            value = float(request.minimum_improvement_over_baseline)
        except (TypeError, ValueError) as exc:
            raise InvalidTrainingRequestError(
                "minimum_improvement_over_baseline inválido."
            ) from exc
        if value < 0:
            raise InvalidTrainingRequestError(
                "minimum_improvement_over_baseline deve ser >= 0."
            )
        request.minimum_improvement_over_baseline = value

    def _load_normalized(self):
        try:
            raw, _meta = load_configured_source(self.config)
            validation = self.config["validation"]
            data = normalize_approved_results(
                raw,
                approved_values=validation.get("approved_values", ["approved"]),
                published_values=validation.get("published_values", ["published"]),
                duplicate_policy=validation.get("duplicate_policy", "reject"),
            )
            return data, True, None
        except Exception as exc:  # noqa: BLE001
            return None, False, str(exc)


def get_default_facade(*, background: bool = True) -> ModelTrainingFacade:
    return ModelTrainingFacade(background=background)
