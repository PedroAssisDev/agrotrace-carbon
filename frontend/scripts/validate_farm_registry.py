"""Validação headless do cadastro local de fazendas.

Uso:
    python scripts/validate_farm_registry.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from services.farm_registry_service import (  # noqa: E402
    FarmRegistryError,
    find_by_name,
    list_persisted_properties,
    register_farm,
    resolve_or_register_farm,
)
from services.property_registry import load_property_catalog  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def main() -> int:
    v = Validator()
    print("== AgroTrace Carbon — validação cadastro de fazendas ==")

    with tempfile.TemporaryDirectory() as tmp:
        props_dir = Path(tmp) / "properties"
        props_dir.mkdir(parents=True)
        original = config.PROPERTIES_DIR
        config.PROPERTIES_DIR = props_dir

        try:
            name = "Fazenda Teste Validação"
            entry = register_farm(name, municipality="Uberaba", state="MG", production_type="leite")
            v.check("cadastro persiste json", (props_dir / f"{entry['property_id']}.json").exists())
            v.check("property_id gerado", bool(entry.get("property_id", "").startswith("FARM-")))
            v.check("nome preservado", entry.get("name") == name)

            again = resolve_or_register_farm(name)
            v.check("nome duplicado reutiliza id", again.get("property_id") == entry.get("property_id"))
            v.check("lista persistidos", len(list_persisted_properties()) == 1)

            try:
                register_farm("   ")
                v.check("nome vazio rejeitado", False)
            except FarmRegistryError:
                v.check("nome vazio rejeitado", True)

            found = find_by_name(name.casefold(), catalog=[entry])
            v.check("busca case-insensitive", found is not None and found["property_id"] == entry["property_id"])

            config.PROPERTIES_DIR = original
            catalog = load_property_catalog()
            v.check("catálogo continua listável", isinstance(catalog, list))
        finally:
            config.PROPERTIES_DIR = original

    if v.errors:
        print("\nFarm registry validation: FAIL")
        for err in v.errors:
            print(f"  - {err}")
        return 1

    print("\nFarm registry validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
