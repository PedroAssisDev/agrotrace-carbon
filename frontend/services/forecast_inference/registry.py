"""Leitura e seleção de modelos no registry.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.forecast_inference.errors import (
    ModelNotFoundError,
    RegistryEmptyError,
    RegistryNotFoundError,
)

REQUIRED_ARTIFACT_FILES = ("model.joblib", "metadata.json", "metrics.json", "dataset_manifest.json")


class ModelRegistryReader:
    def __init__(self, registry_path: str | Path, artifacts_root: str | Path | None = None) -> None:
        self.registry_path = Path(registry_path)
        self.artifacts_root = Path(artifacts_root) if artifacts_root else self.registry_path.parent

    def read_all(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            raise RegistryNotFoundError(f"Registry não encontrado: {self.registry_path}")
        entries: list[dict[str, Any]] = []
        with self.registry_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if not payload.get("model_id"):
                    continue
                entries.append(payload)
        if not entries:
            raise RegistryEmptyError(f"Registry vazio ou sem entradas válidas: {self.registry_path}")
        return entries

    def artifact_dir_exists(self, entry: dict[str, Any]) -> bool:
        directory = self._resolve_artifact_dir(entry)
        if directory is None or not directory.is_dir():
            return False
        return all((directory / name).exists() for name in REQUIRED_ARTIFACT_FILES)

    def _resolve_artifact_dir(self, entry: dict[str, Any]) -> Path | None:
        raw = entry.get("artifact_dir")
        if not raw:
            return None
        path = Path(str(raw))
        if path.is_dir():
            return path
        # Fallback: reconstrói a partir do root local (paths absolutos de outra máquina).
        family = entry.get("model_family")
        version = entry.get("version")
        target = entry.get("target")
        granularity = entry.get("granularity")
        if not all([family, version, target, granularity]):
            return None
        if family == "regression":
            candidate = (
                self.artifacts_root
                / "regression"
                / str(granularity)
                / "global"
                / str(target)
                / str(version)
            )
            return candidate if candidate.is_dir() else None
        if family == "time_series":
            property_id = entry.get("property_id") or "unknown"
            slug = _safe_slug(str(property_id))
            candidate = (
                self.artifacts_root
                / "time_series"
                / "monthly"
                / slug
                / str(target)
                / str(version)
            )
            return candidate if candidate.is_dir() else None
        return None

    def find_latest(
        self,
        *,
        model_family: str,
        target: str,
        granularity: str,
        model_scope: str | None = None,
        property_id: str | None = None,
        forecast_horizon: int | None = None,
    ) -> dict[str, Any]:
        matches: list[dict[str, Any]] = []
        for entry in self.read_all():
            if entry.get("model_family") != model_family:
                continue
            if entry.get("target") != target:
                continue
            if entry.get("granularity") != granularity:
                continue
            if model_scope is not None and entry.get("model_scope") != model_scope:
                continue
            entry_property = entry.get("property_id")
            if property_id is None:
                if entry_property not in (None, ""):
                    continue
            else:
                if str(entry_property) != str(property_id):
                    continue
            if forecast_horizon is not None:
                try:
                    if int(entry.get("forecast_horizon", -1)) != int(forecast_horizon):
                        continue
                except (TypeError, ValueError):
                    continue
            if not self.artifact_dir_exists(entry):
                continue
            resolved = self._resolve_artifact_dir(entry)
            enriched = dict(entry)
            enriched["artifact_dir"] = str(resolved)
            matches.append(enriched)
        if not matches:
            raise ModelNotFoundError(
                f"Modelo não encontrado: family={model_family} target={target} "
                f"granularity={granularity} property_id={property_id}"
            )
        # Preferência: índice de versões ativas; fallback: última entrada válida.
        active = self._resolve_active_index(
            model_family=model_family,
            target=target,
            granularity=granularity,
            model_scope=model_scope,
            property_id=property_id,
        )
        if active is not None:
            return active
        return matches[-1]

    def _resolve_active_index(
        self,
        *,
        model_family: str,
        target: str,
        granularity: str,
        model_scope: str | None,
        property_id: str | None,
    ) -> dict[str, Any] | None:
        index_path = self.artifacts_root / "active_models.json"
        if not index_path.exists():
            return None
        try:
            import json

            payload = json.loads(index_path.read_text(encoding="utf-8"))
            models = payload.get("models") or {}
        except Exception:
            return None
        if model_family == "regression":
            key = f"regression|{granularity}|{target}|global"
        else:
            key = f"time_series|monthly|{property_id}|{target}"
        entry = models.get(key)
        if not isinstance(entry, dict):
            return None
        directory = Path(str(entry.get("artifact_dir") or ""))
        if not directory.is_dir() or not (directory / "model.joblib").exists():
            return None
        enriched = dict(entry)
        enriched["artifact_dir"] = str(directory)
        enriched.setdefault("model_family", model_family)
        enriched.setdefault("target", target)
        enriched.setdefault("granularity", granularity)
        enriched.setdefault("model_scope", model_scope or ("global" if model_family == "regression" else "property"))
        enriched.setdefault("property_id", property_id)
        return enriched

    def list_available_summary(self, property_id: str | None = None) -> dict[str, Any]:
        try:
            entries = [e for e in self.read_all() if self.artifact_dir_exists(e)]
        except (RegistryNotFoundError, RegistryEmptyError):
            return {
                "registry_ok": False,
                "regression": {"monthly": {}, "annual": {}},
                "time_series": {},
                "latest_created_at": None,
            }

        regression: dict[str, dict[str, Any]] = {"monthly": {}, "annual": {}}
        time_series: dict[str, Any] = {}
        latest_created: str | None = None
        for entry in entries:
            created = entry.get("created_at")
            if isinstance(created, str) and (latest_created is None or created > latest_created):
                latest_created = created
            family = entry.get("model_family")
            target = entry.get("target")
            gran = entry.get("granularity")
            if family == "regression" and gran in regression and target:
                regression[gran][str(target)] = {
                    "model_id": entry.get("model_id"),
                    "version": entry.get("version"),
                    "selected_candidate": entry.get("selected_candidate"),
                    "created_at": entry.get("created_at"),
                }
            if family == "time_series" and property_id and str(entry.get("property_id")) == str(property_id):
                bucket = time_series.setdefault(str(target), {})
                bucket.update(
                    {
                        "model_id": entry.get("model_id"),
                        "version": entry.get("version"),
                        "selected_candidate": entry.get("selected_candidate"),
                        "created_at": entry.get("created_at"),
                        "forecast_horizon": entry.get("forecast_horizon"),
                    }
                )
        return {
            "registry_ok": True,
            "regression": regression,
            "time_series": time_series,
            "latest_created_at": latest_created,
            "has_any_regression": any(regression["monthly"].values()) or any(regression["annual"].values()),
            "has_property_timeseries": bool(time_series),
        }


def _safe_slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "unknown-property"
