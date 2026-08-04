"""Execução de training runs em thread com persistência SQLite."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any, Callable

from model_training_service.api.contracts import ModelSlot, TrainModelsRequest, TrainingRunRecord
from model_training_service.api.data_source import load_configured_source
from model_training_service.api.run_store import TrainingRunStore
from model_training_service.domain.enums import TrainingRunStatus
from model_training_service.domain.errors import DataSourceUnavailableError, TrainingConflictError
from model_training_service.orchestration.training_service import ModelTrainingService


class TrainingRunExecutor:
    def __init__(
        self,
        config: dict[str, Any],
        run_store: TrainingRunStore,
        *,
        background: bool = True,
    ) -> None:
        self.config = config
        self.run_store = run_store
        self.background = background
        self._threads: dict[str, threading.Thread] = {}

    def start(self, request: TrainModelsRequest, slots: list[ModelSlot]) -> TrainingRunRecord:
        configuration = {
            "candidate_profile": request.candidate_profile,
            "selection_metric": request.selection_metric,
            "minimum_improvement_over_baseline": request.minimum_improvement_over_baseline,
            "activate_after_success": request.activate_after_success,
        }
        record = self.run_store.create_run(
            property_id=request.property_id,
            mode=request.mode,
            requested_models=[s.to_dict() for s in slots],
            configuration=configuration,
        )
        keys = [s.logical_key() for s in slots]
        try:
            self.run_store.acquire_locks(keys, record.run_id)
        except TrainingConflictError:
            self.run_store.update_run(
                record.run_id,
                status=TrainingRunStatus.CANCELLED.value,
                current_stage="Cancelado por conflito",
                finished_at=datetime.now(UTC).isoformat(),
                error_summary="Conflito de concorrência",
            )
            raise

        if self.background:
            thread = threading.Thread(
                target=self._execute,
                args=(record.run_id, request, slots),
                daemon=True,
                name=f"training-run-{record.run_id[:8]}",
            )
            self._threads[record.run_id] = thread
            thread.start()
        else:
            self._execute(record.run_id, request, slots)
        return self.run_store.get_run(record.run_id)

    def _execute(
        self,
        run_id: str,
        request: TrainModelsRequest,
        slots: list[ModelSlot],
    ) -> None:
        def stage(message: str) -> None:
            self.run_store.update_run(
                run_id,
                status=TrainingRunStatus.RUNNING.value,
                current_stage=message,
            )

        try:
            stage("Validando dados")
            raw, source_meta = load_configured_source(self.config)
            service = ModelTrainingService(self.config).with_overrides(
                {
                    "candidate_profile": request.candidate_profile,
                    "selection_metric": request.selection_metric,
                    "minimum_improvement_over_baseline": request.minimum_improvement_over_baseline,
                }
            )
            stage("Avaliando candidatos")
            report = service.run_selection(
                raw,
                slots=slots,
                data_source=source_meta,
                training_run_id=run_id,
                activate_after_success=request.activate_after_success,
                stage_callback=stage,
            )
            created = []
            for model in report.get("models") or []:
                created.append(
                    {
                        "model": model.get("model_id"),
                        "logical_key": model.get("logical_key"),
                        "version": model.get("version"),
                        "winner": model.get("winner") or model.get("selected_candidate"),
                        "baseline": model.get("baseline"),
                        "selection_comparison": model.get("selection_comparison"),
                        "activated": bool(model.get("active")),
                        "artifact_dir": model.get("artifact_dir"),
                    }
                )
            skipped = [
                {
                    "model": item.get("model"),
                    "logical_key": None,
                    "reason": item.get("reason"),
                }
                for item in (report.get("skipped") or [])
            ]
            failed = [
                {
                    "model": item.get("model"),
                    "logical_key": None,
                    "reason": item.get("reason"),
                }
                for item in (report.get("errors") or [])
            ]
            status = report.get("status") or TrainingRunStatus.COMPLETED.value
            if status not in {
                TrainingRunStatus.COMPLETED.value,
                TrainingRunStatus.PARTIAL.value,
                TrainingRunStatus.FAILED.value,
            }:
                if failed and created:
                    status = TrainingRunStatus.PARTIAL.value
                elif failed:
                    status = TrainingRunStatus.FAILED.value
                else:
                    status = TrainingRunStatus.COMPLETED.value

            self.run_store.update_run(
                run_id,
                status=status,
                current_stage="Concluído",
                finished_at=datetime.now(UTC).isoformat(),
                models_created=created,
                models_skipped=skipped,
                models_failed=failed,
                error_summary="; ".join(item.get("reason") or "" for item in failed) or None,
            )
        except DataSourceUnavailableError as exc:
            self.run_store.update_run(
                run_id,
                status=TrainingRunStatus.FAILED.value,
                current_stage="Falha na fonte de dados",
                finished_at=datetime.now(UTC).isoformat(),
                error_summary=str(exc),
                models_failed=[{"reason": str(exc)}],
            )
        except Exception as exc:  # noqa: BLE001
            self.run_store.update_run(
                run_id,
                status=TrainingRunStatus.FAILED.value,
                current_stage="Falha",
                finished_at=datetime.now(UTC).isoformat(),
                error_summary=str(exc),
                models_failed=[{"reason": str(exc)}],
            )
        finally:
            self.run_store.release_locks(run_id)
            self._threads.pop(run_id, None)
