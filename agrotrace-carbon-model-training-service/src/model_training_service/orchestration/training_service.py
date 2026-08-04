from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from model_training_service.api.contracts import ModelSlot
from model_training_service.data.dataset_builder import DatasetBuilder
from model_training_service.data.validation import normalize_approved_results
from model_training_service.domain.enums import ModelFamily
from model_training_service.domain.errors import ModelTrainingError
from model_training_service.registry.artifact_store import ArtifactStore
from model_training_service.registry.environment import write_run_artifacts
from model_training_service.regression.trainer import RegressionTrainer
from model_training_service.time_series.trainer import PropertySkippedError, TimeSeriesTrainer


class ModelTrainingService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.dataset_builder = DatasetBuilder(config["paths"]["processed_data_dir"])
        self.artifact_store = ArtifactStore(config["paths"]["artifacts_dir"])
        selection = config.get("selection") or {
            "metric": "mae",
            "minimum_improvement_over_baseline": 0.0,
        }
        gap_policy = (config.get("validation") or {}).get("monthly_gap_policy", "reject")
        self.regression_trainer = RegressionTrainer(config["regression"], selection)
        self.time_series_trainer = TimeSeriesTrainer(
            config["time_series"], selection, monthly_gap_policy=gap_policy
        )
        self.selection = selection
        self.gap_policy = gap_policy

    def with_overrides(self, overrides: dict[str, Any] | None) -> "ModelTrainingService":
        if not overrides:
            return self
        cfg = copy.deepcopy(self.config)
        if "candidate_profile" in overrides:
            cfg.setdefault("regression", {})["candidate_profile"] = overrides["candidate_profile"]
        if "selection_metric" in overrides:
            cfg.setdefault("selection", {})["metric"] = overrides["selection_metric"]
        if "minimum_improvement_over_baseline" in overrides:
            cfg.setdefault("selection", {})["minimum_improvement_over_baseline"] = float(
                overrides["minimum_improvement_over_baseline"]
            )
        return ModelTrainingService(cfg)

    def run(
        self,
        raw_data: pd.DataFrame,
        data_source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Train-all: todas as regressões + todas as séries de todas as propriedades."""
        return self.run_selection(
            raw_data,
            slots=None,
            data_source=data_source,
        )

    def run_selection(
        self,
        raw_data: pd.DataFrame,
        slots: Iterable[ModelSlot] | None = None,
        *,
        data_source: dict[str, Any] | None = None,
        training_run_id: str | None = None,
        activate_after_success: bool = True,
        stage_callback=None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        self._stage(stage_callback, "Validando dados")
        run_paths = write_run_artifacts(self.config["paths"]["artifacts_dir"], self.config)
        environment = {
            "config_sha256": (self.config.get("_meta") or {}).get("config_sha256"),
            "environment_path": run_paths["environment_path"],
            "resolved_config_path": run_paths["resolved_config_path"],
        }
        self.artifact_store.set_run_context(environment)

        validation_config = self.config["validation"]
        data = normalize_approved_results(
            raw_data,
            approved_values=validation_config.get("approved_values", ["approved"]),
            published_values=validation_config.get("published_values", ["published"]),
            duplicate_policy=validation_config.get("duplicate_policy", "reject"),
        )
        self._stage(stage_callback, "Materializando datasets")
        datasets = self.dataset_builder.materialize(data)
        report: dict[str, Any] = {
            "status": "completed",
            "input_rows": int(len(raw_data)),
            "approved_rows": int(len(data)),
            "datasets": datasets,
            "models": [],
            "skipped": [],
            "skipped_properties": [],
            "errors": [],
            "gap_policy": self.gap_policy,
            "selection": dict(self.selection),
            "validation_strategies_used": [],
            "environment_path": run_paths["environment_path"],
            "resolved_config_path": run_paths["resolved_config_path"],
            "config_sha256": environment["config_sha256"],
            "training_run_id": training_run_id,
        }
        if data_source is not None:
            report["data_source"] = dict(data_source)

        self._maybe_skip_lstm(report)

        slot_list = list(slots) if slots is not None else None
        if slot_list is None:
            self._train_regression_models(
                data,
                report,
                training_run_id=training_run_id,
                activate=activate_after_success,
                stage_callback=stage_callback,
            )
            self._train_time_series_models(
                data,
                report,
                training_run_id=training_run_id,
                activate=activate_after_success,
                stage_callback=stage_callback,
            )
        else:
            for slot in slot_list:
                self._train_slot(
                    data,
                    slot,
                    report,
                    training_run_id=training_run_id,
                    activate=activate_after_success,
                    stage_callback=stage_callback,
                )

        self._stage(stage_callback, "Atualizando registry")
        report["duration_seconds"] = round(time.perf_counter() - started, 3)
        report["validation_strategies_used"] = sorted(set(report["validation_strategies_used"]))
        if report["errors"] and not report["models"]:
            report["status"] = "failed"
        elif report["errors"] or report["skipped"]:
            report["status"] = "partial" if report["models"] else report["status"]
            if report["errors"] and report["models"]:
                report["status"] = "partial"
            elif report["errors"] and not report["models"]:
                report["status"] = "failed"
        self._stage(stage_callback, "Concluído")
        return report

    def _train_slot(
        self,
        data: pd.DataFrame,
        slot: ModelSlot,
        report: dict[str, Any],
        *,
        training_run_id: str | None,
        activate: bool,
        stage_callback,
    ) -> None:
        if slot.family == ModelFamily.REGRESSION.value:
            stage = (
                "Treinando regressão mensal"
                if slot.granularity == "monthly"
                else "Treinando regressão anual"
            )
            self._stage(stage_callback, stage)
            self._train_one_regression(
                data,
                slot.granularity,
                slot.target,
                report,
                training_run_id=training_run_id,
                activate=activate,
            )
            return

        stage = (
            "Treinando série de produção"
            if "milk" in slot.target
            else "Treinando série de emissão"
        )
        self._stage(stage_callback, stage)
        monthly = data[data["granularity"].eq(self.config["time_series"]["granularity"])]
        property_data = monthly[monthly["property_id"].astype(str).eq(str(slot.property_id))]
        self._train_one_time_series(
            property_data,
            str(slot.property_id),
            slot.target,
            report,
            training_run_id=training_run_id,
            activate=activate,
        )

    def _maybe_skip_lstm(self, report: dict[str, Any]) -> None:
        ts = self.config.get("time_series") or {}
        if not ts.get("enable_lstm"):
            return
        report["skipped"].append(
            {
                "model": "time_series/lstm",
                "reason": (
                    "LSTM experimental ainda não está integrada ao pipeline padrão. "
                    f"Requisito futuro documentado: lstm_min_records="
                    f"{ts.get('lstm_min_records', 36)}. "
                    "Nenhuma dependência TensorFlow foi carregada."
                ),
            }
        )

    def _train_regression_models(
        self,
        data: pd.DataFrame,
        report: dict[str, Any],
        *,
        training_run_id: str | None = None,
        activate: bool = True,
        stage_callback=None,
    ) -> None:
        regression_config = self.config["regression"]
        if not regression_config.get("enabled", True):
            return
        for granularity in regression_config["granularities"]:
            stage = (
                "Treinando regressão mensal"
                if granularity == "monthly"
                else "Treinando regressão anual"
            )
            self._stage(stage_callback, stage)
            for target in regression_config["targets"]:
                self._train_one_regression(
                    data,
                    granularity,
                    target,
                    report,
                    training_run_id=training_run_id,
                    activate=activate,
                )

    def _train_one_regression(
        self,
        data: pd.DataFrame,
        granularity: str,
        target: str,
        report: dict[str, Any],
        *,
        training_run_id: str | None,
        activate: bool,
    ) -> None:
        label = f"regression/{granularity}/global/{target}"
        try:
            result = self.regression_trainer.train(data, granularity, target)
            self._stage_eval(report)
            artifact = self.artifact_store.save_regression(
                model=result.model,
                granularity=granularity,
                target=target,
                selected_candidate=result.selected_candidate,
                selected_params=result.selected_params,
                metrics=result.metrics,
                candidate_results=result.candidate_results,
                training_data=result.training_data,
                feature=self.config["regression"]["feature"],
                selection_comparison=result.selection_comparison,
                validation_strategy=result.validation_strategy,
                feature_columns=result.feature_columns,
                training_run_id=training_run_id,
                activate=activate,
            )
            report["models"].append(
                {
                    **artifact,
                    "baseline": result.selection_comparison.get("baseline_name"),
                    "winner": result.selected_candidate,
                    "selection_comparison": result.selection_comparison,
                    "validation_strategy": result.validation_strategy,
                }
            )
            report["validation_strategies_used"].append(result.validation_strategy)
        except ModelTrainingError as exc:
            report["skipped"].append({"model": label, "reason": str(exc)})
        except Exception as exc:
            report["errors"].append({"model": label, "reason": str(exc)})

    def _train_time_series_models(
        self,
        data: pd.DataFrame,
        report: dict[str, Any],
        *,
        training_run_id: str | None = None,
        activate: bool = True,
        stage_callback=None,
    ) -> None:
        ts_config = self.config["time_series"]
        if not ts_config.get("enabled", True):
            return
        monthly = data[data["granularity"].eq(ts_config["granularity"])]
        skipped_properties: set[str] = set(
            item["property_id"] for item in report["skipped_properties"]
        )
        for property_id, property_data in monthly.groupby("property_id", sort=True):
            property_key = str(property_id)
            if property_key in skipped_properties:
                continue
            for target in ts_config["targets"]:
                stage = (
                    "Treinando série de produção"
                    if "milk" in target
                    else "Treinando série de emissão"
                )
                self._stage(stage_callback, stage)
                try:
                    self._train_one_time_series(
                        property_data,
                        property_key,
                        target,
                        report,
                        training_run_id=training_run_id,
                        activate=activate,
                        skipped_properties=skipped_properties,
                    )
                except _StopProperty:
                    break

    def _train_one_time_series(
        self,
        property_data: pd.DataFrame,
        property_id: str,
        target: str,
        report: dict[str, Any],
        *,
        training_run_id: str | None,
        activate: bool,
        skipped_properties: set[str] | None = None,
    ) -> None:
        label = f"time_series/monthly/{property_id}/{target}"
        try:
            result = self.time_series_trainer.train(property_data, property_id, target)
            self._stage_eval(report)
            artifact = self.artifact_store.save_time_series(
                model=result.model,
                property_id=property_id,
                target=target,
                selected_candidate=result.selected_candidate,
                metrics=result.metrics,
                candidate_results=result.candidate_results,
                training_series=result.training_series,
                validation_predictions=result.validation_predictions,
                horizon=int(self.config["time_series"]["forecast_horizon"]),
                selection_comparison=result.selection_comparison,
                validation_strategy=result.validation_strategy,
                training_run_id=training_run_id,
                activate=activate,
            )
            report["models"].append(
                {
                    **artifact,
                    "baseline": result.selection_comparison.get("baseline_name"),
                    "winner": result.selected_candidate,
                    "selection_comparison": result.selection_comparison,
                    "validation_strategy": result.validation_strategy,
                }
            )
            report["validation_strategies_used"].append(result.validation_strategy)
        except PropertySkippedError as exc:
            report["skipped_properties"].append(
                {
                    "property_id": property_id,
                    "target": target,
                    "reason": str(exc),
                }
            )
            report["skipped"].append({"model": label, "reason": str(exc)})
            if skipped_properties is not None:
                skipped_properties.add(property_id)
                raise _StopProperty() from exc
        except ModelTrainingError as exc:
            report["skipped"].append({"model": label, "reason": str(exc)})
        except Exception as exc:
            report["errors"].append({"model": label, "reason": str(exc)})

    @staticmethod
    def _stage(callback, message: str) -> None:
        if callback:
            callback(message)

    @staticmethod
    def _stage_eval(report: dict[str, Any]) -> None:
        # marker for reports; stage_callback handled by caller loops
        report.setdefault("_eval_ticks", 0)
        report["_eval_ticks"] += 1


class _StopProperty(Exception):
    """Internal control flow for skip_property policy in train-all loops."""


def resolve_paths_relative_to_config(config: dict[str, Any], config_path: str | Path) -> dict[str, Any]:
    """Compatibility wrapper; path resolution lives in model_training_service.config."""
    from model_training_service.config import resolve_paths_relative_to_config as _resolve

    return _resolve(config, config_path)
