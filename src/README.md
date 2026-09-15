# Source

Application code. The LLM is not the source of truth for numbers or business definitions.

## Packages

| Package | Role |
|---------|------|
| `ecia/` | Shared helpers (config loader, repo paths) |
| `semantic/` | SSOT projection loaders / helpers (definitions in `config/semantic.yaml`) |
| `policy/` | Response modes, reason codes, pre-flight boundaries (not IAM) |
| `tools/sql/` | Read-only SQL (I4) |
| `tools/analytics/` | Named deterministic metrics (I3+) |
| `tools/rag/` | Approved-document retrieval as **data** (I4) |
| `agent/` | Single orchestrating agent (I4; no multi-agent unless later evidence) |
| `validation/` | Guardrails, figures vs evidence, mode/reason checks |
| `api/` | HTTP surface (V3) |
| `explore/` | Local Explore service + Streamlit UI (I8; Ask / Explore / SQL) |

Canonical metric names follow SSOT (e.g. `net_room_revenue`, `hotel_pillar_total`, `fb_self_op_revenue`)—**not** proposal-era `booking_revenue`.

Existing `security/` scaffold is folded into `policy/` (pre-flight) and `validation/` (output); do not add a third source of truth there.
