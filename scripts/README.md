# Scripts

## Rebuild synthetic database (I2+)

```bash
pip install -e ".[dev]"
python scripts/rebuild_db.py
```

Creates `data/synthetic/generated/ir01.duckdb` (fixed seed) and locks the high-value threshold in `config/semantic.yaml`.

**Do not run this on every test.** Pytest reuses the frozen DB when present.

## Ask (V1 CLI, no LLM required)

```bash
python -m agent.cli "過去 90 天活躍會員有多少？"
python -m agent.cli --question-id Q5 --json
python scripts/v1_smoke.py
```

`v1_smoke.py` reuses the frozen DB by default. Add `--rebuild` only when you changed the generator (slow).
