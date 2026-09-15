"""Load checked-in YAML config (behaviour lives here, not in environment variables)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_APP_CONFIG = REPO_ROOT / "config" / "app.yaml"


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_app_config(path: Path | None = None) -> dict[str, Any]:
    return load_yaml(path or DEFAULT_APP_CONFIG)


def resolve_repo_path(relative: str, *, repo_root: Path | None = None) -> Path:
    root = repo_root or REPO_ROOT
    return (root / relative).resolve()
