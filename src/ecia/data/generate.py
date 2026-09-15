"""Synthetic IR world generator (deterministic seed)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb

from ecia.config_loader import REPO_ROOT

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = REPO_ROOT / "data" / "synthetic" / "generated" / "ir01.duckdb"
SEED = 42
PROPERTY_ID = "IR01"


@dataclass
class GenStats:
    members: int = 0
    wallet_cash_total: float = 0.0
    high_value_threshold: float | None = None


def _rng(seed: int):
    import random

    return random.Random(seed)


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def _insert_outlets(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, str]]:
    rows = [
        ("FB_SELF_1", "Harbor Grill", "fb", "self_op"),
        ("FB_SELF_2", "Garden Cafe", "fb", "self_op"),
        ("FB_SELF_3", "Lobby Bar", "fb", "self_op"),
        ("FB_LEASE_1", "Star Chef Bistro", "fb", "leased"),
        ("RET_SELF_1", "Resort Souvenirs", "retail", "self_op"),
        ("RET_LEASE_1", "Brand Boutique A", "retail", "leased"),
        ("RET_LEASE_2", "Brand Boutique B", "retail", "leased"),
        ("RET_LEASE_3", "Brand Boutique C", "retail", "leased"),
        ("HTL_IRD", "In-Room Dining", "hotel", "self_op"),
    ]
    con.executemany(
        "INSERT INTO outlets VALUES (?, ?, ?, ?)",
        rows,
    )
    return {r[0]: {"pillar": r[2], "operating_model": r[3]} for r in rows}


def generate(
    db_path: Path | None = None,
    *,
    seed: int = SEED,
    start_year: int = 2024,
) -> GenStats:
    """Build a fresh DuckDB file with ≥2 full years of synthetic IR data."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    rng = _rng(seed)
    con = duckdb.connect(str(path))
    create_schema(con)
    outlets = _insert_outlets(con)

    stats = GenStats()
    start = date(start_year, 1, 1)
    end = date(start_year + 1, 12, 31)

    # --- members ---
    n_members = 120
    members: list[tuple] = []
    for i in range(1, n_members + 1):
        mid = f"M{i:04d}"
        join = start + timedelta(days=rng.randint(0, 200))
        # provisional tier; recomputed after wallet cash
        members.append((mid, join, "Tier 1", None))
    con.executemany("INSERT INTO members VALUES (?, ?, ?, ?)", members)
    stats.members = n_members

    # --- campaigns ---
    con.execute(
        "INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?)",
        [
            "CAMP_A",
            "Co-brand Shopping Week",
            date(start_year + 1, 3, 1),
            date(start_year + 1, 3, 31),
            "RET_LEASE_1",
            False,
        ],
    )
    contacts = []
    for i, mid in enumerate([f"M{i:04d}" for i in range(1, 41)], start=1):
        contacts.append(
            (
                f"CC{i:04d}",
                "CAMP_A",
                mid,
                date(start_year + 1, 3, rng.randint(1, 28)),
            )
        )
    con.executemany("INSERT INTO campaign_contacts VALUES (?, ?, ?, ?)", contacts)

    # helpers
    wallet_rows: list[tuple] = []
    points_rows: list[tuple] = []
    stay_rows: list[tuple] = []
    txn_rows: list[tuple] = []
    voucher_rows: list[tuple] = []
    redeem_rows: list[tuple] = []
    package_rows: list[tuple] = []
    component_rows: list[tuple] = []
    report_rows: list[tuple] = []

    wid = 0
    pid = 0
    tid = 0
    vid = 0
    rid = 0
    sid = 0
    pkg_i = 0
    comp_i = 0

    def add_wallet(member_id: str | None, d: date, amount: float, source_type: str, source_id: str) -> str:
        nonlocal wid, pid
        wid += 1
        eid = f"W{wid:05d}"
        wallet_rows.append((eid, member_id, d, round(amount, 2), source_type, source_id))
        stats.wallet_cash_total += amount
        if member_id:
            pid += 1
            points_rows.append((f"P{pid:05d}", member_id, d, round(amount, 2), "earn", eid))
        return eid

    # --- stays + room revenue (members + unidentified) ---
    for i in range(1, 401):
        sid += 1
        stay_id = f"S{sid:05d}"
        d0 = start + timedelta(days=rng.randint(0, (end - start).days - 3))
        nights = rng.randint(1, 4)
        cancelled = rng.random() < 0.05
        identified = rng.random() < 0.7
        mid = f"M{rng.randint(1, n_members):04d}" if identified else None
        guest = f"G{sid:05d}"
        net = 0.0 if cancelled else round(180 * nights * (0.85 + rng.random() * 0.3), 2)
        stay_rows.append(
            (stay_id, PROPERTY_ID, mid, guest, d0, d0 + timedelta(days=nights), nights, net, cancelled, None)
        )
        if not cancelled and net > 0:
            add_wallet(mid, d0 + timedelta(days=nights), net, "stay_settlement", stay_id)

    # --- self-op F&B / retail POS + IRD ---
    for i in range(1, 800):
        tid += 1
        txn_id = f"T{tid:05d}"
        d = start + timedelta(days=rng.randint(0, (end - start).days))
        identified = rng.random() < 0.65
        mid = f"M{rng.randint(1, n_members):04d}" if identified else None
        guest = f"GX{tid:05d}"
        roll = rng.random()
        if roll < 0.55:
            outlet = rng.choice(["FB_SELF_1", "FB_SELF_2", "FB_SELF_3"])
            bucket = "fb_self_op"
            amount = round(25 + rng.random() * 90, 2)
            path = "pos"
        elif roll < 0.75:
            outlet = "RET_SELF_1"
            bucket = "retail_self_op"
            amount = round(15 + rng.random() * 80, 2)
            path = "pos"
        else:
            outlet = "HTL_IRD"
            bucket = "hotel_other"
            amount = round(20 + rng.random() * 60, 2)
            path = "pos"
        txn_rows.append((txn_id, outlet, mid, guest, d, bucket, amount, path, None, None, None))
        add_wallet(mid, d, amount, "pos", txn_id)

    # --- paid standalone vouchers (shopping) + redemptions ---
    for i in range(1, 61):
        vid += 1
        voucher_id = f"V{vid:05d}"
        mid = f"M{rng.randint(1, n_members):04d}"
        issued = start + timedelta(days=rng.randint(30, 600))
        face = float(rng.choice([50, 100, 150]))
        w = add_wallet(mid, issued, face, "voucher_purchase", voucher_id)
        status = "open"
        voucher_rows.append((voucher_id, "paid_standalone", face, issued, mid, None, w, status))
        if rng.random() < 0.7:
            rid += 1
            outlet = rng.choice(["RET_LEASE_1", "RET_LEASE_2", "RET_SELF_1", "FB_LEASE_1"])
            rdate = issued + timedelta(days=rng.randint(1, 90))
            redeem_rows.append((f"R{rid:05d}", voucher_id, outlet, rdate, face, mid))
            voucher_rows[-1] = (voucher_id, "paid_standalone", face, issued, mid, None, w, "redeemed")
            # Self-op redemption → pillar revenue, NOT second wallet cash
            if outlets[outlet]["operating_model"] == "self_op":
                tid += 1
                bucket = "retail_self_op" if outlets[outlet]["pillar"] == "retail" else "fb_self_op"
                txn_rows.append(
                    (
                        f"T{tid:05d}",
                        outlet,
                        mid,
                        None,
                        rdate,
                        bucket,
                        face,
                        "voucher_redeem_self_op",
                        None,
                        voucher_id,
                        None,
                    )
                )

    # --- comp vouchers (no wallet, no revenue) ---
    for i in range(1, 16):
        vid += 1
        voucher_id = f"V{vid:05d}"
        mid = f"M{rng.randint(1, n_members):04d}"
        issued = start + timedelta(days=rng.randint(40, 650))
        face = 50.0
        voucher_rows.append((voucher_id, "comp", face, issued, mid, None, None, "redeemed"))
        rid += 1
        redeem_rows.append(
            (
                f"R{rid:05d}",
                voucher_id,
                "RET_LEASE_2",
                issued + timedelta(days=10),
                face,
                mid,
            )
        )

    # --- Q15 packages ---
    # 1) Tenant breakfast + shopping voucher (liabilities)
    pkg_i += 1
    package_id = f"PKG{pkg_i:03d}"
    mid = "M0001"
    sold = date(start_year, 6, 15)
    cash = 400.0
    w = add_wallet(mid, sold, cash, "package_purchase", package_id)
    package_rows.append((package_id, sold, mid, cash, w, "tenant_breakfast_and_shop"))
    # liabilities first by face, remainder to room
    tenant_bf = 80.0
    shop = 100.0
    room = cash - tenant_bf - shop
    for ctype, outlet, face, recog, status, amt in [
        ("tenant_meal", "FB_LEASE_1", tenant_bf, "liability", "settled_liability", tenant_bf),
        ("shopping_voucher", "RET_LEASE_1", shop, "liability", "settled_liability", shop),
        ("room", None, room, "ir_revenue", "recognized", room),
    ]:
        comp_i += 1
        component_rows.append(
            (f"PC{comp_i:04d}", package_id, ctype, outlet, face, recog, amt, status)
        )
    stay_rows.append(
        (
            f"S{sid+1:05d}",
            PROPERTY_ID,
            mid,
            f"GPKG{pkg_i}",
            sold,
            sold + timedelta(days=2),
            2,
            room,
            False,
            package_id,
        )
    )
    sid += 1
    # shopping voucher issue+redeem at tenant (no retail revenue)
    vid += 1
    voucher_id = f"V{vid:05d}"
    voucher_rows.append(
        (voucher_id, "paid_package", shop, sold, mid, package_id, w, "redeemed")
    )
    rid += 1
    redeem_rows.append((f"R{rid:05d}", voucher_id, "RET_LEASE_1", sold + timedelta(days=1), shop, mid))

    # 2) Self-op breakfast package
    pkg_i += 1
    package_id = f"PKG{pkg_i:03d}"
    mid = "M0002"
    sold = date(start_year, 9, 10)
    cash = 350.0
    w = add_wallet(mid, sold, cash, "package_purchase", package_id)
    package_rows.append((package_id, sold, mid, cash, w, "self_op_breakfast"))
    bf = 60.0
    room = cash - bf
    for ctype, outlet, face, recog, status, amt in [
        ("fb_self_op", "FB_SELF_1", bf, "ir_revenue", "recognized", bf),
        ("room", None, room, "ir_revenue", "recognized", room),
    ]:
        comp_i += 1
        component_rows.append(
            (f"PC{comp_i:04d}", package_id, ctype, outlet, face, recog, amt, status)
        )
    tid += 1
    txn_rows.append(
        (
            f"T{tid:05d}",
            "FB_SELF_1",
            mid,
            None,
            sold + timedelta(days=1),
            "fb_self_op",
            bf,
            "package_component",
            None,
            None,
            package_id,
        )
    )

    # 3) Self-op folio dinner (not a package) — I21
    tid += 1
    folio_txn = f"T{tid:05d}"
    mid = "M0003"
    d = date(start_year + 1, 2, 20)
    stay_for_folio = f"S{sid+1:05d}"
    sid += 1
    stay_rows.append(
        (
            stay_for_folio,
            PROPERTY_ID,
            mid,
            "GFOLIO1",
            d,
            d + timedelta(days=1),
            1,
            200.0,
            False,
            None,
        )
    )
    add_wallet(mid, d + timedelta(days=1), 200.0, "stay_settlement", stay_for_folio)
    amount = 85.0
    txn_rows.append(
        (
            folio_txn,
            "FB_SELF_2",
            mid,
            "GFOLIO1",
            d,
            "fb_self_op",
            amount,
            "folio",
            stay_for_folio,
            None,
            None,
        )
    )
    add_wallet(mid, d + timedelta(days=1), amount, "folio_settlement", folio_txn)

    # --- breakage sample ---
    tid += 1
    txn_rows.append(
        (
            f"T{tid:05d}",
            "HTL_IRD",
            "M0010",
            None,
            date(start_year + 1, 11, 30),
            "hotel_other",
            40.0,
            "breakage",
            None,
            None,
            None,
        )
    )

    # --- points redeem (not wallet, not revenue) ---
    pid += 1
    points_rows.append((f"P{pid:05d}", "M0005", date(start_year + 1, 5, 1), -100.0, "redeem", None))

    # --- tenant reported counts (no amount) ---
    for i, oid in enumerate(["RET_LEASE_1", "RET_LEASE_2", "FB_LEASE_1"], start=1):
        report_rows.append(
            (
                f"TR{i:03d}",
                oid,
                date(start_year + 1, 1, 1),
                date(start_year + 1, 3, 31),
                rng.randint(20, 80),
            )
        )

    # --- members who only redeem tenant vouchers in a window (for Q14 samples) ---
    for i in range(1, 6):
        mid = f"M{100 + i:04d}"
        vid += 1
        voucher_id = f"V{vid:05d}"
        issued = date(start_year + 1, 10, 1)
        # funded earlier so not in last-90d wallet if we freeze "today" = end
        w = add_wallet(mid, date(start_year, 1, 15), 100.0, "voucher_purchase", voucher_id)
        voucher_rows.append((voucher_id, "paid_standalone", 100.0, issued, mid, None, w, "redeemed"))
        rid += 1
        redeem_rows.append(
            (f"R{rid:05d}", voucher_id, "RET_LEASE_3", date(start_year + 1, 11, 15), 100.0, mid)
        )

    con.executemany("INSERT INTO stays VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", stay_rows)
    con.executemany(
        "INSERT INTO self_op_transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        txn_rows,
    )
    con.executemany(
        "INSERT INTO wallet_cash_events VALUES (?, ?, ?, ?, ?, ?)",
        wallet_rows,
    )
    con.executemany("INSERT INTO points_ledger VALUES (?, ?, ?, ?, ?, ?)", points_rows)
    con.executemany("INSERT INTO vouchers VALUES (?, ?, ?, ?, ?, ?, ?, ?)", voucher_rows)
    con.executemany(
        "INSERT INTO voucher_redemptions VALUES (?, ?, ?, ?, ?, ?)",
        redeem_rows,
    )
    con.executemany("INSERT INTO packages VALUES (?, ?, ?, ?, ?, ?)", package_rows)
    con.executemany(
        "INSERT INTO package_components VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        component_rows,
    )
    con.executemany(
        "INSERT INTO tenant_reported_redemption_counts VALUES (?, ?, ?, ?, ?)",
        report_rows,
    )

    # Recompute end-of-period tiers from lifetime wallet cash (simple bands)
    cash_by_member = con.execute(
        """
        SELECT member_id, SUM(amount) AS s
        FROM wallet_cash_events
        WHERE member_id IS NOT NULL
        GROUP BY 1
        """
    ).fetchall()
    for mid, total in cash_by_member:
        if total >= 3000:
            tier = "Tier 3"
        elif total >= 1200:
            tier = "Tier 2"
        else:
            tier = "Tier 1"
        con.execute("UPDATE members SET tier = ? WHERE member_id = ?", [tier, mid])

    # High-value threshold candidate: ~75th percentile of trailing 12m cash at end
    trailing_start = date(start_year + 1, 1, 1)
    rows = con.execute(
        """
        SELECT member_id, SUM(amount) AS s
        FROM wallet_cash_events
        WHERE member_id IS NOT NULL
          AND event_date >= ?
          AND event_date <= ?
        GROUP BY 1
        ORDER BY 2
        """,
        [trailing_start, end],
    ).fetchall()
    amounts = [r[1] for r in rows] or [0.0]
    idx = max(0, min(len(amounts) - 1, math.ceil(0.75 * len(amounts)) - 1))
    raw = amounts[idx]
    # Nice round number
    threshold = float(max(500, int(round(raw / 100.0) * 100)))
    stats.high_value_threshold = threshold

    con.execute("INSERT INTO meta VALUES (?, ?)", ["seed", str(seed)])
    con.execute("INSERT INTO meta VALUES (?, ?)", ["property_id", PROPERTY_ID])
    con.execute("INSERT INTO meta VALUES (?, ?)", ["start_date", start.isoformat()])
    con.execute("INSERT INTO meta VALUES (?, ?)", ["end_date", end.isoformat()])
    con.execute(
        "INSERT INTO meta VALUES (?, ?)",
        ["high_value_threshold_suggested", str(threshold)],
    )
    con.execute("INSERT INTO meta VALUES (?, ?)", ["as_of_date", end.isoformat()])
    con.close()
    return stats


def lock_high_value_threshold(
    threshold: float,
    *,
    semantic_path: Path | None = None,
) -> None:
    """Write threshold into config/semantic.yaml (WP-206)."""
    import re

    path = semantic_path or (REPO_ROOT / "config" / "semantic.yaml")
    text = path.read_text(encoding="utf-8")
    text2, n = re.subn(
        r"(wallet_cash_threshold:\s*)null",
        rf"\g<1>{int(threshold)}",
        text,
        count=1,
    )
    if n != 1:
        text2, n = re.subn(
            r"(wallet_cash_threshold:\s*)\d+",
            rf"\g<1>{int(threshold)}",
            text,
            count=1,
        )
    text2 = text2.replace(
        'threshold_status: "pending_data_freeze"',
        'threshold_status: "locked_after_data_freeze"',
        1,
    )
    path.write_text(text2, encoding="utf-8")


if __name__ == "__main__":
    s = generate()
    print(s)
