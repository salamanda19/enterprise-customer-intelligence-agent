#!/usr/bin/env python
"""Agent-eval entry gate: refuse to run without full goldens (WP-507).

    python scripts/run_agent_eval.py --dry-gate
    python scripts/run_agent_eval.py   # future: full agent vs goldens (I6)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tools.analytics.golden_runner import ALL_QUESTION_IDS, require_full_goldens  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent eval (gated on full goldens)")
    parser.add_argument(
        "--dry-gate",
        action="store_true",
        help="Only verify goldens exist; do not score an agent yet",
    )
    args = parser.parse_args(argv)

    try:
        path = require_full_goldens()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Goldens OK: {path} ({len(ALL_QUESTION_IDS)} question ids required)")
    if args.dry_gate:
        return 0

    print(
        "Agent scoring vs goldens is I6 (WP-601). "
        "Use --dry-gate until the evaluator lands.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
