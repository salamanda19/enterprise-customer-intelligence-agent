#!/usr/bin/env python
"""I6 agent eval vs goldens (+ optional naive baseline).

Gate: refuses to score without full goldens (WP-507 / WP-601).

Examples:
  python scripts/run_agent_eval.py --dry-gate
  python scripts/run_agent_eval.py
  python scripts/run_agent_eval.py --with-naive
  python scripts/run_agent_eval.py --with-naive --naive-llm   # needs secrets.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent.orchestrator import handle  # noqa: E402
from agent_eval.naive_baseline import NAIVE_PROMPT_VERSION, naive_answer  # noqa: E402
from agent_eval.scorer import run_agent_eval, write_results  # noqa: E402
from ecia.config_loader import load_yaml  # noqa: E402
from tools.analytics.golden_runner import require_full_goldens  # noqa: E402


def _agent_answer(prompt: str, question_id: str) -> dict:
    return handle(prompt, question_id=question_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent eval vs goldens (I6)")
    parser.add_argument("--dry-gate", action="store_true", help="Only verify goldens exist")
    parser.add_argument("--with-naive", action="store_true", help="Also score offline naive baseline")
    parser.add_argument(
        "--naive-llm",
        action="store_true",
        help="Naive path may call LLM if secrets.yaml has a key (default: offline simulator)",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON summaries to stdout")
    args = parser.parse_args(argv)

    try:
        gpath = require_full_goldens()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.dry_gate:
        print(f"Goldens OK: {gpath}")
        return 0

    app = load_yaml(ROOT / "config" / "app.yaml")
    agent_meta = {
        "model": app.get("llm", {}).get("model"),
        "prompt_version": app.get("eval", {}).get("agent_prompt_version", "deterministic-router-v1"),
        "routing": app.get("routing"),
    }

    agent_run = run_agent_eval(answer_fn=_agent_answer, system="deterministic_agent")
    agent_run["meta"] = agent_meta
    agent_summary_path = write_results(agent_run, stem="agent")

    print("=== deterministic agent ===")
    print(json.dumps(agent_run["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {agent_summary_path}")

    exit_code = 0
    gates = agent_run["summary"]["gates"]
    if not (
        gates["mode_reason_100"]
        and gates["prohibited_claims_0"]
        and gates["figures_100"]
        and agent_run["summary"].get("q8_conflict_ok")
    ):
        exit_code = 1
        print("AGENT BEHAVIOURAL GATES FAILED", file=sys.stderr)

    if args.with_naive:
        use_llm = bool(args.naive_llm)

        def _naive(prompt: str, question_id: str) -> dict:
            return naive_answer(prompt, question_id, use_llm=use_llm)

        naive_run = run_agent_eval(answer_fn=_naive, system="naive_baseline")
        naive_run["meta"] = {
            "prompt_version": NAIVE_PROMPT_VERSION if not use_llm else "naive-llm-rag-v1",
            "use_llm": use_llm,
            "note": "Baseline for contrast; not expected to pass behavioural gates.",
        }
        naive_path = write_results(naive_run, stem="naive")
        print("=== naive baseline ===")
        print(json.dumps(naive_run["summary"], ensure_ascii=False, indent=2))
        print(f"Wrote {naive_path}")

        comparison = {
            "agent": agent_run["summary"],
            "naive": naive_run["summary"],
            "note": "Do not pre-declare a winner; report measured gap only.",
            "agent_meta": agent_meta,
            "naive_meta": naive_run["meta"],
        }
        cmp_path = ROOT / "eval" / "results" / "agent_vs_naive_latest.json"
        cmp_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {cmp_path}")

    if args.json:
        print(json.dumps({"agent": agent_run["summary"]}, ensure_ascii=False))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
