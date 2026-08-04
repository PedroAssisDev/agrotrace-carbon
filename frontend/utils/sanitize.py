"""Sanitização de payloads para exibição em auditoria (sem paths/segredos)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SECRET_FRAGMENTS = (
    "private_key",
    "privkey",
    "rpc",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
)

_ABS_PATH_RE = re.compile(
    r"(^[A-Za-z]:\\)|(^/)|(\\Users\\)|(/home/)|(/var/)|(/tmp/)",
    re.IGNORECASE,
)

_PATH_KEYS = frozenset({
    "stored_path",
    "path",
    "file_path",
    "filepath",
    "absolute_path",
    "db_path",
    "working_ontology_path",
    "published_ontology_path",
    "export_path",
    "storage_uri",
    "normalized_file",
    "raw_file_path",
    "ontology_path",
    "ttl_path",
})

_REPO_REL_PATH_RE = re.compile(
    r"(frontend[/\\]data[/\\])|(agrotrace-data[/\\])|(raw_originals[/\\])|(normalized[/\\])",
    re.IGNORECASE,
)


def looks_like_absolute_path(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < 3:
        return False
    if _ABS_PATH_RE.search(value):
        return True
    if _REPO_REL_PATH_RE.search(value) and ("/" in value or "\\" in value):
        return True
    try:
        p = Path(value)
        return p.is_absolute()
    except Exception:
        return False


def is_secret_key(key: str) -> bool:
    lk = str(key).lower()
    return any(frag in lk for frag in _SECRET_FRAGMENTS)


def sanitize_for_display(data: Any, *, max_depth: int = 8) -> Any:
    """Remove caminhos absolutos e chaves sensíveis de estruturas aninhadas."""
    if max_depth < 0:
        return "[truncated]"
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            ks = str(k)
            lk = ks.lower()
            if is_secret_key(ks) or lk in _PATH_KEYS:
                if lk in {
                    "stored_path",
                    "path",
                    "file_path",
                    "filepath",
                    "normalized_file",
                    "raw_file_path",
                } and isinstance(v, str) and v:
                    out["file_name"] = Path(v.replace("\\", "/")).name
                continue
            if isinstance(v, str) and looks_like_absolute_path(v):
                out[ks] = Path(v.replace("\\", "/")).name
                continue
            out[ks] = sanitize_for_display(v, max_depth=max_depth - 1)
        return out
    if isinstance(data, list):
        return [sanitize_for_display(x, max_depth=max_depth - 1) for x in data[:200]]
    if isinstance(data, str) and looks_like_absolute_path(data):
        return Path(data.replace("\\", "/")).name
    return data


def safe_error_message(exc: BaseException) -> str:
    msg = str(exc)
    if looks_like_absolute_path(msg):
        # remove segmentos de path
        msg = re.sub(r"[A-Za-z]:\\[^\s]+", "[path]", msg)
        msg = re.sub(r"(/[^\s]+)+", "[path]", msg)
    return msg[:400]
