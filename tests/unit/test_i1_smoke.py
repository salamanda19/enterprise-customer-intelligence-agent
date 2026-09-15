"""I1 smoke: configs and contracts load; package layout exists."""

from __future__ import annotations

from pathlib import Path

import yaml

from ecia.config_loader import REPO_ROOT, load_app_config, load_yaml


def test_package_layout_exists() -> None:
    src = REPO_ROOT / "src"
    for rel in (
        "semantic",
        "policy",
        "tools",
        "tools/sql",
        "tools/analytics",
        "tools/rag",
        "agent",
        "validation",
    ):
        assert (src / rel).is_dir(), f"missing {rel}"


def test_app_config_loads() -> None:
    cfg = load_app_config()
    assert cfg["routing"]["deterministic_first"] is True
    assert cfg["duckdb"]["read_only"] is True
    assert "ACCESS_RESTRICTED" not in str(cfg)


def test_semantic_yaml() -> None:
    sem = load_yaml(REPO_ROOT / "config" / "semantic.yaml")
    assert sem["defaults"]["customer_means"] == "member"
    assert sem["tiers"]["entry"] == "Tier 1"
    assert sem["tiers"]["highest"] == "Tier 3"
    assert sem["tiers"]["vip_synonym_of"] == "Tier 3"
    assert sem["loyalty"]["active_member"]["window_days"] == 90
    assert sem["loyalty"]["points_per_wallet_cash_unit"] == 1.0
    thr = sem["loyalty"]["high_value_member"]["wallet_cash_threshold"]
    status = sem["loyalty"]["high_value_member"]["threshold_status"]
    assert status in {"pending_data_freeze", "locked_after_data_freeze"}
    if status == "locked_after_data_freeze":
        assert isinstance(thr, int) and thr > 0
    else:
        assert thr is None
    assert sem["definition_authority"]["on_conflict"] == "refuse_definition_conflict"


def test_policy_yaml() -> None:
    pol = load_yaml(REPO_ROOT / "config" / "policy.yaml")
    assert "ACCESS_RESTRICTED" in pol["forbidden_reason_codes"]
    assert "ACCESS_RESTRICTED" not in pol["reason_codes"]
    assert pol["definition_conflict"]["conflict"].startswith("Do not pick a side")


def test_question_contracts() -> None:
    path = REPO_ROOT / "eval" / "questions" / "contracts.yaml"
    data = load_yaml(path)
    by_id = {q["id"]: q for q in data["questions"]}
    assert set(by_id) >= {f"Q{i}" for i in range(1, 16)} | {"Q_REVPAR"}
    for q in data["questions"]:
        assert "expected_amount" not in q
        assert q["question_type"] in {
            "deterministic",
            "analytical",
            "knowledge",
            "should_refuse",
        }
    assert by_id["Q5"]["response_mode"] == "downgrade"
    assert by_id["Q5"]["reason_codes"] == ["COVERAGE_GAP", "DATA_UNAVAILABLE"]
    assert by_id["Q8"]["expectation"].startswith("VIP = Tier 3")
    assert by_id["Q_REVPAR"]["reason_codes"] == ["OUT_OF_SCOPE"]


def test_invariant_catalog() -> None:
    cat = load_yaml(REPO_ROOT / "tests" / "invariants" / "catalog.yaml")
    ids = [i["id"] for i in cat["invariants"]]
    assert ids == [f"I{n}" for n in range(1, 22)]
    i18 = next(i for i in cat["invariants"] if i["id"] == "I18")
    assert i18["earliest_milestone"] == "M2"
    assert i18["test_kind"] == "data_generator"
