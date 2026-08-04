"""Geração de dados emulados para pipeline AgroTrace Carbon."""

from __future__ import annotations

from save_file.emulated.catalog import get_profiles
from save_file.emulated.manifest import default_emulated_dir
from save_file.emulated.planner import expected_approval_count, expected_entry_count
from save_file.emulated.validate import validate_emulated_directory
from save_file.emulated.writer import generate_emulated_uploads

__all__ = [
    "default_emulated_dir",
    "expected_approval_count",
    "expected_entry_count",
    "generate_emulated_uploads",
    "get_profiles",
    "validate_emulated_directory",
]
