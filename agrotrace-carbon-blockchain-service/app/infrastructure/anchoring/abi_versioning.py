"""Resolução e validação de ABI versionada (RNF010)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
LEGACY_ABI_NAME = "CarbonEvidenceRegistry.abi.json"
VERSIONED_ABI_PATTERN = "CarbonEvidenceRegistry.abi.v{version}.json"
_VERSION_IN_NAME = re.compile(r"CarbonEvidenceRegistry\.abi\.v(\d+\.\d+\.\d+)\.json$")


class AbiVersionError(ValueError):
    """ABI path/version/checksum mismatch (mensagem sem segredos)."""


def abi_checksum_sha256(path: Path) -> str:
    raw = path.read_bytes()
    # Prefer checksum of normalized JSON when parseable
    try:
        data = json.loads(raw.decode("utf-8"))
        normalized = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()
    except Exception:
        return hashlib.sha256(raw).hexdigest()


def versioned_abi_filename(contract_version: str) -> str:
    ver = (contract_version or "").strip().lstrip("v")
    if not ver:
        raise AbiVersionError("contract_version is required to resolve ABI")
    return VERSIONED_ABI_PATTERN.format(version=ver)


def resolve_abi_path(
    *,
    contract_version: str | None = None,
    abi_path: Path | None = None,
    contracts_dir: Path | None = None,
) -> Path:
    """Resolve ABI file: explicit path > versioned > legacy."""
    base = contracts_dir or CONTRACTS_DIR
    if abi_path is not None:
        return Path(abi_path)
    if contract_version:
        candidate = base / versioned_abi_filename(contract_version)
        if candidate.exists():
            return candidate
    legacy = base / LEGACY_ABI_NAME
    if legacy.exists():
        return legacy
    raise AbiVersionError("ABI file not found (versioned or legacy)")


def version_from_abi_path(path: Path) -> str | None:
    m = _VERSION_IN_NAME.search(path.name)
    return m.group(1) if m else None


def validate_abi_file(
    path: Path,
    *,
    expected_version: str | None = None,
    expected_checksum: str | None = None,
) -> dict[str, Any]:
    """Load and validate ABI; return metadata (no secret fields)."""
    if not path.exists():
        raise AbiVersionError(f"ABI file not found: {path.name}")
    try:
        abi = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AbiVersionError("ABI JSON is invalid") from exc
    if not isinstance(abi, list):
        raise AbiVersionError("ABI root must be a list")

    file_version = version_from_abi_path(path)
    if expected_version and file_version and file_version != expected_version.lstrip("v"):
        raise AbiVersionError(
            f"ABI version mismatch: file={file_version} expected={expected_version}"
        )

    checksum = abi_checksum_sha256(path)
    if expected_checksum and checksum.lower() != expected_checksum.lower().removeprefix("0x"):
        raise AbiVersionError("ABI checksum mismatch")

    return {
        "path_name": path.name,
        "abi_version": file_version or expected_version,
        "abi_checksum_sha256": checksum,
        "entry_count": len(abi),
        "abi": abi,
    }
