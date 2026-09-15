"""Data-layer invariants against the frozen synthetic DuckDB (WP-204).

Uses the repo DB at data/synthetic/generated/ir01.duckdb when present so weak
machines are not forced to regenerate (~1 minute) on every pytest run.
"""

from __future__ import annotations

import duckdb
import pytest

from ecia.config_loader import REPO_ROOT
from ecia.data.generate import DEFAULT_DB_PATH

SCHEMA_SQL = (REPO_ROOT / "src" / "ecia" / "data" / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def con():
    if not DEFAULT_DB_PATH.exists():
        pytest.skip("Frozen DB missing; run: python scripts/rebuild_db.py")
    c = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
    yield c
    c.close()


def test_no_tenant_gmv_or_pos_tables(con) -> None:
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    forbidden = {"tenant_pos", "tenant_gmv", "tenant_transactions", "gmv"}
    assert not (tables & forbidden)
    assert "tenant_reported_redemption_counts" in tables
    cols = [r[0] for r in con.execute("DESCRIBE tenant_reported_redemption_counts").fetchall()]
    assert "redemption_count" in cols
    assert not any("amount" in c.lower() or "gmv" in c.lower() for c in cols)


def test_leased_outlet_not_in_self_op_facts(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*)
        FROM self_op_transactions t
        JOIN outlets o ON t.outlet_id = o.outlet_id
        WHERE o.operating_model = 'leased'
        """
    ).fetchone()[0]
    assert n == 0


def test_ird_not_in_fb_bucket(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*)
        FROM self_op_transactions t
        JOIN outlets o ON t.outlet_id = o.outlet_id
        WHERE o.outlet_id = 'HTL_IRD' AND t.revenue_bucket = 'fb_self_op'
        """
    ).fetchone()[0]
    assert n == 0
    n2 = con.execute(
        """
        SELECT COUNT(*) FROM self_op_transactions
        WHERE outlet_id = 'HTL_IRD' AND revenue_bucket = 'hotel_other'
        """
    ).fetchone()[0]
    assert n2 > 0


def test_tenant_voucher_redemption_not_in_revenue(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*)
        FROM voucher_redemptions r
        JOIN outlets o ON r.outlet_id = o.outlet_id
        JOIN self_op_transactions t
          ON t.voucher_id = r.voucher_id AND t.payment_path = 'voucher_redeem_self_op'
        WHERE o.operating_model = 'leased'
        """
    ).fetchone()[0]
    assert n == 0


def test_package_cash_conservation(con) -> None:
    rows = con.execute(
        """
        SELECT p.package_id, p.cash_received,
               SUM(c.recognized_amount) FILTER (WHERE c.recognition = 'ir_revenue') AS rev,
               SUM(c.recognized_amount) FILTER (
                 WHERE c.recognition = 'liability'
                   AND c.status IN ('pending', 'settled_liability')
               ) AS liab,
               SUM(c.recognized_amount) FILTER (WHERE c.recognition = 'hotel_other') AS brk
        FROM packages p
        JOIN package_components c ON c.package_id = p.package_id
        GROUP BY 1, 2
        """
    ).fetchall()
    assert rows
    for package_id, cash, rev, liab, brk in rows:
        rev = rev or 0
        liab = liab or 0
        brk = brk or 0
        assert rev + liab + brk <= cash + 1e-6, package_id


def test_self_op_voucher_redeem_not_second_wallet(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*) FROM wallet_cash_events
        WHERE source_type = 'voucher_redeem'
        """
    ).fetchone()[0]
    assert n == 0
    n2 = con.execute(
        """
        SELECT COUNT(*) FROM self_op_transactions
        WHERE payment_path = 'voucher_redeem_self_op'
        """
    ).fetchone()[0]
    assert n2 > 0


def test_comp_not_wallet_or_revenue(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*)
        FROM vouchers v
        JOIN wallet_cash_events w ON w.event_id = v.wallet_cash_event_id
        WHERE v.funding_source = 'comp'
        """
    ).fetchone()[0]
    assert n == 0
    n2 = con.execute(
        """
        SELECT COUNT(*)
        FROM vouchers v
        JOIN self_op_transactions t ON t.voucher_id = v.voucher_id
        WHERE v.funding_source = 'comp'
        """
    ).fetchone()[0]
    assert n2 == 0


def test_folio_dinner_in_fb(con) -> None:
    n = con.execute(
        """
        SELECT COUNT(*) FROM self_op_transactions
        WHERE payment_path = 'folio' AND revenue_bucket = 'fb_self_op'
        """
    ).fetchone()[0]
    assert n >= 1


def test_tenant_reported_counts_exist(con) -> None:
    n = con.execute("SELECT COUNT(*) FROM tenant_reported_redemption_counts").fetchone()[0]
    assert n >= 1
    leased = con.execute(
        """
        SELECT COUNT(*)
        FROM tenant_reported_redemption_counts r
        JOIN outlets o ON o.outlet_id = r.outlet_id
        WHERE o.operating_model = 'leased'
        """
    ).fetchone()[0]
    assert leased == n


def test_two_full_years_and_unidentified(con) -> None:
    start = con.execute("SELECT value FROM meta WHERE key='start_date'").fetchone()[0]
    end = con.execute("SELECT value FROM meta WHERE key='end_date'").fetchone()[0]
    assert start.startswith("2024")
    assert end.startswith("2025")
    n_unid = con.execute(
        "SELECT COUNT(*) FROM wallet_cash_events WHERE member_id IS NULL"
    ).fetchone()[0]
    assert n_unid > 0


def test_schema_has_no_tenant_pos() -> None:
    assert "tenant_pos" not in SCHEMA_SQL.lower()
    assert "tenant_gmv" not in SCHEMA_SQL.lower()
