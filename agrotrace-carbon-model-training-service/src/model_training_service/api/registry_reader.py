"""Leitura do registry.jsonl e resolução da versão ativa."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from model_training_service.api.contracts import ModelSlot
from model_training_service.registry.active_index import ActiveModelIndex


class RegistryReader:
    def __init__(self, artifacts_root: str | Path) -> None:
        self.root = Path(artifacts_root)
        self.registry_path = self.root / "registry.jsonl"
        self.active_index = ActiveModelIndex(self.root)

    def read_all(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.registry_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and payload.get("model_id"):
                    entries.append(payload)
        return entries

    def entries_for_slot(self, slot: ModelSlot) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for entry in self.read_all():
            if entry.get("model_family") != slot.family:
                continue
            if entry.get("granularity") != slot.granularity:
                continue
            if entry.get("target") != slot.target:
                continue
            if slot.family == "regression":
                if entry.get("model_scope") not in (None, "global"):
                    continue
                if entry.get("property_id") not in (None, ""):
                    continue
            else:
                if str(entry.get("property_id")) != str(slot.property_id):
                    continue
            directory = Path(str(entry.get("artifact_dir") or ""))
            if not directory.is_dir():
                # fallback relative rebuild
                directory = self._fallback_dir(entry, slot)
                if directory is None or not directory.is_dir():
                    continue
                entry = {**entry, "artifact_dir": str(directory)}
            if not (directory / "model.joblib").exists():
                continue
            matches.append(entry)
        return matches

    def resolve_active(self, slot: ModelSlot) -> dict[str, Any] | None:
        key = slot.logical_key()
        indexed = self.active_index.get(key)
        if indexed:
            directory = Path(str(indexed.get("artifact_dir") or ""))
            if directory.is_dir() and (directory / "model.joblib").exists():
                # enrich from metadata if present
                meta_path = directory / "metadata.json"
                meta: dict[str, Any] = {}
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except Exception:
                        meta = {}
                return {**meta, **indexed, "artifact_dir": str(directory)}
        matches = self.entries_for_slot(slot)
        if not matches:
            return None
        return matches[-1]

    def _fallback_dir(self, entry: dict[str, Any], slot: ModelSlot) -> Path | None:
        version = entry.get("version")
        if not version:
            return None
        if slot.family == "regression":
            return (
                self.root
                / "regression"
                / slot.granularity
                / "global"
                / slot.target
                / str(version)
            )
        from model_training_service.data.dataset_builder import safe_slug

        slug = safe_slug(str(slot.property_id))
        return (
            self.root
            / "time_series"
            / "monthly"
            / slug
            / slot.target
            / str(version)
        )


def load_manifest(artifact_dir: str | Path) -> dict[str, Any]:
    path = Path(artifact_dir) / "dataset_manifest.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_metrics(artifact_dir: str | Path) -> dict[str, Any]:
    path = Path(artifact_dir) / "metrics.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
