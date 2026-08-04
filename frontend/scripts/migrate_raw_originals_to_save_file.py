"""Migra (copia) os originais legados para o serviço save-file.

Copia arquivos e sidecars ``.meta.json`` de ``frontend/data/raw_originals/``
para ``agrotrace-carbon-save-file/data/originals/``, pulando os que já existem.

A cópia é não destrutiva de propósito: os ciclos já persistidos guardam o
``stored_path`` absoluto apontando para o local legado, então mantê-los evita
quebrar a re-execução do wrapper desses ciclos.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from config import RAW_ORIGINALS_DIR, SAVE_FILE_ORIGINALS_DIR, ensure_data_dirs  # noqa: E402


def migrate() -> dict[str, int]:
    ensure_data_dirs()
    copied = 0
    skipped = 0

    if not RAW_ORIGINALS_DIR.exists():
        print(f"Nada a migrar: {RAW_ORIGINALS_DIR} não existe.")
        return {"copied": 0, "skipped": 0}

    for src in RAW_ORIGINALS_DIR.glob("*"):
        if not src.is_file() or src.name == ".gitkeep":
            continue
        dest = SAVE_FILE_ORIGINALS_DIR / src.name
        if dest.exists():
            skipped += 1
            continue
        shutil.copy2(src, dest)
        copied += 1
        print(f"copiado: {src.name}")

    print(f"\nMigração concluída: {copied} copiado(s), {skipped} já existente(s).")
    print(f"Origem : {RAW_ORIGINALS_DIR}")
    print(f"Destino: {SAVE_FILE_ORIGINALS_DIR}")
    return {"copied": copied, "skipped": skipped}


if __name__ == "__main__":
    migrate()
