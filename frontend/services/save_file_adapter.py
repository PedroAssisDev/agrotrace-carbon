"""Adapter para o serviço agrotrace-carbon-save-file (chamada direta).

Delega a preservação do dado bruto original ao serviço `save_file`. Se o
serviço não puder ser importado, cai em um fallback local explícito que grava
no mesmo diretório (`SAVE_FILE_ORIGINALS_DIR`), sem quebrar a UI.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from config import SAVE_FILE_ORIGINALS_DIR, SAVE_FILE_SERVICE_DIR, ensure_data_dirs
from utils.date_helpers import now_iso
from utils.hash_helpers import sha256_file
from utils.pipeline_logging import log_call, timed_op, truncate

logger = logging.getLogger("agrotrace.save_file")

_FALLBACK_SOURCE_SYSTEM = "save-file-fallback"
_service_cache: Any = None


def _load_service() -> Any:
    """Importa o módulo `save_file` do serviço, garantindo o path. Cacheia o resultado."""
    global _service_cache
    if _service_cache is not None:
        return _service_cache

    root = str(SAVE_FILE_SERVICE_DIR.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import save_file as _svc  # type: ignore

        _service_cache = _svc
        return _svc
    except Exception as exc:  # noqa: BLE001 — fallback explícito
        logger.warning("save-file service indisponível, usando fallback local: %s", exc)
        return None


def _fallback_metadata(dest: Path, *, original_filename: str, property_id: str, reporting_period: str) -> dict[str, Any]:
    file_hash = sha256_file(dest)
    metadata = {
        "original_filename": original_filename,
        "stored_path": str(dest),
        "file_size_bytes": dest.stat().st_size,
        "file_extension": dest.suffix.lower(),
        "sha256": file_hash,
        "uploaded_at": now_iso(),
        "property_id": property_id,
        "reporting_period": reporting_period,
        "source_system": _FALLBACK_SOURCE_SYSTEM,
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "[SAVE-FILE][fallback] stored property=%s period=%s file=%s sha256=%s…",
        property_id,
        reporting_period,
        dest.name,
        file_hash[:12],
    )
    return metadata


def _fallback_save_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
) -> dict[str, Any]:
    ensure_data_dirs()
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")
    ext = src.suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    dest = SAVE_FILE_ORIGINALS_DIR / f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
    shutil.copy2(src, dest)
    return _fallback_metadata(
        dest,
        original_filename=original_filename or src.name,
        property_id=property_id,
        reporting_period=reporting_period,
    )


def _fallback_save_content(
    content: bytes | str,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str,
) -> dict[str, Any]:
    ensure_data_dirs()
    ext = Path(original_filename).suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    dest = SAVE_FILE_ORIGINALS_DIR / f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
    if isinstance(content, str):
        dest.write_text(content, encoding="utf-8")
    else:
        dest.write_bytes(content)
    return _fallback_metadata(
        dest,
        original_filename=original_filename,
        property_id=property_id,
        reporting_period=reporting_period,
    )


def save_raw_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Preserva o arquivo original via serviço save-file e retorna metadados."""
    ensure_data_dirs()
    name = original_filename or Path(source_path).name
    log_call(
        logger,
        "save_file.start",
        property_id=property_id,
        period=reporting_period,
        file=name,
    )
    with timed_op() as timer:
        svc = _load_service()
        if svc is not None:
            meta = svc.save_original_file(
                source_path,
                property_id=property_id,
                reporting_period=reporting_period,
                original_filename=original_filename,
                dest_dir=SAVE_FILE_ORIGINALS_DIR,
            )
            mode = "real"
        else:
            meta = _fallback_save_file(
                source_path,
                property_id=property_id,
                reporting_period=reporting_period,
                original_filename=original_filename,
            )
            mode = "fallback"
        log_call(
            logger,
            "save_file.done",
            mode=mode,
            property_id=property_id,
            period=reporting_period,
            file=name,
            sha256=truncate(meta.get("sha256")),
            duration_ms=timer.duration_ms,
        )
    return meta


def save_uploaded_content(
    content: bytes | str,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str,
) -> dict[str, Any]:
    """Preserva conteúdo enviado (bytes/str) via serviço save-file."""
    ensure_data_dirs()
    log_call(
        logger,
        "save_content.start",
        property_id=property_id,
        period=reporting_period,
        file=original_filename,
    )
    with timed_op() as timer:
        svc = _load_service()
        if svc is not None:
            meta = svc.save_original_content(
                content,
                property_id=property_id,
                reporting_period=reporting_period,
                original_filename=original_filename,
                dest_dir=SAVE_FILE_ORIGINALS_DIR,
            )
            mode = "real"
        else:
            meta = _fallback_save_content(
                content,
                property_id=property_id,
                reporting_period=reporting_period,
                original_filename=original_filename,
            )
            mode = "fallback"
        log_call(
            logger,
            "save_content.done",
            mode=mode,
            property_id=property_id,
            period=reporting_period,
            file=original_filename,
            sha256=truncate(meta.get("sha256")),
            duration_ms=timer.duration_ms,
        )
    return meta
