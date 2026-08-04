"""Pytest: expõe a raiz do repositório como pacote ``wrappers``."""

from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class _WrappersAliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path, target=None):  # noqa: ANN001
        if fullname != "wrappers" and not fullname.startswith("wrappers."):
            return None
        if fullname == "wrappers":
            init = SERVICE_ROOT / "__init__.py"
            return importlib.util.spec_from_file_location(
                fullname,
                init,
                submodule_search_locations=[str(SERVICE_ROOT)],
            )
        relative = fullname.removeprefix("wrappers.")
        py_file = SERVICE_ROOT / f"{relative.replace('.', '/')}.py"
        if py_file.is_file():
            return importlib.util.spec_from_file_location(fullname, py_file)
        pkg_dir = SERVICE_ROOT / relative.replace(".", "/")
        init = pkg_dir / "__init__.py"
        if pkg_dir.is_dir() and init.is_file():
            return importlib.util.spec_from_file_location(
                fullname,
                init,
                submodule_search_locations=[str(pkg_dir)],
            )
        return None


if not any(isinstance(f, _WrappersAliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _WrappersAliasFinder())
