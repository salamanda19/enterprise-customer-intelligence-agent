#!/usr/bin/env python
"""Rebuild the synthetic DuckDB world and lock high-value threshold (I2).

Usage (from repo root, after `pip install -e .`):

    python scripts/rebuild_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecia.data.generate import DEFAULT_DB_PATH, generate, lock_high_value_threshold  # noqa: E402


def main() -> int:
    stats = generate()
    assert stats.high_value_threshold is not None
    lock_high_value_threshold(stats.high_value_threshold)
    print(f"Wrote {DEFAULT_DB_PATH}")
    print(f"members={stats.members} wallet_cash_total={stats.wallet_cash_total:.2f}")
    print(f"locked high_value_threshold={int(stats.high_value_threshold)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
