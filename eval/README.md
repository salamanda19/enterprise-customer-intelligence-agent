# Evaluation

Mandatory for V2. Target a 50–100 question benchmark.

## Question categories

- Simple SQL
- Analytical
- Multi-step
- Knowledge retrieval
- Causal reasoning (expect refusal / association-not-causation)
- Adversarial / unsupported

## Metrics (targets after baseline exists)

SQL correctness, numerical correctness, retrieval accuracy, groundedness, refusal accuracy, latency, cost.

## Baseline

Compare a minimal RAG/LLM path against the tool-using agent. Results must be measured, not assumed.

`questions/` — benchmark items  
`baseline/` — baseline runner (later)  
`results/` — committed summaries; ignore large run dumps
