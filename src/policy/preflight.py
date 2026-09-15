"""Pre-flight policy gate (before DB / LLM). Not IAM."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml


@dataclass
class PreflightDecision:
    action: str  # allow | refuse | downgrade_hint
    reason_codes: list[str]
    message: str
    matched_rule: str | None = None


def _policy(path: Path | None = None) -> dict[str, Any]:
    return load_yaml(path or (REPO_ROOT / "config" / "policy.yaml"))


def _hit(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            return p
    return None


def preflight(question: str, *, policy_path: Path | None = None) -> PreflightDecision:
    """Intercept out-of-scope / causal / PII / imputation / tenant-GMV asks."""
    pol = _policy(policy_path)
    q = question.strip()

    # Never emit ACCESS_RESTRICTED
    assert "ACCESS_RESTRICTED" not in pol["reason_codes"]

    if _hit(pol["out_of_scope_keywords"], q):
        return PreflightDecision(
            action="refuse",
            reason_codes=["OUT_OF_SCOPE"],
            message="此問題超出本版範圍（例如 RevPAR／ADR／博彩／租戶 P&L）。",
            matched_rule="out_of_scope",
        )

    if _hit(pol["pii_request_patterns"], q):
        return PreflightDecision(
            action="refuse",
            reason_codes=["PII_MINIMIZATION"],
            message="拒絕提供逐客名單或聯絡方式；可改問彙總指標。",
            matched_rule="pii",
        )

    # Estimate / impute tenant spend → hard refuse (Q6)
    if _hit(pol["imputation_patterns"], q) and (
        re.search(r"租戶|tenant|商場|GMV", q, re.IGNORECASE)
    ):
        return PreflightDecision(
            action="refuse",
            reason_codes=["DATA_UNAVAILABLE"],
            message="拒絕估計或插補租戶真實消費／GMV。系統沒有租戶客人級銷售資料。",
            matched_rule="imputation_tenant",
        )

    if _hit(pol["causal_keywords"], q):
        return PreflightDecision(
            action="refuse",
            reason_codes=["CAUSAL_UNSUPPORTED"],
            message="本版不支援因果結論（觀察性資料、無實驗設計）。可描述可觀察接觸後行為，但不能說「造成」。",
            matched_rule="causal",
        )

    # Mall spend without estimate → may continue to downgrade path (Q5)
    if _hit(pol["tenant_gmv_patterns"], q) and not _hit(pol["imputation_patterns"], q):
        return PreflightDecision(
            action="downgrade_hint",
            reason_codes=["COVERAGE_GAP", "DATA_UNAVAILABLE"],
            message="完整商場／租戶 GMV 不可得；可降級為可觀察子集。",
            matched_rule="tenant_gmv_coverage",
        )

    return PreflightDecision(action="allow", reason_codes=[], message="ok", matched_rule=None)


def refuse_payload(decision: PreflightDecision, *, question_type: str = "should_refuse") -> dict[str, Any]:
    return {
        "answer_text": decision.message,
        "question_type": question_type,
        "response_mode": "refuse",
        "reason_codes": decision.reason_codes,
        "definitions_used": [],
        "figures": [],
        "evidence": [{"type": "preflight", "rule": decision.matched_rule}],
        "coverage_gap": None,
        "missing_for_full": decision.message,
    }
