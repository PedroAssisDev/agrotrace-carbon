"""Proveniência — metadados de origem."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .contracts import ProvenanceMetadata


def build_provenance(
    source_uri: str,
    source_type: str = "csv",
    read_timestamp: datetime | None = None,
    compute_checksum: bool = False,
    file_path: str | Path | None = None,
) -> ProvenanceMetadata:
    ts = read_timestamp or datetime.now(UTC)
    if ts.tzinfo is None:
        read_ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    else:
        read_ts_str = ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    checksum = None
    if compute_checksum and file_path is not None:
        path = Path(file_path)
        if path.exists() and path.is_file():
            try:
                h = hashlib.sha256()
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                checksum = h.hexdigest()
            except OSError:
                pass

    return ProvenanceMetadata(
        source_uri=source_uri,
        source_type=source_type,
        read_timestamp=read_ts_str,
        checksum=checksum,
    )
