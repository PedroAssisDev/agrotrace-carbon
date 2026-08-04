"""Schema e utilitários do manifest de uploads emulados."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EmulatedEntry:
    entry_id: str
    scenario_key: str
    property_id: str
    property_name: str
    data_granularity: str
    period_key: str
    reporting_period: str
    approval_group_key: str
    layout: str
    index: int
    path: str
    filename: str


@dataclass
class EmulatedApprovalGroup:
    cycle_id: str
    scenario_key: str
    property_id: str
    property_name: str
    reporting_period: str
    approval_granularity: str
    data_granularity: str
    layout: str
    approval_group_key: str
    coverage_label: str
    entry_ids: list[str] = field(default_factory=list)
    index: int = 1


@dataclass
class EmulatedFarmMeta:
    property_id: str
    name: str
    municipality: str
    state: str
    production_type: str
    herd_scale: str
    data_quality: str


@dataclass
class EmulatedManifest:
    random_seed: int
    profile_mode: str
    entry_count: int
    approval_group_count: int
    farms: list[EmulatedFarmMeta]
    entries: list[EmulatedEntry]
    approval_groups: list[EmulatedApprovalGroup]

    def to_dict(self) -> dict[str, Any]:
        return {
            "random_seed": self.random_seed,
            "profile_mode": self.profile_mode,
            "entry_count": self.entry_count,
            "approval_group_count": self.approval_group_count,
            "farms": [asdict(f) for f in self.farms],
            "entries": [asdict(e) for e in self.entries],
            "approval_groups": [asdict(g) for g in self.approval_groups],
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> EmulatedManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            random_seed=data["random_seed"],
            profile_mode=data.get("profile_mode", "demo"),
            entry_count=data["entry_count"],
            approval_group_count=data["approval_group_count"],
            farms=[EmulatedFarmMeta(**f) for f in data.get("farms", [])],
            entries=[EmulatedEntry(**e) for e in data.get("entries", [])],
            approval_groups=[
                EmulatedApprovalGroup(**g) for g in data.get("approval_groups", [])
            ],
        )


def default_emulated_dir() -> Path:
    """Pasta canônica: agrotrace-carbon-save-file/data/emulated_uploads/."""
    return Path(__file__).resolve().parents[2] / "data" / "emulated_uploads"
