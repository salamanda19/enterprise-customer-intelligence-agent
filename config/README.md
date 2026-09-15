# Configuration

Runtime behaviour is consolidated in YAML under this directory (not environment-variable sprawl).

| File | Role |
|------|------|
| `app.yaml` | Paths, DuckDB, model name, routing, explore UI caps |
| `semantic.yaml` | SSOT projection: entities, defaults, tiers, metrics |
| `policy.yaml` | Modes, reason codes, conflict rule, out-of-scope cues |
| `secrets.example.yaml` | Template for API keys |
| `secrets.yaml` | Local secrets (**gitignored**) |

```bash
copy config\secrets.example.yaml config\secrets.yaml
```
