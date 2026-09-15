# Evaluation results (committed summaries)

- `agent_latest_summary.json` — deterministic agent vs goldens  
- `naive_latest_summary.json` — offline naive baseline  
- `agent_vs_naive_latest.json` — side-by-side (no pre-declared winner)  

Large per-run dumps live under `runs/` (gitignored). Regenerate:

```text
python scripts/run_agent_eval.py --with-naive
```
