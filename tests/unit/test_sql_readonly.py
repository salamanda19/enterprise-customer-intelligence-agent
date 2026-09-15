"""SQL readonly tool tests (no DB regenerate)."""

from tools.sql.readonly import run_sql, validate_readonly_sql


def test_rejects_writes() -> None:
    assert validate_readonly_sql("DELETE FROM members") is not None
    assert validate_readonly_sql("DROP TABLE members") is not None
    assert validate_readonly_sql("UPDATE members SET tier='Tier 1'") is not None


def test_allows_select() -> None:
    assert validate_readonly_sql("SELECT COUNT(*) AS n FROM members") is None


def test_run_select_capped() -> None:
    res = run_sql("SELECT member_id, tier FROM members")
    if not res.ok and res.error and "DB missing" in res.error:
        return
    assert res.ok
    assert res.rows is not None
    assert len(res.rows) <= 100
