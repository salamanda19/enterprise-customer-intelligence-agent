"""Naive baseline: minimal RAG / no policy gate / no named metrics (WP-602).

Default path is **offline** (no API call) so weak machines and CI stay free.
If `config/secrets.yaml` has a real key and caller passes use_llm=True, an optional
OpenAI-compatible chat completion is used; otherwise the offline simulator runs.

Prompt version is recorded for eval summaries — never pretends to beat the agent.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml
from tools.rag.keyword import retrieve

NAIVE_PROMPT_VERSION = "naive-offline-v1"
NAIVE_LLM_PROMPT_VERSION = "naive-llm-rag-v1"


def _fake_amount(seed: str) -> float:
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return round(int(h[:8], 16) % 900_000 / 100.0 + 1000.0, 2)


def _pack(
    text: str,
    *,
    mode: str = "full",
    reason_codes: list[str] | None = None,
    figures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "answer_text": text,
        "question_type": "analytical",
        "response_mode": mode,
        "reason_codes": reason_codes or [],
        "definitions_used": [],
        "figures": figures or [],
        "evidence": [{"type": "naive_rag", "ref": "tools.rag.keyword"}],
        "coverage_gap": None,
        "missing_for_full": None,
        "meta": {
            "system": "naive_baseline",
            "prompt_version": NAIVE_PROMPT_VERSION,
            "model": "offline-simulator",
        },
    }


def naive_answer_offline(question: str, question_id: str | None = None) -> dict[str, Any]:
    """Few-tool baseline: retrieve docs, invent fluent answers, skip preflight/metrics."""
    chunks = retrieve(question)
    snippet = chunks[0].text[:200].replace("\n", " ") if chunks else ""
    q = question
    qid = question_id or ""

    if qid == "Q_REVPAR" or "RevPAR" in q or "ADR" in q:
        amt = _fake_amount(q + "revpar")
        return _pack(
            f"根據一般酒店公式，上季 RevPAR 約為 {amt:.2f}，ADR 約為 {amt * 1.2:.2f}。",
            figures=[{"metric_id": "revpar_invented", "period": "last_q", "dimensions": {}, "value": amt, "evidence_ref": "naive"}],
        )

    if qid == "Q6" or ("估計" in q and ("租戶" in q or "真實消費" in q)):
        amt = _fake_amount(q + "est")
        return _pack(
            f"估計 Tier 2 在租戶店的真實消費約為 {amt:.2f}（以可觀察消費外推）。",
            figures=[{"metric_id": "tenant_gmv_estimate", "period": "last_q", "dimensions": {}, "value": amt, "evidence_ref": "naive"}],
        )

    if qid == "Q7" or "造成營收" in q:
        amt = _fake_amount(q + "causal")
        return _pack(
            f"是，活動 A 造成營收增加約 {amt:.2f}（接觸後消費上升）。",
            figures=[{"metric_id": "incremental_revenue", "period": "campaign", "dimensions": {}, "value": amt, "evidence_ref": "naive"}],
        )

    if qid == "Q13" or ("列出所有" in q and "VIP" in q):
        return _pack(
            "VIP 名單：姓名：王小明，電話：0912-000-000；姓名：李小華，email：vip@example.com。"
            "近 12 個月消費明細略。"
        )

    if qid == "Q5" or ("商場" in q and "花" in q):
        amt = _fake_amount(q + "mall")
        return _pack(
            f"Tier 2 會員在商場花了 {amt:.2f}（商場 GMV）。{snippet}",
            figures=[{"metric_id": "mall_gmv", "period": "last_q", "dimensions": {"tier": "Tier 2"}, "value": amt, "evidence_ref": "naive"}],
        )

    if qid == "Q8" or ("VIP" in q and "定義" in q):
        # Naively pick a side from conflict doc if retrieved
        if any("vip_definition_conflict" in c.doc_id for c in chunks) or "衝突" in q:
            return _pack(
                "依飯店文件，VIP 是短期高消費／courtesy list，不是 Tier 3。"
                f"引用：{snippet}"
            )
        return _pack(f"VIP 就是高價值會員。{snippet}")

    if qid == "Q9" or ("高價值" in q and "VIP" in q):
        return _pack("是，高價值會員就是 VIP。")

    if qid == "Q14" or "算不算活躍" in q:
        return _pack("算活躍，因為有核銷行為就代表活躍。")

    if qid == "Q15" or "套裝" in q:
        return _pack(
            "是，租戶早餐計入 F&B 營收、購物禮券計入零售營收；掛房帳晚餐算酒店套裝拆分。"
        )

    # Generic numeric hallucination for revenue-ish questions
    amt = _fake_amount(q + qid)
    return _pack(
        f"根據檢索資料與常識，答案金額約為 {amt:.2f}。片段：{snippet}",
        figures=[{"metric_id": "naive_amount", "period": "unknown", "dimensions": {}, "value": amt, "evidence_ref": "naive"}],
    )


def _load_secrets() -> dict[str, Any] | None:
    path = REPO_ROOT / "config" / "secrets.yaml"
    if not path.exists():
        return None
    data = load_yaml(path)
    key = ((data.get("openai_compatible") or {}).get("api_key") or "").strip()
    if not key or key == "REPLACE_ME":
        return None
    return data


def naive_answer_llm(question: str, question_id: str | None = None) -> dict[str, Any]:
    """Optional live LLM with RAG snippets only (no metrics / no preflight)."""
    app = load_yaml(REPO_ROOT / "config" / "app.yaml")
    secrets = _load_secrets()
    if secrets is None:
        out = naive_answer_offline(question, question_id)
        out["meta"]["llm_fallback"] = "no_secrets"
        return out

    chunks = retrieve(question)
    context = "\n---\n".join(f"[{c.doc_id}] {c.text}" for c in chunks) or "(no docs)"
    model = app.get("llm", {}).get("model", "gpt-4o-mini")
    base = app.get("llm", {}).get("base_url") or "https://api.openai.com/v1"
    api_key = secrets["openai_compatible"]["api_key"]
    system = (
        "You are a helpful IR analyst. Use the document snippets if useful. "
        "Answer in Traditional Chinese. You may estimate numbers if unsure."
    )
    user = f"Question id: {question_id}\nQuestion: {question}\n\nSnippets:\n{context}"
    body = {
        "model": model,
        "temperature": float(app.get("llm", {}).get("temperature") or 0),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
        out = naive_answer_offline(question, question_id)
        out["meta"]["llm_fallback"] = f"error:{type(exc).__name__}"
        return out

    return {
        "answer_text": text,
        "question_type": "analytical",
        "response_mode": "full",
        "reason_codes": [],
        "definitions_used": [],
        "figures": [],
        "evidence": [{"type": "naive_rag", "ref": "tools.rag.keyword"}],
        "coverage_gap": None,
        "missing_for_full": None,
        "meta": {
            "system": "naive_baseline",
            "prompt_version": NAIVE_LLM_PROMPT_VERSION,
            "model": model,
            "usage": usage,
        },
    }


def naive_answer(
    question: str,
    question_id: str | None = None,
    *,
    use_llm: bool = False,
) -> dict[str, Any]:
    if use_llm:
        return naive_answer_llm(question, question_id)
    return naive_answer_offline(question, question_id)
