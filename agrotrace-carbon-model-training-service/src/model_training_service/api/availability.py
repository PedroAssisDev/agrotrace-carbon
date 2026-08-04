"""Disponibilidade de modelos por propriedade."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from model_training_service.api.contracts import (
    DataSummary,
    ModelAvailabilityItem,
    ModelAvailabilityReport,
)
from model_training_service.api.eligibility import EligibilityResult, EligibilityService
from model_training_service.api.registry_reader import (
    RegistryReader,
    load_manifest,
    load_metrics,
)
from model_training_service.api.run_store import TrainingRunStore
from model_training_service.api.slots import property_model_slots
from model_training_service.domain.enums import ModelAvailabilityStatus


class AvailabilityService:
    def __init__(
        self,
        config: dict[str, Any],
        registry: RegistryReader,
        run_store: TrainingRunStore,
        eligibility: EligibilityService,
    ) -> None:
        self.config = config
        self.registry = registry
        self.run_store = run_store
        self.eligibility = eligibility

    def build_report(
        self,
        property_id: str,
        data: pd.DataFrame | None,
        *,
        source_ok: bool = True,
        source_error: str | None = None,
    ) -> ModelAvailabilityReport:
        summary = self._data_summary(property_id, data)
        models: list[ModelAvailabilityItem] = []
        active_runs = [r.to_dict() for r in self.run_store.list_active_runs(property_id)]

        for slot in property_model_slots(property_id):
            if data is None or not source_ok:
                elig = EligibilityResult(
                    False,
                    source_error or "Fonte de dados indisponível.",
                    0,
                )
            else:
                elig = self.eligibility.evaluate(data, slot)

            lock_run = self.run_store.find_lock_run(slot.logical_key())
            active = self.registry.resolve_active(slot)
            failed_recent = self._last_failed_for_slot(property_id, slot.logical_key())

            if lock_run:
                models.append(
                    self._item_from_active(
                        slot,
                        active,
                        elig,
                        status=ModelAvailabilityStatus.TRAINING.value,
                        reason=f"Execução ativa: {lock_run}",
                        stale=False,
                    )
                )
                continue

            if active is None:
                if not elig.eligible:
                    status = ModelAvailabilityStatus.INELIGIBLE.value
                    reason = elig.reason
                elif failed_recent:
                    status = ModelAvailabilityStatus.FAILED.value
                    reason = failed_recent
                else:
                    status = ModelAvailabilityStatus.MISSING.value
                    reason = None
                models.append(
                    ModelAvailabilityItem(
                        family=slot.family,
                        scope=slot.scope,
                        property_id=slot.property_id,
                        granularity=slot.granularity,
                        target=slot.target,
                        status=status,
                        eligible=elig.eligible,
                        reason=reason,
                        record_count=elig.record_count,
                        training_period_start=elig.period_start,
                        training_period_end=elig.period_end,
                    )
                )
                continue

            stale = False
            reason = None
            if elig.eligible and data is not None and source_ok:
                stale = self._is_stale(slot, active, data, elig.period_end)
            status = (
                ModelAvailabilityStatus.STALE.value
                if stale
                else ModelAvailabilityStatus.AVAILABLE.value
            )
            if stale:
                reason = "Novos dados aprovados após o período de treinamento do modelo ativo."
            models.append(
                self._item_from_active(
                    slot, active, elig, status=status, reason=reason, stale=stale
                )
            )

        return ModelAvailabilityReport(
            property_id=property_id,
            data_summary=summary,
            models=models,
            active_training_runs=active_runs,
            updated_at=datetime.now(UTC).isoformat(),
            source_ok=source_ok,
            source_error=source_error,
        )

    def _item_from_active(
        self,
        slot,
        active: dict[str, Any] | None,
        elig: EligibilityResult,
        *,
        status: str,
        reason: str | None,
        stale: bool,
    ) -> ModelAvailabilityItem:
        if not active:
            return ModelAvailabilityItem(
                family=slot.family,
                scope=slot.scope,
                property_id=slot.property_id,
                granularity=slot.granularity,
                target=slot.target,
                status=status,
                eligible=elig.eligible,
                reason=reason or elig.reason,
                record_count=elig.record_count,
            )
        artifact_dir = active.get("artifact_dir")
        manifest = load_manifest(artifact_dir) if artifact_dir else {}
        metrics = load_metrics(artifact_dir) if artifact_dir else {}
        selected = (metrics.get("selected") or {}) if isinstance(metrics, dict) else {}
        metric_name = (self.config.get("selection") or {}).get("metric", "mae")
        score = selected.get(metric_name) or selected.get(f"cv_{metric_name}")
        return ModelAvailabilityItem(
            family=slot.family,
            scope=slot.scope,
            property_id=slot.property_id,
            granularity=slot.granularity,
            target=slot.target,
            status=status,
            eligible=elig.eligible,
            active_model_id=active.get("model_id"),
            active_version=active.get("version"),
            created_at=active.get("created_at"),
            training_period_start=manifest.get("period_start"),
            training_period_end=manifest.get("period_end"),
            record_count=manifest.get("row_count") or elig.record_count,
            algorithm=active.get("selected_candidate"),
            selection_metric=str(metric_name),
            selection_score=float(score) if score is not None else None,
            reason=reason,
            stale=stale,
            artifact_dir=str(artifact_dir) if artifact_dir else None,
        )

    def _is_stale(
        self,
        slot,
        active: dict[str, Any],
        data: pd.DataFrame,
        current_end: str | None,
    ) -> bool:
        manifest = load_manifest(active.get("artifact_dir") or "")
        model_end = manifest.get("period_end")
        if model_end and current_end:
            try:
                if pd.Timestamp(current_end) > pd.Timestamp(model_end):
                    return True
            except Exception:
                pass
        current_hash = self._current_dataset_hash(slot, data)
        model_hash = manifest.get("sha256")
        if current_hash and model_hash and current_hash != model_hash:
            return True
        return False

    def _current_dataset_hash(self, slot, data: pd.DataFrame) -> str | None:
        from model_training_service.registry.artifact_store import build_dataset_manifest

        try:
            if slot.family == "regression":
                feature = self.config["regression"]["feature"]
                subset = data[data["granularity"].eq(slot.granularity)][
                    ["property_id", "period", feature, slot.target]
                ].dropna()
            else:
                subset = data[
                    data["granularity"].eq("monthly")
                    & data["property_id"].astype(str).eq(str(slot.property_id))
                ][["property_id", "period", slot.target]].dropna()
            if subset.empty:
                return None
            return build_dataset_manifest(subset).get("sha256")
        except Exception:
            return None

    def _data_summary(self, property_id: str, data: pd.DataFrame | None) -> DataSummary:
        min_ts = int((self.config.get("time_series") or {}).get("min_records", 12))
        if data is None or data.empty:
            return DataSummary(min_ts_records=min_ts)

        monthly = data[data["granularity"].eq("monthly")]
        annual = data[data["granularity"].eq("annual")]
        prop_m = monthly[monthly["property_id"].astype(str).eq(str(property_id))]
        prop_a = annual[annual["property_id"].astype(str).eq(str(property_id))]

        def _last(frame: pd.DataFrame) -> str | None:
            if frame.empty or "period" not in frame.columns:
                return None
            ts = pd.to_datetime(frame["period"], errors="coerce").dropna()
            if ts.empty:
                return None
            return ts.max().isoformat()

        return DataSummary(
            monthly_records=int(len(monthly)),
            annual_records=int(len(annual)),
            last_monthly_period=_last(monthly),
            last_annual_period=_last(annual),
            property_monthly_records=int(len(prop_m)),
            property_annual_records=int(len(prop_a)),
            property_last_monthly_period=_last(prop_m),
            min_ts_records=min_ts,
        )

    def _last_failed_for_slot(self, property_id: str, logical_key: str) -> str | None:
        for run in self.run_store.list_runs(property_id, limit=10):
            if run.status != "failed":
                continue
            for item in run.models_failed:
                if item.get("logical_key") == logical_key:
                    return item.get("reason") or run.error_summary
        return None
