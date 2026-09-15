"""Read-only SQL tool with table/column allowlists and write rejection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from ecia.data.generate import DEFAULT_DB_PATH

# Guest-identifying columns are never selected by default tools.
FORBIDDEN_COLUMNS = {
    "display_name",
    "phone",
    "email",
    "full_name",
    "address",
}

ALLOWED_TABLES = {
    "members",
    "outlets",
    "stays",
    "self_op_transactions",
    "wallet_cash_events",
    "points_ledger",
    "vouchers",
    "voucher_redemptions",
    "tenant_reported_redemption_counts",
    "packages",
    "package_components",
    "campaigns",
    "campaign_contacts",
    "meta",
}

WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|COPY|EXPORT|IMPORT|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

ROW_CAP = 100


@dataclass
class SqlResult:
    ok: bool
    rows: list[dict[str, Any]] | None = None
    error: str | None = None
    sql: str | None = None


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def validate_readonly_sql(sql: str) -> str | None:
    """Return error message if SQL is not allowed; else None."""
    cleaned = _strip_comments(sql)
    if not cleaned:
        return "Empty SQL"
    if WRITE_RE.search(cleaned):
        return "Write/DDL statements are forbidden"
    if ";" in cleaned.rstrip(";"):
        return "Multiple statements are forbidden"
    # Require a SELECT or WITH
    if not re.match(r"^(WITH|SELECT)\b", cleaned, re.IGNORECASE):
        return "Only SELECT/WITH queries are allowed"
    # Table allowlist: crude FROM/JOIN capture
    tables = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", cleaned, re.IGNORECASE)
    for t in tables:
        if t.lower() not in ALLOWED_TABLES:
            return f"Table not allowed: {t}"
    for col in FORBIDDEN_COLUMNS:
        if re.search(rf"\b{col}\b", cleaned, re.IGNORECASE):
            return f"Column not allowed (PII minimization): {col}"
    return None


def run_sql(sql: str, *, db_path: Path | None = None, row_cap: int = ROW_CAP) -> SqlResult:
    err = validate_readonly_sql(sql)
    if err:
        return SqlResult(ok=False, error=err, sql=sql)
    path = db_path or DEFAULT_DB_PATH
    if not path.exists():
        return SqlResult(ok=False, error=f"DB missing: {path}", sql=sql)
    con = duckdb.connect(str(path), read_only=True)
    try:
        capped = f"SELECT * FROM ({_strip_comments(sql).rstrip(';')}) AS _q LIMIT {int(row_cap)}"
        cur = con.execute(capped)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return SqlResult(ok=True, rows=rows, sql=capped)
    except Exception as exc:  # noqa: BLE001 — surface DB errors to caller
        return SqlResult(ok=False, error=str(exc), sql=sql)
    finally:
        con.close()
