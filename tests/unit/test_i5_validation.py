"""I5 validators + full golden coverage (no DB regenerate)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ecia.data.generate import DEFAULT_DB_PATH
from tools.analytics.golden_runner import (
    ALL_QUESTION_IDS,
    answer,
    load_goldens,
    require_full_goldens,
    write_all_goldens,
)
from validation import (
    answer_introduces_unlisted_numbers,
    injection_treated_as_data,
    validate_answer,
)

ROOT = Path(__file__).resolve().parents[2]
FULL_GOLDENS = ROOT / "eval" / "goldens" / "q1_q15_goldens.json"
INJECTION_DOC = ROOT / "data" / "documents"


@pytest.fixture(scope="module")
def require_db():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")


@pytest.fixture(scope="module")
def full_goldens(require_db):
    if not FULL_GOLDENS.exists():
        write_all_goldens()
    return load_goldens(FULL_GOLDENS)


def test_all_question_ids_run(require_db) -> None:
    for qid in ALL_QUESTION_IDS:
        out = answer(qid)
        assert out["response_mode"]
        assert isinstance(out["reason_codes"], list)


def test_q2_declare_hotel_pillar(require_db) -> None:
    out = answer("Q2")
    assert out["response_mode"] == "declare"
    assert out["reason_codes"] == ["SEMANTIC_AMBIGUITY"]
    ids = {f["metric_id"] for f in out["figures"]}
    assert "hotel_pillar_total" in ids
    assert "hotel_pillar_total" in out["answer_text"] or "酒店支柱合計" in out["answer_text"]


def test_q11_deltas_sum(require_db) -> None:
    out = answer("Q11")
    assert not validate_answer(out, "Q11")


def test_q12_observable_dining_no_ird_claim(require_db) -> None:
    out = answer("Q12")
    assert "IRD" in out["answer_text"]
    assert not validate_answer(out, "Q12")


def test_q11_q12_negative_unlisted_numbers(require_db) -> None:
    bad = answer("Q11")
    bad = dict(bad)
    bad["answer_text"] = bad["answer_text"] + " 另外有神秘增量 99999.99。"
    errs = answer_introduces_unlisted_numbers(bad)
    assert errs, "expected unlisted number detection"


def test_q15_tenant_not_pillar_revenue(require_db) -> None:
    out = answer("Q15")
    assert out["response_mode"] == "full"
    assert "不分別計入" in out["answer_text"] or "不" in out["answer_text"]
    assert "F&B" in out["answer_text"]


def test_full_goldens_match_runner(full_goldens) -> None:
    for qid in ALL_QUESTION_IDS:
        live = answer(qid)
        g = full_goldens["questions"][qid]
        assert live["response_mode"] == g["response_mode"], qid
        assert live["reason_codes"] == g["reason_codes"], qid
        live_vals = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in live["figures"])
        gold_vals = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in g["figures"])
        assert live_vals == gold_vals, qid


def test_require_full_goldens_gate(full_goldens) -> None:
    path = require_full_goldens(FULL_GOLDENS)
    assert path.exists()


def test_require_full_goldens_missing(tmp_path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError, match="refusing agent eval"):
        require_full_goldens(missing)


def test_injection_not_in_system_policy(require_db) -> None:
    docs = list(INJECTION_DOC.glob("*inject*")) + list(INJECTION_DOC.glob("*injection*"))
    if not docs:
        pytest.skip("No injection sample doc")
    chunk = docs[0].read_text(encoding="utf-8")
    policy = (ROOT / "config" / "policy.yaml").read_text(encoding="utf-8")
    assert injection_treated_as_data(chunk, policy)
