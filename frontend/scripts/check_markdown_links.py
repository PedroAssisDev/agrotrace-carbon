"""Verificador de links relativos em arquivos Markdown.

Resolve cada link relativo de destino de arquivo/pasta e verifica se existe.
Ignora http(s)/mailto, âncoras puras (#...) e caminhos absolutos.

Uso:
    python frontend/scripts/check_markdown_links.py
    python frontend/scripts/check_markdown_links.py --root docs
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SKIP_PARTS = {".venv", "venv", "node_modules", ".git", "__pycache__", ".pytest_cache", "lib", "out", "cache"}
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")  # [text](target), ignora imagens ![...]
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _skip(path: Path) -> bool:
    return any(p in SKIP_PARTS for p in path.parts)


def _is_external(target: str) -> bool:
    t = target.strip()
    return (
        t.startswith("http://")
        or t.startswith("https://")
        or t.startswith("mailto:")
        or t.startswith("#")
        or t.startswith("<")
    )


def check(root: Path) -> list[tuple[str, int, str]]:
    broken: list[tuple[str, int, str]] = []
    for md in root.rglob("*.md"):
        if _skip(md):
            continue
        lines = md.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines, 1):
            for m in list(LINK_RE.finditer(line)) + list(IMG_RE.finditer(line)):
                target = m.group(1).strip()
                if _is_external(target):
                    continue
                # remove title e âncora
                target = target.split(" ")[0].split("#")[0]
                if not target:
                    continue
                if target.startswith("/"):
                    continue  # caminho absoluto do site; fora do escopo
                # Ignora alvos que não são caminhos de arquivo (ex.: citações/UUID sem
                # separador de diretório nem extensão).
                if "/" not in target and "." not in target:
                    continue
                resolved = (md.parent / target).resolve()
                if not resolved.exists():
                    broken.append((str(md.relative_to(REPO)).replace("\\", "/"), i, target))
    return broken


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica links relativos em Markdown")
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--data-root", type=Path, default=None, help="Ignorado (compat regressão)")
    args = parser.parse_args()
    root = args.root.resolve()
    broken = check(root)
    print(f"=== check_markdown_links === root={root.name}")
    print(f"broken_count={len(broken)}")
    for f, line, target in broken[:200]:
        print(f"  BROKEN {f}:{line} -> {target}")
    if len(broken) > 200:
        print(f"  … truncated ({len(broken) - 200} more)")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
