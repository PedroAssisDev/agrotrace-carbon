#!/usr/bin/env python
"""Compat: use ``python scripts/reset_test_environment.py --confirm``."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).with_name("reset_test_environment.py")
    runpy.run_path(str(target), run_name="__main__")
