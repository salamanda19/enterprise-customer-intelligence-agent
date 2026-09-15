#!/usr/bin/env python
"""2–5 minute demo: real Q5 downgrade + Q7 refuse (no fabricated narration).

    python scripts/demo.py
    python scripts/demo.py --http   # requires API on config/app.yaml port
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent.meta import attach_meta  # noqa: E402
from agent.orchestrator import handle  # noqa: E402
from ecia.config_loader import REPO_ROOT, load_yaml  # noqa: E402


DEMOS = ("Q5", "Q7")


def _prompt(qid: str) -> str:
    contracts = load_yaml(REPO_ROOT / "eval" / "questions" / "contracts.yaml")["questions"]
    return next(c["prompt"] for c in contracts if c["id"] == qid)


def run_local(qid: str) -> dict:
    prompt = _prompt(qid)
    t0 = time.perf_counter()
    out = handle(prompt, question_id=qid)
    return attach_meta(out, latency_ms=(time.perf_counter() - t0) * 1000)


def run_http(qid: str, base: str) -> dict:
    body = json.dumps({"question_id": qid}).encode("utf-8")
    req = urllib.request.Request(
        f"{base.rstrip('/')}/ask",
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _print(qid: str, payload: dict) -> None:
    print("=" * 60)
    print(f"{qid}  prompt: {_prompt(qid)}")
    print(f"mode={payload.get('response_mode')}  reasons={payload.get('reason_codes')}")
    print(f"meta={payload.get('meta')}")
    print("--- answer ---")
    print(payload.get("answer_text"))
    figs = payload.get("figures") or []
    if figs:
        print("--- figures ---")
        for f in figs:
            print(f"  {f.get('metric_id')}={f.get('value')}  period={f.get('period')}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demo Q5 downgrade + Q7 refuse")
    parser.add_argument("--http", action="store_true", help="Call running API instead of in-process")
    args = parser.parse_args(argv)

    cfg = load_yaml(REPO_ROOT / "config" / "app.yaml")
    port = int((cfg.get("api") or {}).get("port", 8080))
    base = f"http://127.0.0.1:{port}"

    print("ECIA demo — live structured outputs (not narrated numbers)\n")
    for qid in DEMOS:
        try:
            payload = run_http(qid, base) if args.http else run_local(qid)
        except (urllib.error.URLError, OSError) as exc:
            print(f"HTTP failed ({exc}); falling back to local handle()", file=sys.stderr)
            payload = run_local(qid)
        _print(qid, payload)

        # Guardrails for the demo script itself
        if qid == "Q5":
            assert payload.get("response_mode") == "downgrade"
            assert payload.get("figures"), "Q5 must show observable figures"
        if qid == "Q7":
            assert payload.get("response_mode") == "refuse"
            assert "CAUSAL_UNSUPPORTED" in (payload.get("reason_codes") or [])

    print("Demo OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
