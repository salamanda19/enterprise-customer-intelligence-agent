# Enterprise Customer Intelligence Agent

Grounded AI analytics for natural-language questions over a synthetic **non-gaming integrated resort** (hotel + F&B + retail + loyalty).

The LLM orchestrates tools. Numbers and business definitions come from a semantic layer, deterministic SQL/analytics, and approved documents—not from model memory.

## Status

**I1 (semantic / policy) in progress.** Planning is locked:

- [`docs/ssot.md`](docs/ssot.md) — product SSOT
- [`docs/implementation_plan.md`](docs/implementation_plan.md) — architecture & phases
- [`docs/work_plan.md`](docs/work_plan.md) — execution tasks

Physical DuckDB schema and the agent loop are **not** started yet (I2+). Do not treat chat as progress before M3 goldens.

## Intended architecture

```text
User question → Pre-flight policy
                 → Agent / tools (SQL RO, named metrics, RAG)
                 → Evidence pack
                 → Validation
                 → full | declare | downgrade | refuse + reason codes + figures
```

## Repository layout

| Path | Purpose |
|------|---------|
| `src/` | Packages: `semantic`, `policy`, `tools`, `agent`, `validation`, `ecia` |
| `config/` | `app.yaml`, `semantic.yaml`, `policy.yaml` (behaviour); secrets gitignored |
| `data/` | Synthetic IR world + approved documents (generator in I2) |
| `eval/questions/` | Q1–Q15 + RevPAR contracts (no amounts yet) |
| `tests/invariants/` | I1–I21 catalog |
| `docs/` | SSOT, plans, later architecture / evaluation / writeup |
| `scripts/` | Rebuild helpers (I2+) |
| `deploy/` | Docker later (V3) |

## Delivery stages

1. **V1** — Semantic/policy first, then synthetic data, golden runner, CLI agent with real downgrade/refuse  
2. **V2** — Full Q1–Q15, validators, naive-LLM baseline, failure analysis  
3. **V3** — API, Docker, CI, cost/latency, writeup, demo  

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

Copy `config/secrets.example.yaml` → `config/secrets.yaml` when you need an API key (optional; V1 CLI does not call the LLM).

```bash
python scripts/rebuild_db.py      # once / when schema changes (heavier)
python scripts/build_goldens.py   # refresh numeric goldens
python -m agent.cli --question-id Q5 --json
python scripts/v1_smoke.py        # light smoke; no rebuild by default
```

## Next implementation slice

**I5** per [`docs/work_plan.md`](docs/work_plan.md): remaining metrics (Q2/Q11/Q12/Q15), full goldens, validators.
