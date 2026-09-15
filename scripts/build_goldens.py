#!/usr/bin/env python
"""Build golden answers from the frozen DuckDB (no LLM).

Writes:
  - eval/goldens/q1_q15_goldens.json  (Q1–Q15 + Q_REVPAR)
  - eval/goldens/v1_goldens.json      (V1 subset, refreshed)

    python scripts/build_goldens.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tools.analytics.golden_runner import write_all_goldens  # noqa: E402


def main() -> int:
    full, v1 = write_all_goldens()
    print(f"Wrote {full}")
    print(f"Wrote {v1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
