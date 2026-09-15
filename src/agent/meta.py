"""Stable cost/latency meta fields shared by CLI and HTTP (WP-704)."""

from __future__ import annotations

from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml


def attach_meta(payload: dict[str, Any], *, latency_ms: float) -> dict[str, Any]:
    """Attach model / prompt / latency fields for demos and eval."""
    cfg = load_yaml(REPO_ROOT / "config" / "app.yaml")
    out = dict(payload)
    meta = dict(out.get("meta") or {})
    meta.update(
        {
            "latency_ms": round(latency_ms, 2),
            "model": cfg.get("llm", {}).get("model"),
            "prompt_version": cfg.get("eval", {}).get("agent_prompt_version"),
            "routing_deterministic_first": bool(
                cfg.get("routing", {}).get("deterministic_first", True)
            ),
            "token_usage": meta.get("token_usage") or {"prompt": 0, "completion": 0, "total": 0},
        }
    )
    out["meta"] = meta
    return out
