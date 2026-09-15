#!/usr/bin/env python
"""Run the HTTP API (reads host/port from config/app.yaml).

    python -m api.server
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import uvicorn

from ecia.config_loader import REPO_ROOT, load_yaml


def main() -> None:
    cfg = load_yaml(REPO_ROOT / "config" / "app.yaml")
    api_cfg = cfg.get("api") or {}
    host = api_cfg.get("host", "127.0.0.1")
    port = int(api_cfg.get("port", 8080))
    uvicorn.run("api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
