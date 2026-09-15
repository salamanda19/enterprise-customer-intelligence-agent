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

## Goldens + I6 eval

```bash
python scripts/build_goldens.py
python scripts/build_variant_goldens.py
python scripts/run_agent_eval.py --dry-gate
python scripts/run_agent_eval.py --with-naive
```

Agent scoring fails closed without `eval/goldens/q1_q15_goldens.json`. Default naive baseline is offline (no API key).

## Demo (I7)

```bash
python scripts/demo.py          # in-process Q5 + Q7
python scripts/demo.py --http   # against python -m api.server
```

## API

```bash
pip install -e ".[api]"
python -m api.server
```
