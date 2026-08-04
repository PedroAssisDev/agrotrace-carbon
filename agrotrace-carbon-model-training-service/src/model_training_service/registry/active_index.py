"""Índice de versões ativas (json) — registry.jsonl permanece append-only."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


class ActiveModelIndex:
    def __init__(self, artifacts_root: str | Path) -> None:
        self.root = Path(artifacts_root)
        self.path = self.root / "active_models.json"

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"models": {}}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"models": {}}
        if not isinstance(payload, dict):
            return {"models": {}}
        models = payload.get("models")
        if not isinstance(models, dict):
            return {"models": {}}
        return {"models": models}

    def get(self, logical_key: str) -> dict[str, Any] | None:
        entry = self.read()["models"].get(logical_key)
        return dict(entry) if isinstance(entry, dict) else None

    def set_active(
        self,
        logical_key: str,
        *,
        model_id: str,
        version: str,
        artifact_dir: str,
        training_run_id: str | None = None,
        supersedes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with _LOCK:
            payload = self.read()
            previous = payload["models"].get(logical_key) or {}
            entry = {
                "model_id": model_id,
                "version": version,
                "artifact_dir": artifact_dir,
                "training_run_id": training_run_id,
                "supersedes": supersedes or previous.get("model_id"),
                "status": "active",
            }
            if metadata:
                for key in (
                    "created_at",
                    "selected_candidate",
                    "target",
                    "granularity",
                    "model_family",
                    "property_id",
                ):
                    if key in metadata:
                        entry[key] = metadata[key]
            payload["models"][logical_key] = entry
            self.root.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def clear(self, logical_key: str) -> None:
        with _LOCK:
            payload = self.read()
            if logical_key in payload["models"]:
                del payload["models"][logical_key]
                self.path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
