# Tests

Automated tests start at I1 (config/contract smoke). Data invariants and agent behaviour grow in I2–I4; CI emphasis increases in V3.

| Area | When |
|------|------|
| Unit: YAML / contracts load | I1 (`tests/unit/`) |
| Data invariants | I2 (`tests/invariants/` + pytest) |
| Metrics / goldens | I3+ |
| Agent behaviour (downgrade/refuse) | I4+ |
| Integration / CI sampling | V2–V3 |

Automated tests prefer the **frozen** DuckDB at `data/synthetic/generated/ir01.duckdb` and do **not** regenerate it on every run (slow on weak machines). Rebuild only via `python scripts/rebuild_db.py` when the generator/schema changes.
