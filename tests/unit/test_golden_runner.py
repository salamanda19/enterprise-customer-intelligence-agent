"""Lightweight golden runner checks (reuse frozen DB; no regenerate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ecia.data.generate import DEFAULT_DB_PATH
from tools.analytics.golden_runner import (
    V1_QUESTION_IDS,
    answer,
    load_goldens,
    write_goldens,
)

GOLDENS = Path(__file__).resolve().parents[2] / "eval" / "goldens" / "v1_goldens.json"


@pytest.fixture(scope="module")
def require_db():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")


def test_v1_modes_and_reason_codes(require_db) -> None:
    q5 = answer("Q5")
    assert q5["response_mode"] == "downgrade"
    assert q5["reason_codes"] == ["COVERAGE_GAP", "DATA_UNAVAILABLE"]
    assert q5["figures"]
    assert all(isinstance(f["value"], (int, float)) for f in q5["figures"])

    q14 = answer("Q14")
    assert q14["response_mode"] == "full"
    assert "不算活躍" in q14["answer_text"]

    q8 = answer("Q8")
    assert q8["response_mode"] == "full"
    assert "Tier 3" in q8["answer_text"]

    q8c = answer("Q8", conflict_vip=True)
    assert q8c["response_mode"] == "refuse"
    assert q8c["reason_codes"] == ["DEFINITION_CONFLICT"]


def test_goldens_file_matches_runner(require_db) -> None:
    if not GOLDENS.exists():
        write_goldens()
    golden = load_goldens(GOLDENS)
    for qid in V1_QUESTION_IDS:
        live = answer(qid)
        g = golden["questions"][qid]
        assert live["response_mode"] == g["response_mode"]
        assert live["reason_codes"] == g["reason_codes"]
        live_vals = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in live["figures"])
        gold_vals = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in g["figures"])
        assert live_vals == gold_vals, qid
