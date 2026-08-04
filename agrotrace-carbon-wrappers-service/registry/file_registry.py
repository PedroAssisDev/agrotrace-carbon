"""
Layout Registry baseado em arquivos — descobre layout.yaml em layouts/<family>/v<version>/
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from .layout_definition import LayoutDefinition

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Instale PyYAML: pip install pyyaml"
    ) from e


def _layouts_root(package_dir: Path | None = None) -> Path:
    if package_dir is None:
        package_dir = Path(__file__).resolve().parent.parent
    return package_dir / "layouts"


class LayoutRegistry:
    """Carrega e indexa definições de layout por layout_id."""

    def __init__(self, layouts_root: Path | None = None):
        self._root = layouts_root or _layouts_root()
        self._by_id: dict[str, dict[str, Any]] = {}
        self._path_by_id: dict[str, Path] = {}
        self._discover()

    def _discover(self) -> None:
        if not self._root.exists():
            return
        for layout_yaml in self._root.rglob("layout.yaml"):
            doc = self._load_yaml(layout_yaml)
            lid = doc.get("layout_id")
            if lid:
                key = str(lid)
                if key in self._by_id:
                    logger.warning(
                        "layout_id duplicado %r: %s substitui definição anterior em %s",
                        key,
                        layout_yaml,
                        self._path_by_id.get(key),
                    )
                self._by_id[key] = doc
                self._path_by_id[key] = layout_yaml.parent

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Layout inválido (não é dict): {path}")
        return data

    def get(self, layout_id: str) -> dict[str, Any]:
        if layout_id not in self._by_id:
            raise KeyError(f"Layout não registrado: {layout_id}. Disponíveis: {sorted(self._by_id)}")
        return self._by_id[layout_id]

    def get_definition(self, layout_id: str) -> LayoutDefinition:
        """Metadados do layout (id, família, versão) — extensão do catálogo sem acoplar ao YAML bruto."""
        return LayoutDefinition.from_doc(self.get(layout_id))

    def layout_directory(self, layout_id: str) -> Path:
        return self._path_by_id[layout_id]

    def list_layout_ids(self) -> list[str]:
        return sorted(self._by_id.keys())

    def list_definitions(self) -> list[LayoutDefinition]:
        """Catálogo de metadados (sem o YAML completo) — útil para descoberta e UIs."""
        return [LayoutDefinition.from_doc(self._by_id[lid]) for lid in sorted(self._by_id)]

    def source_schema_fingerprint(self, layout_id: str) -> str:
        """Hash do documento do layout (governança / source_schema_version)."""
        raw = json.dumps(self.get(layout_id), sort_keys=True, default=str).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()[:16]


def default_registry() -> LayoutRegistry:
    return LayoutRegistry()
