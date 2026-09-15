"""I6 agent eval + naive baseline (offline; no DB regenerate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.orchestrator import handle
from agent_eval.naive_baseline import naive_answer
from agent_eval.scorer import run_agent_eval, score_payload
from agent_eval.variants import build_variant_specs, write_variant_goldens
from ecia.data.generate import DEFAULT_DB_PATH
from tools.analytics.golden_runner import answer, load_goldens, require_full_goldens


@pytest.fixture(scope="module")
def require_db():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")


def test_agent_eval_passes_behavioural_gates(require_db) -> None:
    require_full_goldens()

    def fn(prompt: str, qid: str):
        return handle(prompt, question_id=qid)

    result = run_agent_eval(answer_fn=fn, system="deterministic_agent")
    summary = result["summary"]
    assert summary["gates"]["mode_reason_100"]
    assert summary["gates"]["prohibited_claims_0"]
    assert summary["gates"]["figures_100"]
    assert summary["q8_conflict_ok"] is True
    assert summary["pass_all_behavioural"] is True
    assert summary["latency_ms_median"] is not None


def test_naive_baseline_fails_gates(require_db) -> None:
    def fn(prompt: str, qid: str):
        return naive_answer(prompt, qid, use_llm=False)

    result = run_agent_eval(answer_fn=fn, system="naive_baseline", include_conflict_q8=True)
    summary = result["summary"]
    # Naive must not look like a perfect agent on behavioural gates
    assert summary["pass_all_behavioural"] is False
    assert summary["figures_match_rate"] < 1.0 or summary["mode_match_rate"] < 1.0


def test_score_payload_detects_mode_mismatch(require_db) -> None:
    golden = answer("Q3")
    bad = dict(golden)
    bad["response_mode"] = "refuse"
    sc = score_payload("Q3", bad, golden)
    assert sc.ok is False
    assert sc.mode_ok is False


def test_variant_catalog_and_goldens(require_db, tmp_path) -> None:
    specs = build_variant_specs()
    assert len(specs) >= 50
    out = tmp_path / "variant_goldens.json"
    path = write_variant_goldens(out_path=out)
    data = load_goldens(path)
    assert data["count"] == len(specs)
    assert len(data["questions"]) == len(specs)
