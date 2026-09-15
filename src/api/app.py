"""HTTP API (V3): same structured output contract as CLI."""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.orchestrator import handle
from ecia.config_loader import REPO_ROOT, load_yaml


def _app_cfg() -> dict[str, Any]:
    return load_yaml(REPO_ROOT / "config" / "app.yaml")


def attach_meta(payload: dict[str, Any], *, latency_ms: float) -> dict[str, Any]:
    """Stable cost/latency fields for demos and eval (WP-704)."""
    cfg = _app_cfg()
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


class AskRequest(BaseModel):
    question: str | None = Field(default=None, description="Natural-language question")
    question_id: str | None = Field(default=None, description="Contract id e.g. Q5")


def create_app() -> FastAPI:
    api = FastAPI(
        title="Enterprise Customer Intelligence Agent",
        version="0.1.0",
        description="Grounded IR analytics API — same output contract as CLI.",
    )

    @api.get("/health")
    def health() -> dict[str, Any]:
        cfg = _app_cfg()
        db = REPO_ROOT / cfg["paths"]["duckdb_path"]
        return {
            "status": "ok",
            "db_present": db.exists(),
            "property_id": cfg.get("runtime", {}).get("property_id"),
            "prompt_version": cfg.get("eval", {}).get("agent_prompt_version"),
        }

    @api.post("/ask")
    def ask(body: AskRequest) -> dict[str, Any]:
        question = (body.question or "").strip() or None
        qid = body.question_id
        if not question and not qid:
            raise HTTPException(status_code=400, detail="Provide question and/or question_id")
        if qid and not question:
            contracts = load_yaml(REPO_ROOT / "eval" / "questions" / "contracts.yaml")["questions"]
            by_id = {c["id"]: c for c in contracts}
            if qid not in by_id:
                raise HTTPException(status_code=404, detail=f"Unknown question_id: {qid}")
            question = by_id[qid]["prompt"]
        assert question is not None
        t0 = time.perf_counter()
        result = handle(question, question_id=qid)
        return attach_meta(result, latency_ms=(time.perf_counter() - t0) * 1000)

    return api


app = create_app()
