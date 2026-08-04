"""Redação de segredos para logs, exceções e relatórios.

Nunca registre ou retorne valores reais de chaves/tokens — apenas máscaras.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SECRET_KEY_PATTERN = re.compile(
    r"(PRIVATE_KEY|PRIVKEY|MNEMONIC|SECRET|TOKEN|API_KEY|PASSWORD|"
    r"AUTHORIZATION|BEARER|RPC_URL|raw_transaction|signed)",
    re.IGNORECASE,
)

_HEX_KEY_RE = re.compile(r"0x[a-fA-F0-9]{64}")
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*")
_AUTH_HEADER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)")
_MNEMONIC_HINT_RE = re.compile(
    r"(?i)\b([a-z]+\s+){11,23}[a-z]+\b",
)


def redact_secret(value: str | None) -> str:
    if value is None or value == "":
        return "(vazio)"
    if len(value) <= 8:
        return "********"
    return value[:4] + "********" + value[-4:]


def sanitize_rpc_url(url: str | None) -> str:
    if not url:
        return "(ausente)"
    try:
        parts = urlsplit(url)
        # Strip userinfo credentials from netloc
        netloc = parts.netloc
        if "@" in netloc:
            netloc = "********@" + netloc.split("@", 1)[-1]
        path = parts.path or ""
        if "/v2/" in path or "/v3/" in path or len(path) > 20:
            segments = path.strip("/").split("/")
            if len(segments) >= 2:
                segments[-1] = "********"
                path = "/" + "/".join(segments)
            else:
                path = "/********"
        elif path and path != "/":
            path = "/********"
        query = "********" if parts.query else ""
        return urlunsplit((parts.scheme, netloc, path, query, ""))
    except Exception:
        return "https://********"


def redact_text(text: str | None) -> str:
    """Mascara padrões sensíveis em texto livre (logs / exceções)."""
    if not text:
        return ""
    out = _HEX_KEY_RE.sub("0x********", text)
    out = _BEARER_RE.sub(r"\1********", out)
    out = _AUTH_HEADER_RE.sub(r"\1********", out)
    return out


def sanitize_mapping(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key)
        if SECRET_KEY_PATTERN.search(key_str):
            if "RPC" in key_str.upper() and isinstance(value, str):
                result[key_str] = sanitize_rpc_url(value)
            else:
                result[key_str] = "********"
        elif isinstance(value, dict):
            result[key_str] = sanitize_mapping(value)
        elif isinstance(value, list):
            result[key_str] = [
                sanitize_mapping(item) if isinstance(item, dict) else (
                    redact_text(item) if isinstance(item, str) else item
                )
                for item in value
            ]
        elif isinstance(value, str):
            low = value.lower()
            if "://" in value and ("@" in value or "alchemy.com" in low or "infura.io" in low):
                result[key_str] = sanitize_rpc_url(value)
            elif _HEX_KEY_RE.fullmatch(value.strip()) or value.strip().startswith("0x") and len(value.strip()) >= 66:
                result[key_str] = redact_secret(value)
            else:
                result[key_str] = redact_text(value)
        else:
            result[key_str] = value
    return result


def safe_error_message(exc: BaseException, *, max_len: int = 240) -> str:
    msg = redact_text(f"{type(exc).__name__}: {exc}")
    if len(msg) > max_len:
        return msg[:max_len] + "…"
    return msg
