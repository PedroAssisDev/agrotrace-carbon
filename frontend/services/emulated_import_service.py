"""Importa uploads emulados pela pipeline real do frontend."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import config
from config import LAYOUT_OPTIONS, SAVE_FILE_EMULATED_UPLOADS_DIR, SAVE_FILE_SERVICE_DIR
from services import local_orchestrator as orch
from services.bootstrap import reset_local_data
from services.farm_registry_service import register_farm
from utils.file_helpers import list_cycles, save_cycle

logger = logging.getLogger("agrotrace.emulated_import")


def _ensure_save_file_path() -> None:
    root = str(SAVE_FILE_SERVICE_DIR.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


@dataclass
class ImportResult:
    cycles_created: list[dict] = field(default_factory=list)
    manifest_path: Path | None = None
    entry_count: int = 0
    approval_group_count: int = 0


def _load_manifest_dict(manifest_path: Path | None = None) -> dict[str, Any]:
    _ensure_save_file_path()
    from save_file.emulated.manifest import EmulatedManifest, default_emulated_dir

    path = manifest_path or (SAVE_FILE_EMULATED_UPLOADS_DIR / "manifest.json")
    if not path.exists():
        alt = default_emulated_dir() / "manifest.json"
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(
                f"Manifest não encontrado em {path}. "
                "Execute generate_emulated_uploads.py primeiro."
            )
    return EmulatedManifest.load(path).to_dict()


def _register_farms_from_manifest(manifest: dict[str, Any]) -> None:
    for farm in manifest.get("farms", []):
        register_farm(
            farm["name"],
            property_id=farm.get("property_id"),
            municipality=farm.get("municipality", ""),
            state=farm.get("state", ""),
            production_type=farm.get("production_type"),
        )


def _resolve_entry_path(meta: dict[str, Any], manifest_dir: Path) -> Path:
    raw = meta.get("path") or meta.get("filename", "")
    candidate = Path(raw)
    if candidate.is_file():
        return candidate
    if not candidate.is_absolute():
        resolved = manifest_dir / candidate
        if resolved.is_file():
            return resolved
    filename = meta.get("filename")
    if filename:
        resolved = manifest_dir / filename
        if resolved.is_file():
            return resolved
    raise FileNotFoundError(f"Arquivo emulado não encontrado: {raw} (manifest_dir={manifest_dir})")


def _entry_payloads(
    group: dict[str, Any],
    entries_by_id: dict[str, dict],
    manifest_dir: Path,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for entry_id in group.get("entry_ids", []):
        meta = entries_by_id[entry_id]
        file_path = _resolve_entry_path(meta, manifest_dir)
        payloads.append({
            "entry_id": entry_id,
            "path": str(file_path),
            "reporting_period": meta["reporting_period"],
            "property_id": meta["property_id"],
            "original_filename": meta.get("filename") or file_path.name,
        })
    return payloads


def _layout_id(layout_name: str) -> str:
    if layout_name in LAYOUT_OPTIONS:
        return LAYOUT_OPTIONS[layout_name]
    return f"{layout_name}:v1"


def import_emulated_manifest(
    manifest_path: Path | None = None,
    *,
    wipe_first: bool = False,
    regenerate: bool = True,
    global_seed: int = 42,
    profile_mode: str = "demo",
) -> ImportResult:
    """Fase B: importa manifest emulado pela pipeline até pendência de aprovação."""
    _ensure_save_file_path()
    from save_file.emulated.writer import generate_emulated_uploads

    if wipe_first:
        reset_local_data()

    if regenerate or not (SAVE_FILE_EMULATED_UPLOADS_DIR / "manifest.json").exists():
        generate_emulated_uploads(
            global_seed=global_seed,
            profile_mode=profile_mode,
            output_dir=SAVE_FILE_EMULATED_UPLOADS_DIR,
            wipe=True,
        )

    manifest = _load_manifest_dict(manifest_path)
    path_used = manifest_path or SAVE_FILE_EMULATED_UPLOADS_DIR / "manifest.json"
    manifest_dir = path_used.parent
    _register_farms_from_manifest(manifest)

    entries_by_id = {e["entry_id"]: e for e in manifest.get("entries", [])}
    groups = manifest.get("approval_groups", [])
    created: list[dict] = []

    for group in groups:
        payloads = _entry_payloads(group, entries_by_id, manifest_dir)
        layout_name = group["layout"]
        cycle = orch.run_pipeline_group_until_pending(
            payloads,
            cycle_id=group["cycle_id"],
            property_id=group["property_id"],
            property_name=group["property_name"],
            reporting_period=group["reporting_period"],
            layout_name=layout_name,
            data_granularity=group["data_granularity"],
            approval_granularity=group["approval_granularity"],
            scenario_key=group.get("scenario_key"),
            coverage_label=group.get("coverage_label"),
            layout_id=_layout_id(layout_name),
            frequency=group.get("data_granularity"),
            uploaded_by="emulated-import@agrotrace",
        )
        save_cycle(cycle)
        created.append(cycle)
        logger.info(
            "Importado ciclo %s property=%s status=%s",
            cycle.get("cycle_id"),
            group["property_id"],
            cycle.get("current_status"),
        )

    return ImportResult(
        cycles_created=created,
        manifest_path=path_used,
        entry_count=manifest.get("entry_count", len(entries_by_id)),
        approval_group_count=len(groups),
    )


def list_imported_cycles() -> list[dict]:
    return list_cycles()
