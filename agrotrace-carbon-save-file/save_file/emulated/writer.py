"""Grava CSVs emulados e manifest.json."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from save_file.emulated.catalog import get_profiles
from save_file.emulated.manifest import EmulatedFarmMeta
from save_file.emulated.generators.annual import render_annual_csv
from save_file.emulated.generators.intraday import render_intraday_csv
from save_file.emulated.generators.monthly import render_monthly_csv
from save_file.emulated.manifest import (
    EmulatedApprovalGroup,
    EmulatedEntry,
    EmulatedManifest,
    default_emulated_dir,
)
from save_file.emulated.planner import PlannedApprovalGroup, PlannedEntry, plan_all


def _emulated_filename(entry: PlannedEntry) -> str:
    if entry.data_granularity == "monthly":
        return f"emulated_{entry.property_id}_monthly_{entry.period_key}.csv"
    if entry.data_granularity == "annual":
        return f"emulated_{entry.property_id}_annual_{entry.period_key}.csv"
    if entry.data_granularity == "daily":
        return f"emulated_{entry.property_id}_intraday_{entry.period_key}.csv"
    return f"emulated_{entry.property_id}_{entry.entry_id}.csv"


def _render_csv(profile_mode: str, profiles_by_id: dict, entry: PlannedEntry, global_seed: int) -> str:
    profile = profiles_by_id[entry.property_id]
    if entry.layout == "monthly":
        assert entry.year and entry.month
        return render_monthly_csv(
            profile,
            year=entry.year,
            month=entry.month,
            global_seed=global_seed,
            alert_spike=entry.alert_spike,
        )
    if entry.layout == "annual":
        assert entry.year
        return render_annual_csv(profile, year=entry.year, global_seed=global_seed)
    if entry.layout == "intraday":
        assert entry.day
        return render_intraday_csv(profile, day=entry.day, global_seed=global_seed)
    raise ValueError(f"Layout desconhecido: {entry.layout}")


def _wipe_dir(directory: Path) -> None:
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        return
    for path in directory.iterdir():
        if path.name == ".gitkeep":
            continue
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def generate_emulated_uploads(
    *,
    global_seed: int = 42,
    profile_mode: str = "demo",
    output_dir: Path | None = None,
    wipe: bool = True,
) -> dict[str, Any]:
    """Gera arquivos emulados + manifest (Fase A)."""
    out = output_dir or default_emulated_dir()
    if wipe:
        _wipe_dir(out)
    else:
        out.mkdir(parents=True, exist_ok=True)

    profiles, planned_entries, planned_groups = plan_all(profile_mode)
    profiles_by_id = {p.property_id: p for p in profiles}

    manifest_entries: list[EmulatedEntry] = []
    paths: list[Path] = []

    for entry in planned_entries:
        filename = _emulated_filename(entry)
        path = out / filename
        content = _render_csv(profile_mode, profiles_by_id, entry, global_seed)
        path.write_text(content, encoding="utf-8")
        paths.append(path)
        manifest_entries.append(
            EmulatedEntry(
                entry_id=entry.entry_id,
                scenario_key=entry.scenario_key,
                property_id=entry.property_id,
                property_name=entry.property_name,
                data_granularity=entry.data_granularity,
                period_key=entry.period_key,
                reporting_period=entry.reporting_period,
                approval_group_key=entry.approval_group_key,
                layout=entry.layout,
                index=entry.index,
                path=filename,
                filename=filename,
            )
        )

    approval_groups = [
        EmulatedApprovalGroup(
            cycle_id=g.cycle_id,
            scenario_key=g.scenario_key,
            property_id=g.property_id,
            property_name=g.property_name,
            reporting_period=g.reporting_period,
            approval_granularity=g.approval_granularity,
            data_granularity=g.data_granularity,
            layout=g.layout,
            approval_group_key=g.approval_group_key,
            coverage_label=g.coverage_label,
            entry_ids=[e.entry_id for e in g.entries],
            index=g.index,
        )
        for g in planned_groups
    ]

    farm_meta = [
        EmulatedFarmMeta(
            property_id=p.property_id,
            name=p.name,
            municipality=p.municipality,
            state=p.state,
            production_type=p.production_type,
            herd_scale=p.herd_scale,
            data_quality=p.data_quality,
        )
        for p in profiles
    ]

    manifest = EmulatedManifest(
        random_seed=global_seed,
        profile_mode=profile_mode,
        entry_count=len(manifest_entries),
        approval_group_count=len(approval_groups),
        farms=farm_meta,
        entries=manifest_entries,
        approval_groups=approval_groups,
    )
    manifest_path = out / "manifest.json"
    manifest.write(manifest_path)

    return {
        "manifest_path": manifest_path,
        "manifest": manifest,
        "paths": paths,
        "profiles": profiles,
        "planned_entries": planned_entries,
        "planned_groups": planned_groups,
    }
