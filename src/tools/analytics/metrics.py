"""Named deterministic metrics over the synthetic DuckDB (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from ecia.config_loader import REPO_ROOT, load_yaml
from ecia.data.generate import DEFAULT_DB_PATH


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    label: str


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = db_path or DEFAULT_DB_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: python scripts/rebuild_db.py"
        )
    return duckdb.connect(str(path), read_only=True)


def as_of(con: duckdb.DuckDBPyConnection) -> date:
    raw = con.execute("SELECT value FROM meta WHERE key = 'as_of_date'").fetchone()[0]
    return date.fromisoformat(raw)


def last_quarter(as_of_date: date) -> Period:
    """Calendar quarter containing as_of_date, treated as '上季' when as_of is quarter-end."""
    q = (as_of_date.month - 1) // 3  # 0..3
    start_month = q * 3 + 1
    start = date(as_of_date.year, start_month, 1)
    if q == 3:
        end = date(as_of_date.year, 12, 31)
    else:
        next_start = date(as_of_date.year, start_month + 3, 1)
        end = next_start.fromordinal(next_start.toordinal() - 1)
    return Period(start, end, f"{as_of_date.year}-Q{q + 1}")


def prior_90_days(as_of_date: date) -> Period:
    from datetime import timedelta

    start = as_of_date - timedelta(days=89)
    return Period(start, as_of_date, "trailing_90d")


def trailing_12_months(as_of_date: date) -> Period:
    from datetime import timedelta

    start = as_of_date - timedelta(days=364)
    return Period(start, as_of_date, "trailing_12m")


def net_room_revenue(con: duckdb.DuckDBPyConnection, period: Period) -> float:
    row = con.execute(
        """
        SELECT COALESCE(SUM(net_room_revenue), 0)
        FROM stays
        WHERE cancelled = FALSE
          AND check_out >= ?
          AND check_out <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return float(row[0])


def hotel_other_revenue(con: duckdb.DuckDBPyConnection, period: Period) -> float:
    row = con.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM self_op_transactions
        WHERE revenue_bucket = 'hotel_other'
          AND txn_date >= ? AND txn_date <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return float(row[0])


def hotel_pillar_total(con: duckdb.DuckDBPyConnection, period: Period) -> float:
    return net_room_revenue(con, period) + hotel_other_revenue(con, period)


def fb_self_op_revenue(con: duckdb.DuckDBPyConnection, period: Period) -> float:
    row = con.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM self_op_transactions
        WHERE revenue_bucket = 'fb_self_op'
          AND txn_date >= ? AND txn_date <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return float(row[0])


def retail_self_op_revenue(con: duckdb.DuckDBPyConnection, period: Period) -> float:
    row = con.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM self_op_transactions
        WHERE revenue_bucket = 'retail_self_op'
          AND txn_date >= ? AND txn_date <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return float(row[0])


def member_count(con: duckdb.DuckDBPyConnection) -> int:
    return int(con.execute("SELECT COUNT(*) FROM members").fetchone()[0])


def active_member_count(con: duckdb.DuckDBPyConnection, period: Period) -> int:
    row = con.execute(
        """
        SELECT COUNT(DISTINCT member_id)
        FROM wallet_cash_events
        WHERE member_id IS NOT NULL
          AND event_date >= ? AND event_date <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return int(row[0])


def voucher_issued_amount(
    con: duckdb.DuckDBPyConnection,
    period: Period,
    *,
    shopping_only: bool = False,
) -> float:
    # Shopping vouchers: redeemed or destined at retail outlets, or funding shopping
    # Approximate: face_value of vouchers issued in period that are not F&B-tagged packages only.
    # For Q10 we use all vouchers issued in period (shopping-focused dataset is majority retail).
    row = con.execute(
        """
        SELECT COALESCE(SUM(face_value), 0)
        FROM vouchers
        WHERE issued_date >= ? AND issued_date <= ?
        """,
        [period.start, period.end],
    ).fetchone()
    return float(row[0])


def voucher_redeemed_amount(
    con: duckdb.DuckDBPyConnection,
    period: Period,
    *,
    shopping_only: bool = False,
) -> float:
    if shopping_only:
        row = con.execute(
            """
            SELECT COALESCE(SUM(r.face_amount), 0)
            FROM voucher_redemptions r
            JOIN outlets o ON o.outlet_id = r.outlet_id
            WHERE r.redeemed_date >= ? AND r.redeemed_date <= ?
              AND o.pillar = 'retail'
            """,
            [period.start, period.end],
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT COALESCE(SUM(face_amount), 0)
            FROM voucher_redemptions
            WHERE redeemed_date >= ? AND redeemed_date <= ?
            """,
            [period.start, period.end],
        ).fetchone()
    return float(row[0])


def observable_retail(
    con: duckdb.DuckDBPyConnection,
    period: Period,
    *,
    tier: str | None = None,
) -> dict[str, float]:
    """Self-op retail POS ∪ shopping voucher redemptions (Q5 downgrade subset)."""
    if tier:
        pos = con.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM self_op_transactions t
            JOIN members m ON m.member_id = t.member_id
            WHERE t.revenue_bucket = 'retail_self_op'
              AND t.payment_path IN ('pos', 'voucher_redeem_self_op', 'package_component')
              AND t.txn_date >= ? AND t.txn_date <= ?
              AND m.tier = ?
            """,
            [period.start, period.end, tier],
        ).fetchone()[0]
        vouchers = con.execute(
            """
            SELECT COALESCE(SUM(r.face_amount), 0)
            FROM voucher_redemptions r
            JOIN outlets o ON o.outlet_id = r.outlet_id
            JOIN members m ON m.member_id = r.member_id
            WHERE o.pillar = 'retail'
              AND r.redeemed_date >= ? AND r.redeemed_date <= ?
              AND m.tier = ?
            """,
            [period.start, period.end, tier],
        ).fetchone()[0]
    else:
        pos = retail_self_op_revenue(con, period)
        vouchers = voucher_redeemed_amount(con, period, shopping_only=True)
    return {
        "self_op_retail_pos": float(pos),
        "shopping_voucher_redeemed_face": float(vouchers),
        "observable_total": float(pos) + float(vouchers),
    }


def tenant_only_redeemers_not_active(
    con: duckdb.DuckDBPyConnection,
    period: Period,
) -> dict[str, Any]:
    """Q14: members with tenant voucher redeem in window and no wallet cash → not active."""
    rows = con.execute(
        """
        WITH redeemers AS (
          SELECT DISTINCT r.member_id
          FROM voucher_redemptions r
          JOIN outlets o ON o.outlet_id = r.outlet_id
          WHERE o.operating_model = 'leased'
            AND r.member_id IS NOT NULL
            AND r.redeemed_date >= ? AND r.redeemed_date <= ?
        ),
        cashers AS (
          SELECT DISTINCT member_id
          FROM wallet_cash_events
          WHERE member_id IS NOT NULL
            AND event_date >= ? AND event_date <= ?
        )
        SELECT COUNT(*) FROM redeemers d
        WHERE d.member_id NOT IN (SELECT member_id FROM cashers)
        """,
        [period.start, period.end, period.start, period.end],
    ).fetchone()
    count = int(rows[0])
    return {
        "tenant_only_redeemer_count": count,
        "are_they_active": False,
        "rule": "I16: tenant voucher redemption is not an active-qualifying event",
    }


def prior_quarter(period: Period) -> Period:
    """Immediate previous calendar quarter relative to `period`."""
    # period.label like 2025-Q4
    year = period.start.year
    q = (period.start.month - 1) // 3 + 1
    if q == 1:
        year -= 1
        q = 4
    else:
        q -= 1
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    if q == 4:
        end = date(year, 12, 31)
    else:
        next_start = date(year, start_month + 3, 1)
        end = date.fromordinal(next_start.toordinal() - 1)
    return Period(start, end, f"{year}-Q{q}")


def same_quarter_prior_year(period: Period) -> Period:
    start = date(period.start.year - 1, period.start.month, period.start.day)
    end = date(period.end.year - 1, period.end.month, period.end.day)
    q = (start.month - 1) // 3 + 1
    return Period(start, end, f"{start.year}-Q{q}")


def ir_revenue_by_tier(con: duckdb.DuckDBPyConnection, period: Period) -> dict[str, float]:
    """Self-op IR recognized revenue attributed to end-snapshot member tiers."""
    room = con.execute(
        """
        SELECT COALESCE(m.tier, 'unidentified'), COALESCE(SUM(s.net_room_revenue), 0)
        FROM stays s
        LEFT JOIN members m ON m.member_id = s.member_id
        WHERE s.cancelled = FALSE
          AND s.check_out >= ? AND s.check_out <= ?
        GROUP BY 1
        """,
        [period.start, period.end],
    ).fetchall()
    txn = con.execute(
        """
        SELECT COALESCE(m.tier, 'unidentified'), COALESCE(SUM(t.amount), 0)
        FROM self_op_transactions t
        LEFT JOIN members m ON m.member_id = t.member_id
        WHERE t.txn_date >= ? AND t.txn_date <= ?
          AND t.revenue_bucket IN ('fb_self_op', 'retail_self_op', 'hotel_other')
        GROUP BY 1
        """,
        [period.start, period.end],
    ).fetchall()
    out: dict[str, float] = {}
    for tier, amt in list(room) + list(txn):
        out[str(tier)] = out.get(str(tier), 0.0) + float(amt)
    return out


def tier_contribution_change(
    con: duckdb.DuckDBPyConnection,
    current: Period,
    prior: Period,
) -> dict[str, Any]:
    cur = ir_revenue_by_tier(con, current)
    prev = ir_revenue_by_tier(con, prior)
    tiers = sorted(set(cur) | set(prev))
    deltas = {t: cur.get(t, 0.0) - prev.get(t, 0.0) for t in tiers if t.startswith("Tier")}
    if not deltas:
        top = None
        top_delta = 0.0
    else:
        top = max(deltas, key=lambda t: abs(deltas[t]))
        top_delta = deltas[top]
    return {
        "current": cur,
        "prior": prev,
        "deltas": deltas,
        "largest_abs_contributor_tier": top,
        "largest_abs_delta": top_delta,
        "sum_deltas": sum(deltas.values()),
    }


def observable_dining(
    con: duckdb.DuckDBPyConnection,
    period: Period,
    *,
    tier: str | None = None,
) -> dict[str, float]:
    """Self-op F&B ∪ F&B voucher redemptions; excludes IRD."""
    if tier:
        pos = con.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM self_op_transactions t
            JOIN members m ON m.member_id = t.member_id
            WHERE t.revenue_bucket = 'fb_self_op'
              AND t.txn_date >= ? AND t.txn_date <= ?
              AND m.tier = ?
            """,
            [period.start, period.end, tier],
        ).fetchone()[0]
        vouchers = con.execute(
            """
            SELECT COALESCE(SUM(r.face_amount), 0)
            FROM voucher_redemptions r
            JOIN outlets o ON o.outlet_id = r.outlet_id
            JOIN members m ON m.member_id = r.member_id
            WHERE o.pillar = 'fb'
              AND r.redeemed_date >= ? AND r.redeemed_date <= ?
              AND m.tier = ?
            """,
            [period.start, period.end, tier],
        ).fetchone()[0]
    else:
        pos = fb_self_op_revenue(con, period)
        vouchers = con.execute(
            """
            SELECT COALESCE(SUM(r.face_amount), 0)
            FROM voucher_redemptions r
            JOIN outlets o ON o.outlet_id = r.outlet_id
            WHERE o.pillar = 'fb'
              AND r.redeemed_date >= ? AND r.redeemed_date <= ?
            """,
            [period.start, period.end],
        ).fetchone()[0]
    return {
        "fb_self_op": float(pos),
        "fb_voucher_redeemed_face": float(vouchers),
        "observable_dining_total": float(pos) + float(vouchers),
    }


def package_and_folio_rules(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Q15 facts: tenant package components are liability; folio dinner in F&B."""
    comps = con.execute(
        """
        SELECT p.label, c.component_type, c.recognition, c.recognized_amount, c.status
        FROM packages p
        JOIN package_components c ON c.package_id = p.package_id
        WHERE p.label IN ('tenant_breakfast_and_shop', 'self_op_breakfast')
        ORDER BY p.label, c.component_type
        """
    ).fetchall()
    folio = con.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM self_op_transactions
        WHERE payment_path = 'folio' AND revenue_bucket = 'fb_self_op'
        """
    ).fetchone()
    return {
        "components": [
            {
                "package": r[0],
                "component_type": r[1],
                "recognition": r[2],
                "recognized_amount": float(r[3]),
                "status": r[4],
            }
            for r in comps
        ],
        "folio_fb_txn_count": int(folio[0]),
        "folio_fb_amount": float(folio[1]),
        "tenant_meal_is_fb_revenue": False,
        "shopping_voucher_is_retail_revenue": False,
        "folio_dinner_is_hotel_package_split": False,
    }


def high_value_vs_vip(semantic_path: Path | None = None) -> dict[str, Any]:
    sem = load_yaml(semantic_path or (REPO_ROOT / "config" / "semantic.yaml"))
    thr = sem["loyalty"]["high_value_member"]["wallet_cash_threshold"]
    return {
        "answer_text": (
            "否。高價值會員看過去 12 個月 IR 錢包現金是否超過門檻"
            f"（目前門檻={thr}）；VIP＝Tier 3（最高忠誠等級）。兩者不等同。"
        ),
        "high_value_threshold": thr,
        "vip_tier": sem["tiers"]["vip_synonym_of"],
        "equated": False,
    }


def vip_definition(
    *,
    include_conflict_doc: bool = False,
    semantic_path: Path | None = None,
) -> dict[str, Any]:
    """Q8: VIP = Tier 3; conflict doc triggers refuse path."""
    sem = load_yaml(semantic_path or (REPO_ROOT / "config" / "semantic.yaml"))
    vip_tier = sem["tiers"]["vip_synonym_of"]
    declare = sem["tiers"]["vip_declare"]
    if include_conflict_doc:
        return {
            "response_mode": "refuse",
            "reason_codes": ["DEFINITION_CONFLICT"],
            "answer_text": (
                "核准文件與語意層對 VIP 定義互斥，系統拒絕選邊。"
                "語意層：VIP＝Tier 3。衝突文件將 VIP 寫成飯店名單／短期高消費。"
                "請更新 SSOT 後再答。"
            ),
            "definitions_used": [
                "semantic.tiers.vip_synonym_of",
                "documents/vip_definition_conflict.md",
            ],
        }
    return {
        "response_mode": "full",
        "reason_codes": [],
        "answer_text": declare,
        "definitions_used": [
            "semantic.tiers.vip_synonym_of",
            "semantic.tiers.vip_declare",
        ],
        "vip_equals_tier": vip_tier,
    }
