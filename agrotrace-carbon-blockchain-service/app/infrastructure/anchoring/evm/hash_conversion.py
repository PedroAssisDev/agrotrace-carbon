"""Convert official 0x-prefixed SHA-256 hex strings to EVM bytes32."""

from __future__ import annotations


def hex_hash_to_bytes32(hash_value: str) -> bytes:
    """Convert ``0x`` + 64 hex chars directly to 32 bytes (no re-hashing)."""
    if not isinstance(hash_value, str):
        raise ValueError("hash must be a string")
    cleaned = hash_value.lower().strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if len(cleaned) != 64:
        raise ValueError(f"expected 64 hex chars, got {len(cleaned)}")
    try:
        raw = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError("invalid hexadecimal hash") from exc
    if len(raw) != 32:
        raise ValueError("hash must decode to exactly 32 bytes")
    return raw


def bytes32_to_hex(value: bytes | bytearray) -> str:
    if len(value) != 32:
        raise ValueError("bytes32 value must be 32 bytes")
    return "0x" + bytes(value).hex()
