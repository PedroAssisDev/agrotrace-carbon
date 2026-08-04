"""Adapter para o serviço agrotrace-carbon-save-file (chamada direta).

Delega a preservação e recuperação do dado bruto original ao serviço
`save_file`. Se o serviço não puder ser importado, cai em um fallback local
explícito no mesmo diretório (`SAVE_FILE_ORIGINALS_DIR`), sem quebrar a UI.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

import config
from utils.date_helpers import now_iso
from utils.hash_helpers import sha256_bytes, sha256_file
from utils.pipeline_logging import log_call, timed_op, truncate

logger = logging.getLogger("agrotrace.save_file")

_FALLBACK_SOURCE_SYSTEM = "save-file-fallback"
_META_SUFFIX = ".meta.json"
_service_cache: Any = None


class SaveFileAdapterError(Exception):
    """Base para erros de recuperação via adapter."""


class ArtifactNotFoundError(SaveFileAdapterError):
    """Artefato original não encontrado."""


class MetadataNotFoundError(SaveFileAdapterError):
    """Metadados do artefato ausentes ou inválidos."""


class StoragePathEscapeError(SaveFileAdapterError):
    """Caminho resolvido sai do storage root."""


class IntegrityMismatchError(SaveFileAdapterError):
    """Conteúdo diverge do SHA-256 registrado."""

    def __init__(
        self,
        message: str,
        *,
        registered_sha256: str | None = None,
        recomputed_sha256: str | None = None,
    ) -> None:
        super().__init__(message)
        self.registered_sha256 = registered_sha256
        self.recomputed_sha256 = recomputed_sha256


def _load_service() -> Any:
    """Importa o módulo `save_file` do serviço, garantindo o path. Cacheia o resultado."""
    global _service_cache
    if _service_cache is not None:
        return _service_cache

    root = str(config.SAVE_FILE_SERVICE_DIR.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        import save_file as _svc  # type: ignore

        _service_cache = _svc
        return _svc
    except Exception as exc:  # noqa: BLE001 — fallback explícito
        logger.warning("save-file service indisponível, usando fallback local: %s", exc)
        return None


def _map_domain_error(exc: Exception) -> Exception:
    """Re-raise erros de domínio do serviço como exceções do adapter (quando tipados)."""
    name = type(exc).__name__
    mapping = {
        "ArtifactNotFoundError": ArtifactNotFoundError,
        "MetadataNotFoundError": MetadataNotFoundError,
        "StoragePathEscapeError": StoragePathEscapeError,
        "IntegrityMismatchError": IntegrityMismatchError,
    }
    target = mapping.get(name)
    if target is None:
        return exc
    if name == "IntegrityMismatchError":
        return target(
            str(exc),
            registered_sha256=getattr(exc, "registered_sha256", None),
            recomputed_sha256=getattr(exc, "recomputed_sha256", None),
        )
    return target(str(exc))


def _fallback_metadata(dest: Path, *, original_filename: str, property_id: str, reporting_period: str) -> dict[str, Any]:
    file_hash = sha256_file(dest)
    artifact_id = str(uuid.uuid4())
    metadata = {
        "artifact_id": artifact_id,
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
    meta_path = dest.with_suffix(dest.suffix + _META_SUFFIX)
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "[SAVE-FILE][fallback] stored property=%s period=%s file=%s artifact_id=%s sha256=%s…",
        property_id,
        reporting_period,
        dest.name,
        artifact_id[:8],
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
    config.ensure_data_dirs()
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")
    ext = src.suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    dest = config.SAVE_FILE_ORIGINALS_DIR / f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
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
    config.ensure_data_dirs()
    ext = Path(original_filename).suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    dest = config.SAVE_FILE_ORIGINALS_DIR / f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
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


def _ensure_within_root(path: Path, root: Path) -> Path:
    root_resolved = root.resolve()
    candidate = path.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise StoragePathEscapeError(f"Caminho fora do storage root: {candidate}") from exc
    return candidate


def _content_type_for(filename: str, extension: str | None) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    ext = (extension or Path(filename).suffix or "").lower()
    if ext == ".csv":
        return "text/csv"
    if ext in {".json", ".geojson"}:
        return "application/json"
    return "application/octet-stream"


def _fallback_retrieve(
    *,
    artifact_id: str | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    """Recuperação local espelhando a API de domínio (sem path do usuário)."""
    key_count = sum(1 for value in (artifact_id, sha256) if value)
    if key_count != 1:
        raise ValueError("Informe exatamente uma chave: artifact_id ou sha256")

    config.ensure_data_dirs()
    root = config.SAVE_FILE_ORIGINALS_DIR.resolve()
    root.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] | None = None
    meta_path: Path | None = None
    needle_id = (artifact_id or "").strip()
    needle_hash = (sha256 or "").lower().strip()

    for candidate in sorted(root.glob(f"*{_META_SUFFIX}")):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if needle_id and str(data.get("artifact_id") or "") == needle_id:
            meta, meta_path = data, candidate
            break
        if needle_hash and str(data.get("sha256") or "").lower() == needle_hash:
            meta, meta_path = data, candidate
            break

    if meta is None or meta_path is None:
        key = f"artifact_id={needle_id}" if needle_id else f"sha256={needle_hash[:12]}…"
        raise ArtifactNotFoundError(f"Artefato não encontrado: {key}")

    stored = meta.get("stored_path")
    if stored:
        artifact_path = Path(str(stored))
        if not artifact_path.is_absolute():
            artifact_path = root / artifact_path
        artifact_path = _ensure_within_root(artifact_path, root)
    else:
        name = meta_path.name
        if not name.endswith(_META_SUFFIX):
            raise MetadataNotFoundError(f"Metadados sem stored_path utilizável: {meta_path.name}")
        artifact_path = _ensure_within_root(meta_path.parent / name[: -len(_META_SUFFIX)], root)

    if not artifact_path.is_file():
        raise ArtifactNotFoundError(f"Arquivo original ausente para {meta_path.name}")

    expected_meta = artifact_path.with_suffix(artifact_path.suffix + _META_SUFFIX)
    if not expected_meta.is_file():
        raise MetadataNotFoundError(f"Metadados não encontrados: {expected_meta.name}")

    content = artifact_path.read_bytes()
    registered = str(meta.get("sha256") or "")
    recomputed = sha256_bytes(content)
    if not registered or registered.lower() != recomputed.lower():
        raise IntegrityMismatchError(
            "Conteúdo diverge do SHA-256 registrado",
            registered_sha256=registered or None,
            recomputed_sha256=recomputed,
        )

    original_filename = str(meta.get("original_filename") or artifact_path.name)
    extension = str(meta.get("file_extension") or artifact_path.suffix.lower() or "")
    return {
        "content": content,
        "original_filename": original_filename,
        "content_type": _content_type_for(original_filename, extension),
        "size": len(content),
        "uploaded_at": str(meta.get("uploaded_at") or ""),
        "cycle_id": None,
        "artifact_id": (str(meta["artifact_id"]) if meta.get("artifact_id") else None),
        "registered_sha256": registered,
        "recomputed_sha256": recomputed,
        "verification_status": "verified",
        "property_id": (str(meta["property_id"]) if meta.get("property_id") else None),
        "reporting_period": (str(meta["reporting_period"]) if meta.get("reporting_period") else None),
        "file_extension": extension or None,
        "source_system": (str(meta["source_system"]) if meta.get("source_system") else None),
    }


def _retrieved_to_dict(result: Any, *, cycle_id: str | None = None) -> dict[str, Any]:
    if isinstance(result, dict):
        data = dict(result)
    elif hasattr(result, "to_safe_dict"):
        data = result.to_safe_dict(include_content=True)
    else:
        data = {
            "content": getattr(result, "content", b""),
            "original_filename": getattr(result, "original_filename", ""),
            "content_type": getattr(result, "content_type", "application/octet-stream"),
            "size": getattr(result, "size", 0),
            "uploaded_at": getattr(result, "uploaded_at", ""),
            "cycle_id": getattr(result, "cycle_id", None),
            "artifact_id": getattr(result, "artifact_id", None),
            "registered_sha256": getattr(result, "registered_sha256", ""),
            "recomputed_sha256": getattr(result, "recomputed_sha256", ""),
            "verification_status": getattr(result, "verification_status", ""),
            "property_id": getattr(result, "property_id", None),
            "reporting_period": getattr(result, "reporting_period", None),
            "file_extension": getattr(result, "file_extension", None),
            "source_system": getattr(result, "source_system", None),
        }
    if cycle_id is not None:
        data["cycle_id"] = cycle_id
    return data


def to_ui_dto(retrieved: dict[str, Any]) -> dict[str, Any]:
    """DTO seguro para a UI — sem caminhos absolutos e sem bytes."""
    return {
        "original_filename": retrieved.get("original_filename"),
        "content_type": retrieved.get("content_type"),
        "tipo": retrieved.get("content_type") or retrieved.get("file_extension"),
        "size": retrieved.get("size"),
        "uploaded_at": retrieved.get("uploaded_at"),
        "cycle_id": retrieved.get("cycle_id"),
        "artifact_id": retrieved.get("artifact_id"),
        "registered_sha256": retrieved.get("registered_sha256"),
        "recomputed_sha256": retrieved.get("recomputed_sha256"),
        "verification_status": retrieved.get("verification_status"),
        "property_id": retrieved.get("property_id"),
        "reporting_period": retrieved.get("reporting_period"),
        "file_extension": retrieved.get("file_extension"),
        "source_system": retrieved.get("source_system"),
    }


def save_raw_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Preserva o arquivo original via serviço save-file e retorna metadados."""
    config.ensure_data_dirs()
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
                dest_dir=config.SAVE_FILE_ORIGINALS_DIR,
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
    config.ensure_data_dirs()
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
                dest_dir=config.SAVE_FILE_ORIGINALS_DIR,
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


def retrieve_original(
    *,
    artifact_id: str | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    """Recupera o bruto por artifact_id ou sha256 (legado), com verificação SHA-256."""
    config.ensure_data_dirs()
    log_call(
        logger,
        "retrieve_original.start",
        artifact_id=truncate(artifact_id),
        sha256=truncate(sha256),
    )
    with timed_op() as timer:
        svc = _load_service()
        try:
            if svc is not None and hasattr(svc, "retrieve_original"):
                result = svc.retrieve_original(
                    artifact_id=artifact_id,
                    sha256=sha256,
                    dest_dir=config.SAVE_FILE_ORIGINALS_DIR,
                )
                data = _retrieved_to_dict(result)
                mode = "real"
            else:
                data = _fallback_retrieve(artifact_id=artifact_id, sha256=sha256)
                mode = "fallback"
        except Exception as exc:  # noqa: BLE001
            mapped = _map_domain_error(exc)
            if mapped is not exc:
                raise mapped from exc
            raise
        log_call(
            logger,
            "retrieve_original.done",
            mode=mode,
            artifact_id=truncate(data.get("artifact_id")),
            sha256=truncate(data.get("registered_sha256")),
            verification=data.get("verification_status"),
            duration_ms=timer.duration_ms,
        )
    return data


def retrieve_by_cycle_id(cycle_id: str) -> dict[str, Any]:
    """Resolve o ciclo, localiza raw_file e recupera o original via domínio save-file."""
    from utils.file_helpers import get_cycle

    cycle = get_cycle(cycle_id)
    if not cycle:
        raise ArtifactNotFoundError(f"Ciclo não encontrado: {cycle_id}")

    raw = cycle.get("raw_file") or {}
    artifact_id = raw.get("artifact_id")
    digest = raw.get("sha256")
    if not artifact_id and not digest:
        raise ArtifactNotFoundError(
            f"Ciclo {cycle_id} sem artifact_id/sha256 em raw_file"
        )

    if artifact_id:
        try:
            data = retrieve_original(artifact_id=str(artifact_id))
        except ArtifactNotFoundError:
            if not digest:
                raise
            data = retrieve_original(sha256=str(digest))
    else:
        data = retrieve_original(sha256=str(digest))

    data["cycle_id"] = cycle_id
    return data
