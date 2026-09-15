# Deploy (V3)

One-command local stack (builds synthetic DuckDB inside the image, then serves the API):

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Then:

```bash
curl -s http://127.0.0.1:8080/health
curl -s -X POST http://127.0.0.1:8080/ask -H "content-type: application/json" -d "{\"question_id\":\"Q5\"}"
```

Without Docker:

```bash
pip install -e ".[api]"
python scripts/rebuild_db.py   # once
python -m api.server
```

Host/port come from `config/app.yaml` → `api`.
