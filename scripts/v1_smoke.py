#!/usr/bin/env python
"""V1 smoke: optional DB rebuild, goldens check, 3 CLI asks.

Default skips rebuild (weak machines). Force with --rebuild.

    python scripts/v1_smoke.py
    python scripts/v1_smoke.py --rebuild
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild DuckDB (slow). Default: reuse frozen DB.",
    )
    args = parser.parse_args()

    if args.rebuild:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "rebuild_db.py")])
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_goldens.py")])

    db = ROOT / "data" / "synthetic" / "generated" / "ir01.duckdb"
    if not db.exists():
        print("Missing frozen DB. Run: python scripts/rebuild_db.py", file=sys.stderr)
        return 1

    from agent.orchestrator import handle

    samples = [
        "過去 90 天活躍會員有多少？",
        "Tier 2 會員在商場花了多少？",
        "活動 A 是否造成營收增加？",
    ]
    for q in samples:
        out = handle(q)
        print("---")
        print(q)
        print(out["answer_text"][:240])
        print(
            json.dumps(
                {
                    "response_mode": out["response_mode"],
                    "reason_codes": out["reason_codes"],
                    "n_figures": len(out.get("figures") or []),
                },
                ensure_ascii=False,
            )
        )
    print("V1 smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
