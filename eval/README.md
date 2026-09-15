# Evaluation

Mandatory for V2. Contracts for SSOT Q1–Q15 (+ RevPAR) live in `questions/contracts.yaml` from I1—**no expected amounts**.

## Question types (SSOT §15)

- Deterministic
- Analytical
- Knowledge
- Should-refuse (may still downgrade or attach allowed subsets)

Plus four **response modes**: full / declare / downgrade / refuse, with reason codes.

## Metrics

Behavioural gates are pre-registered (mode/reason 100%, prohibited claims 0, figures match golden). Generative metrics (groundedness quality, naive-LLM gap, latency/cost) are set after the first full V2 run.

## Baseline naming

- **golden runner** — deterministic metrics vs frozen DB  
- **naive-LLM baseline** — minimal RAG/LLM path for comparison  

`questions/` — contracts  
`baseline/` — naive runner (later)  
`goldens/` — generated later (I3+)  
`results/` — committed summaries; ignore large run dumps
