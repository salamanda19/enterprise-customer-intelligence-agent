# Source

Application code will live here. Do not treat the LLM as the source of truth for numbers or business definitions.

Planned packages (empty until implementation):

- `agent/` — single orchestrating agent (V1; no multi-agent unless later evidence requires it)
- `tools/sql/` — read-only SQL tool
- `tools/analytics/` — deterministic Python analytics
- `tools/rag/` — document retrieval
- `semantic/` — explicit business definitions (active_customer, booking_revenue, etc.)
- `validation/` — SQL, numerical, and evidence checks
- `security/` — prompt-injection handling, data minimization, refusal
- `api/` — HTTP surface (V3)
