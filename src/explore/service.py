"""Explore service: engine-side preview / summarize / aggregate (WP-802 / WP-803).

Aggregations never apply a detail row-cap before computing means. Detail caps
belong to preview and free-form run_sql only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import duckdb

from ecia.config_loader import load_app_config, resolve_repo_path
from ecia.data.generate import DEFAULT_DB_PATH
from tools.sql.readonly import ALLOWED_TABLES, FORBIDDEN_COLUMNS

AggFn = Literal["count", "sum", "avg", "min", "max"]
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SMALL_TABLE_ROWS = 50_000


class ExploreError(ValueError):
    """Invalid explore request (whitelist, args, or policy)."""


@dataclass
class ExploreResult:
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    sql: list[str] = field(default_factory=list)


def _explore_cfg() -> dict[str, Any]:
    return dict(load_app_config().get("explore") or {})


def _db_path(db_path: Path | None = None) -> Path:
    if db_path is not None:
        return db_path
    cfg = load_app_config()
    rel = (cfg.get("paths") or {}).get("duckdb_path")
    if rel:
        return resolve_repo_path(rel)
    return DEFAULT_DB_PATH


def _connect(path: Path) -> duckdb.DuckDBPyConnection:
    if not path.exists():
        raise ExploreError(f"DB missing: {path}")
    return duckdb.connect(str(path), read_only=True)


def _require_table(table: str) -> str:
    if not _IDENT.match(table) or table.lower() not in ALLOWED_TABLES:
        raise ExploreError(f"Table not allowed: {table}")
    return table.lower()


def _require_column(col: str, *, allowed: set[str]) -> str:
    if not _IDENT.match(col):
        raise ExploreError(f"Invalid column name: {col}")
    low = col.lower()
    if low in FORBIDDEN_COLUMNS:
        raise ExploreError(f"Column not allowed (PII minimization): {col}")
    if low not in allowed:
        raise ExploreError(f"Column not on table: {col}")
    return low


def list_tables(*, db_path: Path | None = None) -> list[str]:
    """Return allowlisted tables that exist in the DB."""
    path = _db_path(db_path)
    con = _connect(path)
    try:
        present = {
            r[0].lower()
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        return sorted(t for t in ALLOWED_TABLES if t in present)
    finally:
        con.close()


def table_columns(table: str, *, db_path: Path | None = None) -> list[dict[str, str]]:
    """Column metadata for an allowlisted table (excludes forbidden PII names)."""
    t = _require_table(table)
    path = _db_path(db_path)
    con = _connect(path)
    try:
        rows = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'main' AND lower(table_name) = ? "
            "ORDER BY ordinal_position",
            [t],
        ).fetchall()
        out: list[dict[str, str]] = []
        for name, dtype in rows:
            if name.lower() in FORBIDDEN_COLUMNS:
                continue
            out.append({"name": name, "type": str(dtype)})
        return out
    finally:
        con.close()


def _column_names(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(
        "SELECT lower(column_name) FROM information_schema.columns "
        "WHERE table_schema = 'main' AND lower(table_name) = ?",
        [table],
    ).fetchall()
    return {r[0] for r in rows}


def _row_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _scan_relation(
    table: str,
    *,
    row_count: int,
    full_scan: bool | None,
    sample_rows: int | None,
    cfg: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Return (FROM-clause fragment, scan meta). Never wraps aggregates in LIMIT."""
    default_sample = int(cfg.get("default_sample_rows") or 10_000)
    allow_full = bool(cfg.get("allow_full_scan", True))
    n = sample_rows if sample_rows is not None else default_sample

    use_full: bool
    if full_scan is True:
        if not allow_full and row_count > _SMALL_TABLE_ROWS:
            raise ExploreError("Full scan disabled for large tables (allow_full_scan=false)")
        use_full = True
    elif full_scan is False:
        use_full = False
    else:
        # Auto: small tables full scan; larger tables sample unless allow_full and under threshold
        use_full = row_count <= max(n, _SMALL_TABLE_ROWS) or (
            allow_full and row_count <= _SMALL_TABLE_ROWS
        )

    if use_full or row_count <= n:
        return table, {"scan_mode": "full", "row_count": row_count, "sample_rows": None}

    # DuckDB TABLESAMPLE SYSTEM (percentage)
    pct = max(0.01, min(100.0, 100.0 * n / max(row_count, 1)))
    rel = f"(SELECT * FROM {table} TABLESAMPLE SYSTEM ({pct})) AS _sample"
    return rel, {
        "scan_mode": "sample",
        "row_count": row_count,
        "sample_rows": n,
        "sample_pct": pct,
    }


def preview(
    table: str,
    *,
    limit: int | None = None,
    offset: int = 0,
    sample: bool = False,
    db_path: Path | None = None,
) -> ExploreResult:
    """Return a capped detail preview. Never downloads the full table by default."""
    cfg = _explore_cfg()
    t = _require_table(table)
    cap = int(limit if limit is not None else cfg.get("preview_rows") or 100)
    if cap < 1 or cap > 1000:
        raise ExploreError("preview limit must be 1..1000")
    if offset < 0:
        raise ExploreError("offset must be >= 0")

    path = _db_path(db_path)
    sqls: list[str] = []
    try:
        con = _connect(path)
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc))

    try:
        n = _row_count(con, t)
        sqls.append(f"SELECT COUNT(*) FROM {t}")
        if sample and n > 0:
            pct = max(0.01, min(100.0, 100.0 * cap / n))
            sql = (
                f"SELECT * FROM {t} TABLESAMPLE SYSTEM ({pct}) "
                f"LIMIT {cap}"
            )
        else:
            sql = f"SELECT * FROM {t} LIMIT {cap} OFFSET {offset}"
        sqls.append(sql)
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        # Drop forbidden columns if present in schema (defense in depth)
        keep = [c for c in cols if c.lower() not in FORBIDDEN_COLUMNS]
        rows = []
        for r in cur.fetchall():
            row = dict(zip(cols, r))
            rows.append({k: row[k] for k in keep})
        return ExploreResult(
            ok=True,
            data={
                "table": t,
                "row_count": n,
                "preview_rows": len(rows),
                "offset": offset,
                "sample": sample,
                "columns": keep,
                "rows": rows,
            },
            sql=sqls,
        )
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    except Exception as exc:  # noqa: BLE001
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    finally:
        con.close()


def summarize(
    table: str,
    *,
    full_scan: bool | None = None,
    sample_rows: int | None = None,
    value_counts_top_k: int | None = None,
    db_path: Path | None = None,
) -> ExploreResult:
    """Column-level summary via engine SUMMARIZE + categorical top-K.

    Means/null rates are computed on the scan relation — never on a LIMIT of
    detail rows first.
    """
    cfg = _explore_cfg()
    t = _require_table(table)
    top_k = int(value_counts_top_k if value_counts_top_k is not None else cfg.get("value_counts_top_k") or 20)
    if top_k < 1 or top_k > 200:
        raise ExploreError("value_counts_top_k must be 1..200")

    path = _db_path(db_path)
    sqls: list[str] = []
    try:
        con = _connect(path)
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc))

    try:
        n = _row_count(con, t)
        sqls.append(f"SELECT COUNT(*) FROM {t}")
        rel, scan_meta = _scan_relation(
            t, row_count=n, full_scan=full_scan, sample_rows=sample_rows, cfg=cfg
        )

        # Prefer DuckDB SUMMARIZE on the relation (full table or sample subquery).
        if scan_meta["scan_mode"] == "full":
            sum_sql = f"SUMMARIZE SELECT * FROM {t}"
        else:
            sum_sql = f"SUMMARIZE SELECT * FROM {rel}"
        sqls.append(sum_sql)
        cur = con.execute(sum_sql)
        sum_cols = [d[0] for d in cur.description]
        summary_rows = [dict(zip(sum_cols, r)) for r in cur.fetchall()]
        # Filter PII columns from summary
        summary_rows = [
            r
            for r in summary_rows
            if str(r.get("column_name") or r.get("Column") or "").lower() not in FORBIDDEN_COLUMNS
        ]

        # Categorical top-K for low-cardinality / varchar-ish columns
        colnames = _column_names(con, t)
        value_counts: dict[str, list[dict[str, Any]]] = {}
        for row in summary_rows:
            cname = str(row.get("column_name") or "")
            if not cname or cname.lower() not in colnames:
                continue
            if cname.lower() in FORBIDDEN_COLUMNS:
                continue
            ctype = str(row.get("column_type") or row.get("type") or "").lower()
            approx_unique = row.get("approx_unique") or row.get("unique") or 0
            try:
                approx_unique = int(approx_unique)
            except (TypeError, ValueError):
                approx_unique = 0
            is_cat = any(x in ctype for x in ("varchar", "text", "enum", "bool")) or (
                approx_unique > 0 and approx_unique <= max(top_k * 5, 50)
            )
            if not is_cat:
                continue
            vc_sql = (
                f"SELECT {cname} AS value, COUNT(*) AS n FROM {rel} "
                f"GROUP BY 1 ORDER BY n DESC NULLS LAST LIMIT {top_k}"
            )
            sqls.append(vc_sql)
            vc_cur = con.execute(vc_sql)
            value_counts[cname] = [
                {"value": r[0], "count": int(r[1])} for r in vc_cur.fetchall()
            ]

        return ExploreResult(
            ok=True,
            data={
                "table": t,
                "scan": scan_meta,
                "summary": summary_rows,
                "value_counts": value_counts,
            },
            sql=sqls,
        )
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    except Exception as exc:  # noqa: BLE001
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    finally:
        con.close()


def aggregate(
    table: str,
    *,
    group_by: list[str],
    metrics: list[dict[str, str]],
    result_cap: int | None = None,
    full_scan: bool | None = None,
    sample_rows: int | None = None,
    db_path: Path | None = None,
) -> ExploreResult:
    """1–2 dimension group-by with count/sum/avg/min/max (engine-side).

    Result rows are capped with LIMIT on the *aggregated* result, not on the
    underlying fact scan used to compute the aggregates.
    """
    cfg = _explore_cfg()
    t = _require_table(table)
    if not group_by or len(group_by) > 2:
        raise ExploreError("group_by must have 1 or 2 columns")
    if not metrics:
        raise ExploreError("metrics required")

    cap = int(result_cap if result_cap is not None else cfg.get("aggregate_result_cap") or 50)
    if cap < 1 or cap > 500:
        raise ExploreError("aggregate_result_cap must be 1..500")

    path = _db_path(db_path)
    sqls: list[str] = []
    try:
        con = _connect(path)
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc))

    try:
        allowed = _column_names(con, t)
        dims = [_require_column(c, allowed=allowed) for c in group_by]

        select_parts: list[str] = list(dims)
        aliases: list[str] = list(dims)
        for i, m in enumerate(metrics):
            fn = (m.get("fn") or "").lower()
            col = m.get("column")
            alias = m.get("alias") or f"m{i}_{fn}"
            if not _IDENT.match(alias):
                raise ExploreError(f"Invalid metric alias: {alias}")
            if fn == "count" and (not col or col == "*"):
                select_parts.append(f"COUNT(*) AS {alias}")
            elif fn in ("sum", "avg", "min", "max"):
                if not col:
                    raise ExploreError(f"{fn} requires column")
                c = _require_column(col, allowed=allowed)
                select_parts.append(f"{fn.upper()}({c}) AS {alias}")
            else:
                raise ExploreError(f"Unsupported aggregate fn: {fn}")
            aliases.append(alias)

        n = _row_count(con, t)
        sqls.append(f"SELECT COUNT(*) FROM {t}")
        rel, scan_meta = _scan_relation(
            t, row_count=n, full_scan=full_scan, sample_rows=sample_rows, cfg=cfg
        )
        # LIMIT applies only to aggregated output — scan relation has no detail cap.
        sql = (
            f"SELECT {', '.join(select_parts)} FROM {rel} "
            f"GROUP BY {', '.join(str(i) for i in range(1, len(dims) + 1))} "
            f"ORDER BY 1 "
            f"LIMIT {cap}"
        )
        sqls.append(sql)
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return ExploreResult(
            ok=True,
            data={
                "table": t,
                "scan": scan_meta,
                "group_by": dims,
                "result_cap": cap,
                "columns": cols,
                "rows": rows,
            },
            sql=sqls,
        )
    except ExploreError as exc:
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    except Exception as exc:  # noqa: BLE001
        return ExploreResult(ok=False, error=str(exc), sql=sqls)
    finally:
        con.close()
