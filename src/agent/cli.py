"""CLI entry for the V1 agent (deterministic-first; no GPU/LLM required)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from agent.meta import attach_meta  # noqa: E402
from agent.orchestrator import handle  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IR customer-intelligence agent (V1 CLI)")
    parser.add_argument("question", nargs="?", help="Natural-language question")
    parser.add_argument("--question-id", dest="question_id", help="Contract id e.g. Q5")
    parser.add_argument("--json", action="store_true", help="Print full structured JSON")
    args = parser.parse_args(argv)

    if not args.question and not args.question_id:
        parser.error("Provide a question and/or --question-id")

    # If only id given, load prompt from contracts
    question = args.question
    if args.question_id and not question:
        from ecia.config_loader import REPO_ROOT, load_yaml

        contracts = load_yaml(REPO_ROOT / "eval" / "questions" / "contracts.yaml")["questions"]
        by_id = {c["id"]: c for c in contracts}
        if args.question_id not in by_id:
            print(f"Unknown question id: {args.question_id}", file=sys.stderr)
            return 2
        question = by_id[args.question_id]["prompt"]

    import time

    t0 = time.perf_counter()
    result = attach_meta(handle(question, question_id=args.question_id), latency_ms=(time.perf_counter() - t0) * 1000)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["answer_text"])
        print(
            f"[{result['response_mode']}] reason_codes={result.get('reason_codes')} "
            f"figures={len(result.get('figures') or [])} "
            f"latency_ms={result.get('meta', {}).get('latency_ms')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
