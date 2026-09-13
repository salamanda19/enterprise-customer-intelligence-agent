# Enterprise Customer Intelligence Agent

A grounded AI analytics system for natural-language exploration of customer and marketing data.

This repository is the implementation home for a hospitality/retail **enterprise customer intelligence** prototype. The LLM orchestrates tools; numerical answers and business definitions come from deterministic SQL, analytics, and an explicit semantic layer.

## Status

Scaffold only. Scope, schema, and stack are not locked yet. Implementation has not started.

## Intended architecture (V1+)

```text
User question → Agent orchestration
                 ├── SQL / database (read-only)
                 ├── Python analytics
                 ├── Document retrieval (RAG)
                 └── Business metadata / semantic layer
                              ↓
                    Validation / guardrails
                              ↓
                    Answer + evidence
```

## Repository layout

| Path | Purpose |
|------|---------|
| `src/` | Agent, tools, semantic layer, validation, security |
| `data/` | Synthetic enterprise data and unstructured documents |
| `config/` | Non-secret configuration (YAML/Python), not environment-variable sprawl |
| `eval/` | Benchmark questions, metrics, baseline comparison |
| `tests/` | Automated tests (added from V2/V3) |
| `docs/` | Architecture, evaluation report, technical write-up |
| `scripts/` | Data generation and operational helpers |
| `deploy/` | Docker / later packaging (V3) |

## Delivery stages

1. **V1 — Working prototype**: synthetic data, SQL tool, basic RAG, single agent, representative questions.
2. **V2 — Reliability**: semantic layer, benchmark, validation, refusal, baseline comparison, failure analysis.
3. **V3 — Production-oriented polish**: API, Docker, CI, logging, cost/latency, documentation, demo.

## Explicit non-goals (especially V1)

General-purpose autonomous agents, unjustified multi-agent frameworks, a full EDW, production IAM, Kubernetes, microservice sprawl, a polished frontend, or a ChatGPT clone.

## Next steps before coding

1. Lock business scenario and synthetic schema.
2. Define 10–15 representative questions by type (SQL / analytical / RAG / multi-tool / refusal).
3. Freeze minimum V1 architecture and technology stack.
4. Implement the simplest end-to-end baseline.
