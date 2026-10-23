"""Varredura local por padrões de segredo (RNF012).

Nunca imprime o valor encontrado — apenas arquivo, linha e tipo.
Ignora .venv, node_modules, caches e artefatos binários.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIR_NAMES = {
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "out",
    "cache",
    "lib",
    "broadcast",
    "htmlcov",
    ".idea",
    ".vscode",
    ".cursor",
    "data",
    "artifacts",
    # evidence/ is scanned (academic Sepolia artifacts); redacted tokens allowed below
    "contracts",  # Foundry artifacts under contracts/out already covered; skip whole tree for speed
}

# Only scan these extensions
SCAN_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env", ".example", ".sol"}

# Patterns that require credential context (avoid matching SHA-256 hashes)
_CREDENTIAL_KEY_RE = re.compile(
    r"(?i)(private[_-]?key|mnemonic|seed[_-]?phrase|secret[_-]?key|wallet[_-]?key|eth[_-]?key)"
)
_HASH_FIELD_RE = re.compile(
    r"(?i)(package_hash|merkle_root|item_hash|content_hash|sha256|checksum|abi_checksum|"
    r"publication_hash|ontology_hash|preliminary_hash|validation_hash|manifest_hash|"
    r"tx_hash|transaction_hash|block_hash|evidence_key|hash_record)"
)

# Patterns: (tipo, regex) — groups never printed
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_env_assignment", re.compile(r"(?i)(BLOCKCHAIN_.*PRIVATE_KEY|PRIVATE_KEY)\s*=\s*\S+")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*")),
    ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*\S+")),
    ("rpc_url_with_userinfo", re.compile(r"https?://[^/\s]+:[^/@\s]+@[^\s]+")),
    ("infura_alchemy_path_token", re.compile(r"(?i)(infura\.io|alchemy\.com)/v\d+/[A-Za-z0-9_\-]{20,}")),
]

# Contextual: 64-hex only when near a credential key name
_HEX64_RE = re.compile(r"(?:0x)?[a-fA-F0-9]{64}")


def _is_contextual_private_key(line: str) -> bool:
    """True only when 64-hex appears with a credential-like key, not a hash field."""
    if not _HEX64_RE.search(line):
        return False
    if _HASH_FIELD_RE.search(line) and not _CREDENTIAL_KEY_RE.search(line):
        return False
    return bool(_CREDENTIAL_KEY_RE.search(line))


ALLOWLIST_PATH_FRAGMENTS = (
    ".env.example",
    "scan_secrets.py",
    "redact.py",
    "test_redact",
    "test_rnf012",
    "abi_versioning.py",
    # Well-known Anvil account #0 constant documented as local-only
    "app/shared/config.py",
    "app\\shared\\config.py",
    "/docs/",
    "\\docs\\",
    "/tests/",
    "\\tests\\",
    "GUIA_COMPLETO",
    "test_anvil_anchoring",
    "test_evm_hash_conversion",
    "test_validar_sepolia",
    "evm_types.py",  # __repr__ field name only
    # Declared academic evidence (Sepolia validation runs): public addresses +
    # already-redacted RPC tokens (********). Not credentials.
    "evidence/sepolia/",
    "evidence\\sepolia\\",
)


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.startswith(".")


def _is_allowlisted(path: Path) -> bool:
    s = str(path).replace("\\", "/")
    return any(frag.replace("\\", "/") in s for frag in ALLOWLIST_PATH_FRAGMENTS)


def scan_tree(root: Path) -> list[dict]:
    findings: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(_should_skip_dir(p) for p in path.parts):
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES and path.name not in {".env", ".env.example"}:
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            findings.append({
                "file": str(path.relative_to(root)).replace("\\", "/"),
                "line": 0,
                "type": "env_file_present",
                "allowlisted": False,
            })
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if _is_allowlisted(path):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            # Skip obvious documentation placeholders
            if "0000000000000000000000000000000000000000000000000000000000000001" in line:
                continue
            if "example.invalid" in line:
                continue
            # Redacted tokens in academic evidence / logs
            if "********" in line or "/v2/********" in line:
                continue
            for kind, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "file": str(path.relative_to(root)).replace("\\", "/"),
                        "line": i,
                        "type": kind,
                        "allowlisted": False,
                    })
            if _is_contextual_private_key(line):
                findings.append({
                    "file": str(path.relative_to(root)).replace("\\", "/"),
                    "line": i,
                    "type": "private_key_hex",
                    "allowlisted": False,
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan for possible secrets (no values printed)")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    findings = scan_tree(root)
    print(f"=== scan_secrets === root={root.name}")
    print(f"findings_count={len(findings)}")
    for f in findings[:200]:
        print(f"  [{f['type']}] {f['file']}:{f['line']}")
    if len(findings) > 200:
        print(f"  … truncated ({len(findings) - 200} more)")
    # Exit 0 always for inventory; CI may treat count separately
    # Non-zero only if high-confidence leaked env file outside allowlist with key assignment
    critical = [f for f in findings if f["type"] == "env_file_present"]
    if critical:
        print("NOTE: local .env file(s) detected (gitignored). Manual action if ever committed: rotate keys.")
    # Exit 1 only for non-allowlisted assignment/hex outside docs/tests
    blocking = [
        f for f in findings
        if f["type"] in {"private_key_env_assignment", "private_key_hex", "rpc_url_with_userinfo"}
        and not f.get("allowlisted")
    ]
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
