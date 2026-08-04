"""RNG reprodutível para geração de dados emulados."""

from __future__ import annotations

import hashlib
import random
from typing import Any


def derive_rng(global_seed: int, *parts: Any) -> random.Random:
    """Deriva um RNG estável a partir do seed global e identificadores locais."""
    payload = "|".join([str(global_seed), *(str(p) for p in parts)])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    local_seed = int(digest[:16], 16)
    return random.Random(local_seed)


def jitter(rng: random.Random, base: float, pct: float = 0.08) -> float:
    """Variação simétrica em torno de base (±pct)."""
    delta = base * pct
    return base + rng.uniform(-delta, delta)


def seasonal_factor(month: int) -> float:
    """Fator sazonal de produção leiteira (pico out–mar no hemisfério sul simplificado)."""
    # Pico em meses 9-12 e 1-3 (Primavera/Verão BR)
    peak_months = {9: 1.08, 10: 1.10, 11: 1.12, 12: 1.10, 1: 1.08, 2: 1.06, 3: 1.04}
    return peak_months.get(month, 0.92 + (month % 4) * 0.02)


def clamp_int(rng: random.Random, base: int, low: int, high: int, noise: int = 2) -> int:
    return max(low, min(high, base + rng.randint(-noise, noise)))
