# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY data/documents ./data/documents
COPY eval ./eval
COPY scripts ./scripts
COPY docs ./docs

RUN pip install --no-cache-dir -e ".[api]"

# Synthetic DB is gitignored — build at image build time for a ready container
RUN python scripts/rebuild_db.py && python scripts/build_goldens.py

EXPOSE 8080

CMD ["python", "-m", "api.server"]
