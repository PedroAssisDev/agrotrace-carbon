"""Servico save-file: preservacao do dado bruto original.

Responsavel pelas etapas 1-3 do ciclo (salvar arquivo original, calcular
SHA-256 e produzir os metadados de source artifact para a proveniencia).
Integracao por chamada direta a funcao — sem HTTP.
"""

from __future__ import annotations

from save_file.errors import (
    ArtifactNotFoundError,
    IntegrityMismatchError,
    MetadataNotFoundError,
    SaveFileError,
    StoragePathEscapeError,
)
from save_file.hashing import sha256_bytes, sha256_file
from save_file.models import RetrievedOriginal
from save_file.storage import (
    SOURCE_SYSTEM,
    default_originals_dir,
    retrieve_original,
    save_original_content,
    save_original_file,
)

try:
    from save_file.emulated import (
        default_emulated_dir,
        generate_emulated_uploads,
        validate_emulated_directory,
    )
except ImportError:  # pragma: no cover
    default_emulated_dir = None  # type: ignore[misc, assignment]
    generate_emulated_uploads = None  # type: ignore[misc, assignment]
    validate_emulated_directory = None  # type: ignore[misc, assignment]

__all__ = [
    "ArtifactNotFoundError",
    "IntegrityMismatchError",
    "MetadataNotFoundError",
    "RetrievedOriginal",
    "SOURCE_SYSTEM",
    "SaveFileError",
    "StoragePathEscapeError",
    "default_emulated_dir",
    "default_originals_dir",
    "generate_emulated_uploads",
    "retrieve_original",
    "save_original_content",
    "save_original_file",
    "sha256_bytes",
    "sha256_file",
    "validate_emulated_directory",
]
