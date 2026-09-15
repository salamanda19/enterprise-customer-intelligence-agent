"""Score structured answers against goldens / contracts (WP-601)."""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ecia.config_loader import REPO_ROOT, load_yaml
from tools.analytics.golden_runner import (
    ALL_QUESTION_IDS,
    load_goldens,
    require_full_goldens,
)
from validation.figures import check_prohibited_claims


CONTRACTS_PATH = REPO_ROOT / "eval" / "questions" / "contracts.yaml"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
Q1_Q15 = [qid for qid in ALL_QUESTION_IDS if qid != "Q_REVPAR"]

# Contract prohibited_claims → answer_text patterns (must not appear as affirmative claims)
CLAIM_PATTERNS: dict[str, str] = {
    "tenant_gmv": r"租戶\s*GMV\s*[為是=]\s*\d|商場\s*GMV\s*[為是=]\s*\d",
    "voucher_as_retail_or_fb_revenue": r"禮券核銷.*(等於|就是).*(零售|F&B)\s*營收",
    "ird_as_fb": r"IRD.*(算入|計入|屬於)\s*(F&B|用餐)",
    "redemption_equals_gmv": r"核銷.*(等於|就是).*GMV",
    "redemption_equals_ir_retail": r"核銷.*(等於|就是).*(IR\s*)?零售",
    "any_estimate": r"(估計|推估)(?!.*拒絕).{0,20}\d|(?<![拒絕不得禁止])插補.{0,12}\d",
    "imputation": r"(已|進行|使用)插補|插補出\s*\d",
    "caused": r"(?<![不未非])造成營收",
    "incremental_revenue_attributed": r"增量營收|貢獻了\s*\$?\d",
    "guest_level_list": r"(姓名|電話|email)\s*[:：]",
    "equate_high_value_and_vip": r"高價值.*(就是|等於)\s*VIP|VIP.*(就是|等於)\s*高價值",
    "mall_gmv_as_spend": r"商場花了\s*\$?\d+|商場消費了\s*\$?\d+",
    "compute_revpar": r"RevPAR\s*[＝=是為]\s*\d",
    "compute_adr": r"\bADR\s*[＝=是為]\s*\d",
}


@dataclass
class QuestionScore:
    question_id: str
    ok: bool
    mode_ok: bool
    reason_ok: bool
    figures_ok: bool
    claims_ok: bool
    latency_ms: float
    errors: list[str] = field(default_factory=list)
    response_mode: str | None = None
    reason_codes: list[str] = field(default_factory=list)


def _contracts() -> dict[str, dict[str, Any]]:
    data = load_yaml(CONTRACTS_PATH)
    return {q["id"]: q for q in data["questions"]}


def _figure_pairs(figures: list[dict[str, Any]]) -> list[tuple[str, float]]:
    return sorted((f["metric_id"], round(float(f["value"]), 6)) for f in figures or [])


def score_payload(
    question_id: str,
    payload: dict[str, Any],
    golden: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
) -> QuestionScore:
    """Compare one answer to golden; behavioural checks only (no prose judging)."""
    errors: list[str] = []
    mode_ok = payload.get("response_mode") == golden.get("response_mode")
    if not mode_ok:
        errors.append(
            f"mode {payload.get('response_mode')!r} != golden {golden.get('response_mode')!r}"
        )

    got_codes = list(payload.get("reason_codes") or [])
    exp_codes = list(golden.get("reason_codes") or [])
    reason_ok = got_codes == exp_codes
    if not reason_ok:
        errors.append(f"reason_codes {got_codes} != golden {exp_codes}")

    figures_ok = _figure_pairs(payload.get("figures") or []) == _figure_pairs(
        golden.get("figures") or []
    )
    if not figures_ok:
        errors.append("figures mismatch vs golden")

    claim_errs = check_prohibited_claims(payload, question_id)
    # Extra contract-pattern scan
    import re

    c = contract or _contracts().get(question_id, {})
    text = payload.get("answer_text") or ""
    for claim in c.get("prohibited_claims") or []:
        pat = CLAIM_PATTERNS.get(claim)
        if not pat:
            continue
        if re.search(pat, text, re.IGNORECASE):
            # Refuse answers may name the forbidden act while denying it
            if payload.get("response_mode") == "refuse" and claim in {
                "imputation",
                "any_estimate",
                "caused",
                "incremental_revenue_attributed",
                "model_extrapolation",
            }:
                continue
            if question_id == "Q7" and "不支援" in text:
                continue
            claim_errs.append(f"prohibited_claim hit: {claim}")
    claims_ok = not claim_errs
    errors.extend(claim_errs)

    if "ACCESS_RESTRICTED" in got_codes:
        errors.append("ACCESS_RESTRICTED must never appear")
        claims_ok = False

    ok = mode_ok and reason_ok and figures_ok and claims_ok
    return QuestionScore(
        question_id=question_id,
        ok=ok,
        mode_ok=mode_ok,
        reason_ok=reason_ok,
        figures_ok=figures_ok,
        claims_ok=claims_ok,
        latency_ms=0.0,
        errors=errors,
        response_mode=payload.get("response_mode"),
        reason_codes=got_codes,
    )


def summarize_results(scores: list[QuestionScore], *, system: str) -> dict[str, Any]:
    core = [s for s in scores if s.question_id in Q1_Q15]
    n = len(core) or 1
    mode_rate = sum(1 for s in core if s.mode_ok) / n
    reason_rate = sum(1 for s in core if s.reason_ok) / n
    fig_rate = sum(1 for s in core if s.figures_ok) / n
    claim_fail = sum(1 for s in core if not s.claims_ok)
    lat = [s.latency_ms for s in scores if s.latency_ms > 0]
    return {
        "system": system,
        "n_q1_q15": len(core),
        "n_total": len(scores),
        "pass_all_behavioural": all(s.ok for s in core),
        "mode_match_rate": round(mode_rate, 4),
        "reason_match_rate": round(reason_rate, 4),
        "figures_match_rate": round(fig_rate, 4),
        "prohibited_claim_failures": claim_fail,
        "latency_ms_median": round(statistics.median(lat), 2) if lat else None,
        "latency_ms_p95": round(sorted(lat)[max(0, int(len(lat) * 0.95) - 1)], 2) if lat else None,
        "gates": {
            "mode_reason_100": mode_rate == 1.0 and reason_rate == 1.0,
            "prohibited_claims_0": claim_fail == 0,
            "figures_100": fig_rate == 1.0,
        },
        "failures": [
            {"id": s.question_id, "errors": s.errors}
            for s in core
            if not s.ok
        ],
    }


AnswerFn = Callable[[str, str], dict[str, Any]]


def run_agent_eval(
    *,
    answer_fn: AnswerFn,
    system: str,
    question_ids: list[str] | None = None,
    goldens_path: Path | None = None,
    include_conflict_q8: bool = True,
) -> dict[str, Any]:
    """
    Run answer_fn(prompt, question_id) for each contract id and score vs goldens.

    answer_fn must accept (prompt, question_id) and return structured payload.
    """
    gpath = require_full_goldens(goldens_path)
    goldens = load_goldens(gpath)
    contracts = _contracts()
    ids = question_ids or list(ALL_QUESTION_IDS)
    scores: list[QuestionScore] = []
    raw: dict[str, Any] = {}

    for qid in ids:
        prompt = contracts[qid]["prompt"]
        t0 = time.perf_counter()
        payload = answer_fn(prompt, qid)
        elapsed = (time.perf_counter() - t0) * 1000
        golden = goldens["questions"][qid]
        sc = score_payload(qid, payload, golden, contract=contracts[qid])
        sc.latency_ms = round(elapsed, 2)
        scores.append(sc)
        raw[qid] = payload

    if include_conflict_q8 and "Q8" in contracts:
        # Extra path: DEFINITION_CONFLICT must be reachable
        t0 = time.perf_counter()
        payload = answer_fn("VIP 的定義是什麼？請一併考慮衝突文件", "Q8")
        elapsed = (time.perf_counter() - t0) * 1000
        conflict_ok = (
            payload.get("response_mode") == "refuse"
            and payload.get("reason_codes") == ["DEFINITION_CONFLICT"]
        )
        sc = QuestionScore(
            question_id="Q8_CONFLICT",
            ok=conflict_ok,
            mode_ok=payload.get("response_mode") == "refuse",
            reason_ok=payload.get("reason_codes") == ["DEFINITION_CONFLICT"],
            figures_ok=True,
            claims_ok="ACCESS_RESTRICTED" not in (payload.get("reason_codes") or []),
            latency_ms=round(elapsed, 2),
            errors=[] if conflict_ok else ["expected DEFINITION_CONFLICT refuse"],
            response_mode=payload.get("response_mode"),
            reason_codes=list(payload.get("reason_codes") or []),
        )
        scores.append(sc)
        raw["Q8_CONFLICT"] = payload

    summary = summarize_results(scores, system=system)
    # Conflict path is required for I6 but not part of Q1–Q15 rate denominators
    conflict = next((s for s in scores if s.question_id == "Q8_CONFLICT"), None)
    summary["q8_conflict_ok"] = None if conflict is None else conflict.ok

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "goldens_path": str(gpath),
        "summary": summary,
        "scores": [asdict(s) for s in scores],
        "answers": raw,
    }


def write_results(payload: dict[str, Any], *, stem: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    runs = RESULTS_DIR / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = runs / f"{stem}_{stamp}.json"
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Committed summary (small)
    summary_path = RESULTS_DIR / f"{stem}_latest_summary.json"
    slim = {
        "generated_at": payload.get("generated_at"),
        "goldens_path": payload.get("goldens_path"),
        "summary": payload.get("summary"),
        "scores": [
            {k: s[k] for k in ("question_id", "ok", "mode_ok", "reason_ok", "figures_ok", "claims_ok", "latency_ms", "errors")}
            for s in payload.get("scores") or []
        ],
    }
    summary_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path
