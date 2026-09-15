#!/usr/bin/env python
"""Build template-variant catalog + goldens (WP-603).

    python scripts/build_variant_goldens.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_eval.variants import build_variant_specs, write_variant_goldens  # noqa: E402


def main() -> int:
    specs = build_variant_specs()
    path = write_variant_goldens()
    print(f"Variants: {len(specs)}")
    print(f"Wrote {path}")
    print(f"Wrote {ROOT / 'eval' / 'questions' / 'variants.yaml'}")
    if len(specs) < 50:
        print(
            f"NOTE: variant count {len(specs)} < 50 target; documented shortfall OK per work plan.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
