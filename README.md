# Enterprise Customer Intelligence Agent

Grounded AI analytics for natural-language questions over a synthetic **non-gaming integrated resort** (hotel + F&B + retail + loyalty).

Numbers and definitions come from a semantic layer, deterministic SQL/analytics, and approved documents—not from model memory. The default path is **deterministic-first** (no LLM required).

## Status

**I1–I8 complete** (V1 CLI → V2 eval → V3 packaging → optional local Explore UI).

- [`docs/ssot.md`](docs/ssot.md) — product SSOT  
- [`docs/implementation_plan.md`](docs/implementation_plan.md) — architecture & phases  
- [`docs/work_plan.md`](docs/work_plan.md) — execution tasks  
- [`docs/architecture/overview.md`](docs/architecture/overview.md) — system diagram  
- [`docs/writeup/technical_writeup.md`](docs/writeup/technical_writeup.md) — technical writeup  
- [`docs/evaluation/`](docs/evaluation/) — failure analysis & generative targets  

## Architecture (short)

```text
User question → Pre-flight policy
                 → Deterministic router / tools (metrics, SQL RO, RAG)
                 → Evidence pack → Validation
                 → full | declare | downgrade | refuse + reason codes + figures
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev,api,explore]"
python scripts/rebuild_db.py      # once / when schema changes
python scripts/build_goldens.py
pytest
```

Copy `config/secrets.example.yaml` → `config/secrets.yaml` only if you need a live LLM naive baseline.

## CLI / demo / eval

```bash
python -m agent.cli --question-id Q5 --json
python scripts/demo.py                 # Q5 downgrade + Q7 refuse (real outputs)
python scripts/run_agent_eval.py --with-naive
```

## HTTP API

```bash
python -m api.server
# GET  /health
# POST /ask  {"question_id":"Q5"}  or  {"question":"..."}
```

Host/port: `config/app.yaml` → `api`.

## Docker

```bash
docker compose -f deploy/docker-compose.yml up --build
```

See [`deploy/README.md`](deploy/README.md).

## Local Explore UI (I8)

Thin Streamlit surface over the same `handle()` / explore service / `run_sql()` — not a product UI.

```bash
pip install -e ".[explore]"
streamlit run src/explore/ui.py
```

Tabs: **Ask** (structured agent response), **Explore** (preview / `SUMMARIZE` / group-by; push-down), **SQL** (read-only, row-capped). Behaviour constants: `config/app.yaml` → `explore`.

## Repository layout

| Path | Purpose |
|------|---------|
| `src/` | `agent`, `policy`, `tools`, `validation`, `ecia`, `api`, `agent_eval`, `explore` |
| `config/` | Behaviour YAML (secrets gitignored) |
| `data/` | Documents + synthetic generator (DB gitignored) |
| `eval/` | Contracts, goldens, result summaries |
| `deploy/` | Dockerfile + compose |
| `.github/workflows/` | CI (no live LLM) |
