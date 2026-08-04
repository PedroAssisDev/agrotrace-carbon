"""Erros de dominio do servico save-file (preservacao / recuperacao)."""

from __future__ import annotations


class SaveFileError(Exception):
    """Base para erros de dominio do save-file."""


class ArtifactNotFoundError(SaveFileError):
    """Artefato original nao encontrado no storage root."""


class MetadataNotFoundError(SaveFileError):
    """Sidecar de metadados (.meta.json) ausente ou invalido."""


class StoragePathEscapeError(SaveFileError):
    """Caminho resolvido sai do storage root configurado."""


class IntegrityMismatchError(SaveFileError):
    """Conteudo divergente do SHA-256 registrado nos metadados."""

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
