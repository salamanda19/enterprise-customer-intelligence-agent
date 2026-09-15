# Evaluation

Mandatory for V2. Contracts for SSOT Q1–Q15 (+ RevPAR) live in `questions/contracts.yaml`—**no expected amounts**.

## Layout

| Path | Role |
|---|---|
| `questions/contracts.yaml` | Base Q1–Q15 + RevPAR contracts |
| `questions/variants.yaml` | Template variants (reword / tier / period) |
| `goldens/q1_q15_goldens.json` | Full goldens from runner |
| `goldens/variant_goldens.json` | Variant goldens |
| `results/*_latest_summary.json` | Committed eval summaries |
| `results/runs/` | Large dumps (gitignored) |

## Behavioural gates (pre-registered)

- `response_mode` / reason codes vs contract = **100%**
- Prohibited claims = **0**
- Numeric figures vs golden = **100%**

Generative metrics (groundedness, explanation quality, naive gap, latency/cost) are calibrated after the first full run — see `docs/evaluation/`.

## Commands

```text
python scripts/build_goldens.py
python scripts/build_variant_goldens.py
python scripts/run_agent_eval.py --dry-gate
python scripts/run_agent_eval.py --with-naive
```

`--naive-llm` is optional and requires `config/secrets.yaml`; default naive path is an offline simulator (`naive-offline-v1`) so CI / weak PCs stay free.
