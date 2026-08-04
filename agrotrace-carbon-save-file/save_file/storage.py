"""Salvamento do dado bruto original (etapas 1-3 do ciclo).

Este servico e o dono da preservacao do arquivo original: grava o arquivo em
pasta controlada dentro do proprio servico, calcula o SHA-256 e produz os
metadados que a etapa de proveniencia precisa (source artifact).

Nao faz ancoragem blockchain nem registra proveniencia: apenas preserva o
arquivo e devolve os metadados para quem observa/registra o ciclo.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from save_file.hashing import sha256_file

logger = logging.getLogger("agrotrace.save_file")

SOURCE_SYSTEM = "save-file-service"


def default_originals_dir() -> Path:
    """Pasta padrao de originais, dentro do proprio servico."""
    return Path(__file__).resolve().parents[1] / "data" / "originals"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_dir(dest_dir: str | Path | None) -> Path:
    target = Path(dest_dir) if dest_dir is not None else default_originals_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target


def _build_metadata(dest: Path, *, original_filename: str, property_id: str, reporting_period: str) -> dict[str, Any]:
    file_hash = sha256_file(dest)
    metadata = {
        "original_filename": original_filename,
        "stored_path": str(dest),
        "file_size_bytes": dest.stat().st_size,
        "file_extension": dest.suffix.lower(),
        "sha256": file_hash,
        "uploaded_at": _now_iso(),
        "property_id": property_id,
        "reporting_period": reporting_period,
        "source_system": SOURCE_SYSTEM,
    }
    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "[SAVE-FILE] stored property=%s period=%s file=%s sha256=%s…",
        property_id,
        reporting_period,
        dest.name,
        file_hash[:12],
    )
    return metadata


def save_original_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
    dest_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Copia o arquivo original para pasta controlada e devolve metadados.

    Retorna dict com: original_filename, stored_path, file_size_bytes,
    file_extension, sha256, uploaded_at, property_id, reporting_period,
    source_system — tudo o que a etapa de proveniencia precisa.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {src}")

    target_dir = _resolve_dir(dest_dir)
    name = original_filename or src.name
    ext = src.suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    stored_name = f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
    dest = target_dir / stored_name
    shutil.copy2(src, dest)

    return _build_metadata(
        dest,
        original_filename=name,
        property_id=property_id,
        reporting_period=reporting_period,
    )


def save_original_content(
    content: bytes | str,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str,
    dest_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Grava conteudo enviado (bytes/str) direto na pasta controlada."""
    target_dir = _resolve_dir(dest_dir)
    ext = Path(original_filename).suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    stored_name = f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
    dest = target_dir / stored_name

    if isinstance(content, str):
        dest.write_text(content, encoding="utf-8")
    else:
        dest.write_bytes(content)

    return _build_metadata(
        dest,
        original_filename=original_filename,
        property_id=property_id,
        reporting_period=reporting_period,
    )
