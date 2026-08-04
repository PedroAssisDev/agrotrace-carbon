"""Salvamento e recuperacao do dado bruto original (etapas 1-3 do ciclo).

Este servico e o dono da preservacao do arquivo original: grava o arquivo em
pasta controlada dentro do proprio servico, calcula o SHA-256 e produz os
metadados que a etapa de proveniencia precisa (source artifact).

Nao faz ancoragem blockchain nem registra proveniencia: apenas preserva o
arquivo e devolve os metadados para quem observa/registra o ciclo.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from save_file.errors import (
    ArtifactNotFoundError,
    IntegrityMismatchError,
    MetadataNotFoundError,
    StoragePathEscapeError,
)
from save_file.hashing import sha256_bytes, sha256_file
from save_file.models import RetrievedOriginal

logger = logging.getLogger("agrotrace.save_file")

SOURCE_SYSTEM = "save-file-service"
_META_SUFFIX = ".meta.json"


def default_originals_dir() -> Path:
    """Pasta padrao de originais.

    Com ``AGROTRACE_DATA_ROOT``: ``{root}/save_file/originals`` (mesmo contrato do frontend).
    Sem root: ``{save-file}/data/originals`` (comportamento local legado).
    """
    import os

    raw = os.environ.get("AGROTRACE_DATA_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve() / "save_file" / "originals"
    return Path(__file__).resolve().parents[1] / "data" / "originals"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_dir(dest_dir: str | Path | None) -> Path:
    target = Path(dest_dir) if dest_dir is not None else default_originals_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


def _meta_path_for(artifact_path: Path) -> Path:
    return artifact_path.with_suffix(artifact_path.suffix + _META_SUFFIX)


def _ensure_within_root(path: Path, root: Path) -> Path:
    """Garante que ``path`` resolvido permanece sob ``root``."""
    root_resolved = root.resolve()
    candidate = path.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise StoragePathEscapeError(
            f"Caminho fora do storage root: {candidate}"
        ) from exc
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


def _load_meta_json(meta_path: Path, root: Path) -> dict[str, Any]:
    meta_path = _ensure_within_root(meta_path, root)
    if not meta_path.is_file():
        raise MetadataNotFoundError(f"Metadados nao encontrados: {meta_path.name}")
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataNotFoundError(f"Metadados invalidos: {meta_path.name}") from exc
    if not isinstance(data, dict):
        raise MetadataNotFoundError(f"Metadados invalidos: {meta_path.name}")
    return data


def _iter_meta_files(root: Path):
    for path in sorted(root.glob(f"*{_META_SUFFIX}")):
        if path.is_file():
            yield path


def _find_meta_by_artifact_id(root: Path, artifact_id: str) -> tuple[Path, dict[str, Any]]:
    for meta_path in _iter_meta_files(root):
        try:
            meta = _load_meta_json(meta_path, root)
        except (MetadataNotFoundError, StoragePathEscapeError):
            continue
        if str(meta.get("artifact_id") or "") == artifact_id:
            return meta_path, meta
    raise ArtifactNotFoundError(f"Artefato nao encontrado: artifact_id={artifact_id}")


def _find_meta_by_sha256(root: Path, digest: str) -> tuple[Path, dict[str, Any]]:
    needle = digest.lower().strip()
    for meta_path in _iter_meta_files(root):
        try:
            meta = _load_meta_json(meta_path, root)
        except (MetadataNotFoundError, StoragePathEscapeError):
            continue
        if str(meta.get("sha256") or "").lower() == needle:
            return meta_path, meta
    raise ArtifactNotFoundError(f"Artefato nao encontrado: sha256={digest[:12]}…")


def _resolve_artifact_path(meta: dict[str, Any], meta_path: Path, root: Path) -> Path:
    """Resolve o arquivo de conteudo a partir dos metadados, sem aceitar path do usuario."""
    stored = meta.get("stored_path")
    if stored:
        candidate = Path(str(stored))
        if not candidate.is_absolute():
            candidate = root / candidate
        return _ensure_within_root(candidate, root)

    # Sidecar padrao: arquivo.ext.meta.json → arquivo.ext
    name = meta_path.name
    if name.endswith(_META_SUFFIX):
        artifact_name = name[: -len(_META_SUFFIX)]
        return _ensure_within_root(meta_path.parent / artifact_name, root)

    raise MetadataNotFoundError(f"Metadados sem stored_path utilizavel: {meta_path.name}")


def _build_metadata(dest: Path, *, original_filename: str, property_id: str, reporting_period: str) -> dict[str, Any]:
    file_hash = sha256_file(dest)
    artifact_id = str(uuid.uuid4())
    metadata = {
        "artifact_id": artifact_id,
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
    meta_path = _meta_path_for(dest)
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "[SAVE-FILE] stored property=%s period=%s file=%s artifact_id=%s sha256=%s…",
        property_id,
        reporting_period,
        dest.name,
        artifact_id[:8],
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

    Retorna dict com: artifact_id, original_filename, stored_path, file_size_bytes,
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


def retrieve_original(
    *,
    artifact_id: str | None = None,
    sha256: str | None = None,
    dest_dir: str | Path | None = None,
) -> RetrievedOriginal:
    """Recupera o artefato bruto por ``artifact_id`` ou ``sha256`` (legado).

    Nao aceita caminho arbitrario do chamador. Localiza o sidecar no storage
    root, valida containment, le os bytes e verifica o SHA-256 registrado.
    """
    key_count = sum(1 for value in (artifact_id, sha256) if value)
    if key_count != 1:
        raise ValueError("Informe exatamente uma chave: artifact_id ou sha256")

    root = _resolve_dir(dest_dir)

    if artifact_id:
        meta_path, meta = _find_meta_by_artifact_id(root, str(artifact_id).strip())
    else:
        meta_path, meta = _find_meta_by_sha256(root, str(sha256).strip())

    artifact_path = _resolve_artifact_path(meta, meta_path, root)
    if not artifact_path.is_file():
        # Arquivo sumiu mas meta existe → trate como artefato ausente
        raise ArtifactNotFoundError(f"Arquivo original ausente para {meta_path.name}")

    # Se o sidecar esperado junto ao arquivo nao existir, erro de metadados
    expected_meta = _meta_path_for(artifact_path)
    if not expected_meta.is_file():
        raise MetadataNotFoundError(f"Metadados nao encontrados: {expected_meta.name}")

    content = artifact_path.read_bytes()
    registered = str(meta.get("sha256") or "")
    recomputed = sha256_bytes(content)
    if not registered or registered.lower() != recomputed.lower():
        raise IntegrityMismatchError(
            "Conteudo diverge do SHA-256 registrado",
            registered_sha256=registered or None,
            recomputed_sha256=recomputed,
        )

    original_filename = str(meta.get("original_filename") or artifact_path.name)
    extension = str(meta.get("file_extension") or artifact_path.suffix.lower() or "")
    return RetrievedOriginal(
        content=content,
        original_filename=original_filename,
        content_type=_content_type_for(original_filename, extension),
        size=len(content),
        uploaded_at=str(meta.get("uploaded_at") or ""),
        cycle_id=None,
        artifact_id=(str(meta["artifact_id"]) if meta.get("artifact_id") else None),
        registered_sha256=registered,
        recomputed_sha256=recomputed,
        verification_status="verified",
        property_id=(str(meta["property_id"]) if meta.get("property_id") else None),
        reporting_period=(str(meta["reporting_period"]) if meta.get("reporting_period") else None),
        file_extension=extension or None,
        source_system=(str(meta["source_system"]) if meta.get("source_system") else None),
    )
