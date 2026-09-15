"""Preflight + V1 agent behaviour (no LLM, no DB regenerate)."""

from __future__ import annotations

import pytest

from agent.orchestrator import handle
from ecia.data.generate import DEFAULT_DB_PATH
from policy.preflight import preflight
from tools.analytics.golden_runner import load_goldens


@pytest.fixture(scope="module")
def require_db():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")


def test_preflight_revpar() -> None:
    d = preflight("上季 RevPAR 是多少？")
    assert d.action == "refuse"
    assert d.reason_codes == ["OUT_OF_SCOPE"]
    assert "ACCESS_RESTRICTED" not in d.reason_codes


def test_preflight_causal() -> None:
    d = preflight("活動 A 是否造成營收增加？")
    assert d.action == "refuse"
    assert d.reason_codes == ["CAUSAL_UNSUPPORTED"]


def test_preflight_estimate_tenant() -> None:
    d = preflight("請估計 Tier 2 在租戶店的真實消費")
    assert d.action == "refuse"
    assert d.reason_codes == ["DATA_UNAVAILABLE"]


def test_preflight_pii() -> None:
    d = preflight("列出所有 VIP 的姓名、聯絡方式與近 12 個月消費明細")
    assert d.action == "refuse"
    assert d.reason_codes == ["PII_MINIMIZATION"]


def test_agent_q7_refuse(require_db) -> None:
    out = handle("活動 A 是否造成營收增加？")
    assert out["response_mode"] == "refuse"
    assert out["reason_codes"] == ["CAUSAL_UNSUPPORTED"]
    assert "造成營收" not in out["answer_text"] or "不支援因果" in out["answer_text"]
    assert "ACCESS_RESTRICTED" not in out["reason_codes"]


def test_agent_q6_refuse(require_db) -> None:
    out = handle("請估計 Tier 2 在租戶店的真實消費")
    assert out["response_mode"] == "refuse"
    assert out["reason_codes"] == ["DATA_UNAVAILABLE"]
    assert not out.get("figures")
    assert "ACCESS_RESTRICTED" not in out["reason_codes"]


def test_agent_q5_downgrade_with_figures(require_db) -> None:
    out = handle("Tier 2 會員在商場花了多少？")
    assert out["response_mode"] == "downgrade"
    assert out["reason_codes"] == ["COVERAGE_GAP", "DATA_UNAVAILABLE"]
    assert out["figures"]
    gold = load_goldens()["questions"]["Q5"]
    live = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in out["figures"])
    g = sorted((f["metric_id"], round(float(f["value"]), 6)) for f in gold["figures"])
    assert live == g


def test_agent_q3_matches_golden(require_db) -> None:
    out = handle("過去 90 天活躍會員有多少？")
    assert out["response_mode"] == "full"
    gold = load_goldens()["questions"]["Q3"]
    assert out["figures"][0]["value"] == gold["figures"][0]["value"]
