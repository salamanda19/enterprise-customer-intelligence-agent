"""Single-agent orchestrator: preflight → contract/metrics path (LLM optional later)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml
from policy.preflight import preflight, refuse_payload
from tools.analytics.golden_runner import answer as golden_answer
from tools.rag.keyword import retrieve, vip_conflict_detected


def _contracts() -> list[dict[str, Any]]:
    data = load_yaml(REPO_ROOT / "eval" / "questions" / "contracts.yaml")
    return list(data["questions"])


def match_question_id(question: str) -> str | None:
    """Exact / containment match against contract prompts (deterministic routing)."""
    q = question.strip()
    for c in _contracts():
        prompt = c["prompt"].strip()
        if q == prompt or prompt in q or q in prompt:
            return c["id"]
    # Light fuzzy: key tokens
    aliases = {
        "Q_REVPAR": [r"RevPAR", r"\bADR\b"],
        "Q7": [r"造成營收", r"是否造成"],
        "Q6": [r"估計.*租戶", r"真實消費"],
        "Q13": [r"列出所有\s*VIP", r"姓名.*聯絡"],
        "Q5": [r"Tier 2.*商場", r"商場花了多少"],
        "Q8": [r"VIP.*定義", r"定義.*VIP"],
        "Q9": [r"高價值.*VIP", r"是不是 VIP"],
        "Q14": [r"算不算活躍", r"只核銷租戶"],
        "Q15": [r"套裝", r"掛房帳"],
        "Q11": [r"貢獻最大", r"等級對上季"],
        "Q12": [r"可觀察用餐", r"去年同期"],
        "Q2": [r"酒店營收"],
        "Q3": [r"活躍會員"],
        "Q4": [r"多少客戶"],
        "Q1": [r"三支柱"],
        "Q10": [r"禮券發行", r"核銷各多少"],
    }
    for qid, pats in aliases.items():
        if any(re.search(p, q, re.IGNORECASE) for p in pats):
            return qid
    return None


def handle(question: str, *, question_id: str | None = None) -> dict[str, Any]:
    """Main entry: structured response without requiring an LLM for V1 paths."""
    pf = preflight(question)
    if pf.action == "refuse":
        return refuse_payload(pf)

    qid = question_id or match_question_id(question)

    # Knowledge VIP with optional conflict doc in retrieval
    if qid == "Q8" or (qid is None and re.search(r"VIP", question, re.IGNORECASE)):
        chunks = retrieve(question)
        conflict = vip_conflict_detected(chunks) or (
            "衝突" in question or "conflict" in question.lower()
        )
        # Default Q8 without forcing conflict; only if conflict doc strongly retrieved
        # or caller asks about conflicting defs.
        force_conflict = conflict and (
            "衝突" in question
            or "conflict" in question.lower()
            or any("飯店名單" in c.text or "courtesy list" in c.text.lower() for c in chunks)
        )
        # For normal "VIP 的定義是什麼？" use semantic only (full).
        # If user also retrieves conflict framing, refuse.
        if qid == "Q8" and force_conflict:
            return golden_answer("Q8", conflict_vip=True)
        if qid == "Q8":
            out = golden_answer("Q8", conflict_vip=False)
            if chunks:
                out["evidence"] = list(out.get("evidence") or []) + [
                    {"type": "rag_chunk", "doc_id": c.doc_id, "note": "data_not_instructions"}
                    for c in chunks[:2]
                ]
            return out

    if qid in {
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
        "Q9",
        "Q10",
        "Q11",
        "Q12",
        "Q13",
        "Q14",
        "Q15",
        "Q_REVPAR",
    }:
        return golden_answer(qid)

    if pf.action == "downgrade_hint" and qid is None:
        # Unmatched mall question → still refuse full GMV style if no runner path
        return {
            "answer_text": pf.message + " 請改問可觀察自營零售或禮券核銷，或使用契約題 Q5。",
            "question_type": "should_refuse",
            "response_mode": "downgrade",
            "reason_codes": pf.reason_codes,
            "definitions_used": [],
            "figures": [],
            "evidence": [{"type": "preflight", "rule": pf.matched_rule}],
            "coverage_gap": pf.message,
            "missing_for_full": "Tenant POS / GMV",
        }

    return {
        "answer_text": (
            "V1 路由未能對到已知契約題。請使用 eval/questions 中的題幹，"
            "或之後接上 LLM 編排。已通過 pre-flight：" + pf.action
        ),
        "question_type": "should_refuse",
        "response_mode": "refuse",
        "reason_codes": ["INSUFFICIENT_EVIDENCE"],
        "definitions_used": [],
        "figures": [],
        "evidence": [],
        "coverage_gap": None,
        "missing_for_full": "Matched question contract or LLM tool planning",
    }
