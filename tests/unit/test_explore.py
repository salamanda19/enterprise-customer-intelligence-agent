"""I8 explore service tests (whitelist, caps, summarize ≠ limited-mean)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ecia.config_loader import load_app_config
from ecia.data.generate import DEFAULT_DB_PATH
from explore.service import ExploreError, aggregate, preview, summarize
from tools.sql.readonly import run_sql

pytestmark = pytest.mark.skipif(
    not DEFAULT_DB_PATH.exists(),
    reason="DuckDB missing; run scripts/rebuild_db.py",
)


def test_explore_config_present() -> None:
    cfg = load_app_config()["explore"]
    for key in (
        "preview_rows",
        "aggregate_result_cap",
        "value_counts_top_k",
        "default_sample_rows",
        "allow_full_scan",
    ):
        assert key in cfg


def test_preview_rejects_unknown_table() -> None:
    with pytest.raises(ExploreError, match="not allowed"):
        preview("tenant_pos_gmv")


def test_preview_capped() -> None:
    res = preview("members", limit=5)
    assert res.ok
    assert res.data is not None
    assert len(res.data["rows"]) <= 5


def test_aggregate_rejects_write_shaped_table() -> None:
    with pytest.raises(ExploreError, match="not allowed"):
        aggregate("secret_table", group_by=["a"], metrics=[{"fn": "count"}])


def test_summarize_mean_matches_full_avg_not_limited_slice() -> None:
    """WP-807: summarize must not equal mean(LIMIT n) when that differs from full mean."""
    con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    try:
        full_avg = con.execute(
            "SELECT avg(amount) FROM wallet_cash_events"
        ).fetchone()[0]
        limited_avg = con.execute(
            "SELECT avg(amount) FROM ("
            "SELECT amount FROM wallet_cash_events LIMIT 5"
            ")"
        ).fetchone()[0]
        n = con.execute("SELECT COUNT(*) FROM wallet_cash_events").fetchone()[0]
    finally:
        con.close()

    if n <= 5:
        pytest.skip("not enough rows to distinguish LIMIT-then-mean")

    # If the limited slice happens to match full avg, skip (rare)
    if limited_avg is not None and full_avg is not None and abs(limited_avg - full_avg) < 1e-9:
        pytest.skip("LIMIT-5 mean coincides with full mean")

    res = summarize("wallet_cash_events", full_scan=True)
    assert res.ok and res.data
    amount_row = next(
        (
            r
            for r in res.data["summary"]
            if str(r.get("column_name", "")).lower() == "amount"
        ),
        None,
    )
    assert amount_row is not None
    # DuckDB SUMMARIZE uses 'avg' key
    engine_avg = amount_row.get("avg")
    assert engine_avg is not None
    assert abs(float(engine_avg) - float(full_avg)) < 1e-6
    assert abs(float(engine_avg) - float(limited_avg)) > 1e-9


def test_aggregate_group_by_tier() -> None:
    res = aggregate(
        "members",
        group_by=["tier"],
        metrics=[{"fn": "count", "column": "*"}],
        full_scan=True,
    )
    assert res.ok
    assert res.data
    assert len(res.data["rows"]) >= 1
    assert len(res.data["rows"]) <= res.data["result_cap"]


def test_sql_tab_writes_still_rejected() -> None:
    res = run_sql("DELETE FROM members")
    assert not res.ok
    assert res.error
