"""Carregamento e cache de artefatos de modelo."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

import config
from services.forecast_inference.errors import ArtifactCorruptError, MetadataIncompatibleError


def _ensure_training_service_on_path() -> None:
    """Garante importabilidade das classes serializadas em model.joblib."""
    src = (config.MODEL_TRAINING_SERVICE_DIR / "src").resolve()
    src_s = str(src)
    if src_s not in sys.path:
        sys.path.insert(0, src_s)


@dataclass
class LoadedArtifact:
    entry: dict[str, Any]
    metadata: dict[str, Any]
    metrics: dict[str, Any]
    manifest: dict[str, Any]
    model: Any
    history: pd.DataFrame | None
    artifact_dir: Path


class ArtifactCache:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, float], LoadedArtifact] = {}

    def get(self, key: tuple[str, str, float]) -> LoadedArtifact | None:
        return self._items.get(key)

    def set(self, key: tuple[str, str, float], value: LoadedArtifact) -> None:
        self._items[key] = value

    def clear(self) -> None:
        self._items.clear()


class ModelArtifactLoader:
    def __init__(self, cache: ArtifactCache | None = None) -> None:
        self.cache = cache or ArtifactCache()

    def load(self, entry: dict[str, Any], *, expect_family: str | None = None) -> LoadedArtifact:
        artifact_dir = Path(entry["artifact_dir"])
        model_path = artifact_dir / "model.joblib"
        if not model_path.exists():
            raise ArtifactCorruptError(f"model.joblib ausente em {artifact_dir}")
        mtime = model_path.stat().st_mtime
        version = str(entry.get("version") or "")
        cache_key = (str(artifact_dir.resolve()), version, mtime)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        metadata = _read_json(artifact_dir / "metadata.json")
        metrics = _read_json(artifact_dir / "metrics.json")
        manifest = _read_json(artifact_dir / "dataset_manifest.json")
        self._validate_metadata(entry, metadata, expect_family=expect_family)

        try:
            _ensure_training_service_on_path()
            model = joblib.load(model_path)
        except Exception as exc:  # noqa: BLE001 — erro controlado para a UI
            raise ArtifactCorruptError(f"Falha ao carregar model.joblib: {exc}") from exc

        history = self._load_history(artifact_dir, metadata.get("model_family"))
        loaded = LoadedArtifact(
            entry=entry,
            metadata=metadata,
            metrics=metrics,
            manifest=manifest,
            model=model,
            history=history,
            artifact_dir=artifact_dir,
        )
        self.cache.set(cache_key, loaded)
        return loaded

    def _validate_metadata(
        self,
        entry: dict[str, Any],
        metadata: dict[str, Any],
        *,
        expect_family: str | None,
    ) -> None:
        family = metadata.get("model_family")
        if expect_family and family != expect_family:
            raise MetadataIncompatibleError(
                f"Família esperada {expect_family}, encontrada {family}"
            )
        for key in ("target", "granularity", "version", "model_id"):
            if metadata.get(key) != entry.get(key) and entry.get(key) is not None:
                # Prefer metadata; soft check — fail only on family/target mismatch
                if key in {"target", "granularity"} and metadata.get(key) != entry.get(key):
                    raise MetadataIncompatibleError(
                        f"Inconsistência de {key}: registry={entry.get(key)} metadata={metadata.get(key)}"
                    )
        if family == "regression":
            features = metadata.get("feature_columns") or [
                item.get("name") for item in (metadata.get("feature_schema") or []) if item.get("name")
            ]
            if features != ["lactating_cows"]:
                raise MetadataIncompatibleError(
                    f"Feature schema de regressão inválido: {features}"
                )
            if metadata.get("model_scope") != "global":
                raise MetadataIncompatibleError("Regressão deve ter escopo global")
        if family == "time_series":
            if metadata.get("uses_exogenous_variables"):
                raise MetadataIncompatibleError("Série temporal não pode usar exógenas")
            if int(metadata.get("forecast_horizon", -1)) != 3:
                raise MetadataIncompatibleError(
                    f"Horizonte temporal deve ser 3; encontrado {metadata.get('forecast_horizon')}"
                )
            if metadata.get("model_scope") != "property":
                raise MetadataIncompatibleError("Série temporal deve ter escopo property")

    def _load_history(self, artifact_dir: Path, family: str | None) -> pd.DataFrame | None:
        if family == "regression":
            path = artifact_dir / "training_data.csv"
        elif family == "time_series":
            path = artifact_dir / "training_series.csv"
        else:
            return None
        if not path.exists():
            return None
        try:
            return pd.read_csv(path)
        except Exception:
            return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ArtifactCorruptError(f"Arquivo ausente: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ArtifactCorruptError(f"JSON inválido em {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactCorruptError(f"JSON deve ser objeto: {path}")
    return payload
