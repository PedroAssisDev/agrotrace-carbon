"""Persistência de arquivos brutos e ciclos no protótipo."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from config import CYCLES_DIR, RAW_ORIGINALS_DIR, ensure_data_dirs
from utils.date_helpers import now_iso
from utils.hash_helpers import sha256_file


def save_raw_file(
    source_path: str | Path,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Salva cópia do arquivo original em pasta controlada e retorna metadados."""
    ensure_data_dirs()
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {src}")

    name = original_filename or src.name
    ext = src.suffix.lower()
    safe_period = reporting_period.replace("/", "_").replace("\\", "_")
    stored_name = f"{property_id}_{safe_period}_{uuid.uuid4().hex[:8]}{ext}"
    dest = RAW_ORIGINALS_DIR / stored_name
    shutil.copy2(src, dest)

    file_hash = sha256_file(dest)
    metadata = {
        "original_filename": name,
        "stored_path": str(dest),
        "file_size_bytes": dest.stat().st_size,
        "file_extension": ext,
        "sha256": file_hash,
        "uploaded_at": now_iso(),
        "property_id": property_id,
        "reporting_period": reporting_period,
    }

    meta_path = dest.with_suffix(dest.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return metadata


def save_uploaded_content(
    content: bytes | str,
    *,
    property_id: str,
    reporting_period: str,
    original_filename: str,
) -> dict[str, Any]:
    """Salva conteúdo enviado via upload do Dash."""
    ensure_data_dirs()
    dest = RAW_ORIGINALS_DIR / f"{property_id}_{reporting_period}_{uuid.uuid4().hex[:8]}_{original_filename}"
    if isinstance(content, str):
        dest.write_text(content, encoding="utf-8")
    else:
        dest.write_bytes(content)
    return save_raw_file(dest, property_id=property_id, reporting_period=reporting_period, original_filename=original_filename)


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Salva dict como JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    """Carrega JSON ou retorna dict vazio."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def list_cycles() -> list[dict[str, Any]]:
    """Lista todos os ciclos salvos."""
    ensure_data_dirs()
    cycles = []
    for f in sorted(CYCLES_DIR.glob("*.json"), reverse=True):
        try:
            cycles.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return cycles


def save_cycle(cycle: dict[str, Any]) -> str:
    """Persiste ciclo e retorna cycle_id."""
    ensure_data_dirs()
    cycle_id = cycle.get("cycle_id") or f"CYCLE-{uuid.uuid4().hex[:12]}"
    cycle["cycle_id"] = cycle_id
    cycle["updated_at"] = now_iso()
    path = CYCLES_DIR / f"{cycle_id}.json"
    # Não persiste chaves privadas (ex.: objeto de ontologia não serializável)
    serializable = {k: v for k, v in cycle.items() if not k.startswith("_")}
    save_json(path, serializable)
    return cycle_id


def get_cycle(cycle_id: str) -> dict[str, Any] | None:
    """Carrega ciclo por ID."""
    path = CYCLES_DIR / f"{cycle_id}.json"
    if not path.exists():
        return None
    return load_json(path)


def get_active_cycle() -> dict[str, Any] | None:
    """Retorna o ciclo mais recente não verificado ou o mais recente."""
    cycles = list_cycles()
    if not cycles:
        return None
    for c in cycles:
        ver_status = (c.get("steps") or {}).get("verification", {}).get("status")
        if ver_status not in ("VERIFIED", "DIVERGENT") and c.get("status") not in ("VERIFIED", "VERIFICATION_FAILED"):
            return c
    return cycles[0]
