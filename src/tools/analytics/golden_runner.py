"""Deterministic golden runner: question id → structured answer (no LLM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml
from ecia.data.generate import DEFAULT_DB_PATH
from tools.analytics import metrics as m


CONTRACTS_PATH = REPO_ROOT / "eval" / "questions" / "contracts.yaml"
GOLDENS_DIR = REPO_ROOT / "eval" / "goldens"
V1_QUESTION_IDS = ["Q1", "Q3", "Q4", "Q5", "Q8", "Q10", "Q14"]
ALL_QUESTION_IDS = [
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "Q5",
    "Q6",
    "Q7",
    "Q8",
    "Q9",
    "Q10",
    "Q11",
    "Q12",
    "Q13",
    "Q14",
    "Q15",
    "Q_REVPAR",
]


def _contracts_by_id() -> dict[str, dict[str, Any]]:
    data = load_yaml(CONTRACTS_PATH)
    return {q["id"]: q for q in data["questions"]}


def _figure(
    metric_id: str,
    value: float | int,
    *,
    period: str,
    evidence_ref: str,
    dimensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "period": period,
        "dimensions": dimensions or {},
        "value": value,
        "evidence_ref": evidence_ref,
    }


def _refuse_from_contract(c: dict[str, Any], answer_text: str) -> dict[str, Any]:
    return {
        "answer_text": answer_text,
        "question_type": c["question_type"],
        "response_mode": c["response_mode"],
        "reason_codes": list(c.get("reason_codes") or []),
        "definitions_used": [],
        "figures": [],
        "evidence": [{"type": "policy", "ref": "config/policy.yaml"}],
        "coverage_gap": None,
        "missing_for_full": None,
    }


def answer(question_id: str, *, db_path: Path | None = None, conflict_vip: bool = False) -> dict[str, Any]:
    contracts = _contracts_by_id()
    if question_id not in contracts:
        raise KeyError(f"Unknown question_id: {question_id}")
    c = contracts[question_id]

    # Refuse-only paths (no DB required for correctness; still open for consistency)
    if question_id == "Q6":
        return _refuse_from_contract(
            c,
            "拒絕估計租戶真實消費／GMV。不得插補或外推。"
            "可改問 Q5 可觀察子集（自營零售 POS ∪ 購物禮券核銷），但那不是估計。",
        )
    if question_id == "Q7":
        return _refuse_from_contract(
            c,
            "不支援因果主張。活動接觸後的觀察性描述不足以證明「造成營收增加」。",
        )
    if question_id == "Q13":
        return _refuse_from_contract(
            c,
            "拒絕輸出 VIP 姓名、聯絡方式或逐客消費明細（PII 最小化）。可改問彙總（例如 Tier 3 人數）。",
        )
    if question_id == "Q_REVPAR":
        return _refuse_from_contract(c, "RevPAR／ADR 非本版範圍（OUT_OF_SCOPE）。")

    if question_id == "Q9":
        hv = m.high_value_vs_vip()
        return {
            "answer_text": hv["answer_text"],
            "question_type": c["question_type"],
            "response_mode": c["response_mode"],
            "reason_codes": list(c.get("reason_codes") or []),
            "definitions_used": [
                "semantic.loyalty.high_value_member",
                "semantic.tiers.vip_synonym_of",
            ],
            "figures": [],
            "evidence": [{"type": "semantic", "ref": "config/semantic.yaml"}],
            "coverage_gap": None,
            "missing_for_full": None,
        }

    con = m.connect(db_path)
    try:
        as_of = m.as_of(con)
        q = m.last_quarter(as_of)
        prior = m.prior_quarter(q)
        yoy = m.same_quarter_prior_year(q)
        p90 = m.prior_90_days(as_of)

        if question_id == "Q1":
            net = m.net_room_revenue(con, q)
            other = m.hotel_other_revenue(con, q)
            hotel = net + other
            fb = m.fb_self_op_revenue(con, q)
            retail = m.retail_self_op_revenue(con, q)
            figures = [
                _figure("hotel_pillar_total", hotel, period=q.label, evidence_ref="metrics.hotel_pillar_total"),
                _figure("net_room_revenue", net, period=q.label, evidence_ref="metrics.net_room_revenue"),
                _figure("hotel_other_revenue", other, period=q.label, evidence_ref="metrics.hotel_other_revenue"),
                _figure("fb_self_op_revenue", fb, period=q.label, evidence_ref="metrics.fb_self_op_revenue"),
                _figure("retail_self_op_revenue", retail, period=q.label, evidence_ref="metrics.retail_self_op_revenue"),
            ]
            text = (
                f"{q.label} 三支柱 IR 營收：酒店支柱合計 {hotel:.2f} "
                f"（淨房收 {net:.2f} + 酒店其他 {other:.2f}）；"
                f"F&B 自營 {fb:.2f}；零售自營 {retail:.2f}。"
                "聲明：F&B／零售僅自營，不含租戶 GMV；酒店為支柱合計。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q2":
            net = m.net_room_revenue(con, q)
            other = m.hotel_other_revenue(con, q)
            hotel = net + other
            figures = [
                _figure("hotel_pillar_total", hotel, period=q.label, evidence_ref="metrics.hotel_pillar_total"),
                _figure("net_room_revenue", net, period=q.label, evidence_ref="metrics.net_room_revenue"),
                _figure("hotel_other_revenue", other, period=q.label, evidence_ref="metrics.hotel_other_revenue"),
            ]
            text = (
                f"聲明：預設「酒店營收」＝酒店支柱合計（淨房收＋酒店其他），非淨房收 alone。"
                f"{q.label} 酒店支柱合計 {hotel:.2f}（淨房收 {net:.2f}＋酒店其他 {other:.2f}）。"
                "間夜／淨房收請另問；不含 F&B／零售；不計算 ADR／RevPAR。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q3":
            n = m.active_member_count(con, p90)
            figures = [
                _figure("active_member_count", n, period=p90.label, evidence_ref="metrics.active_member_count")
            ]
            text = f"過去 90 天活躍會員 {n} 人（僅計 IR 錢包現金事件；不含租戶禮券核銷／點數兌換／comp）。"
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q4":
            n = m.member_count(con)
            figures = [_figure("member_count", n, period="as_of", evidence_ref="metrics.member_count")]
            text = f"客戶數（預設＝會員）為 {n}。聲明：不含訪客數、住房客數、未識別消費者。"
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q5":
            obs = m.observable_retail(con, q, tier="Tier 2")
            figures = [
                _figure(
                    "self_op_retail_pos",
                    obs["self_op_retail_pos"],
                    period=q.label,
                    evidence_ref="metrics.observable_retail",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "shopping_voucher_redeemed_face",
                    obs["shopping_voucher_redeemed_face"],
                    period=q.label,
                    evidence_ref="metrics.observable_retail",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "observable_retail_total",
                    obs["observable_total"],
                    period=q.label,
                    evidence_ref="metrics.observable_retail",
                    dimensions={"tier": "Tier 2"},
                ),
            ]
            text = (
                f"無法回答 Tier 2 完整商場 GMV（租戶實付不可知）。"
                f"可觀察子集（{q.label}）：自營零售 POS {obs['self_op_retail_pos']:.2f}；"
                f"購物禮券核銷面額 {obs['shopping_voucher_redeemed_face']:.2f}；"
                f"合計 {obs['observable_total']:.2f}。"
                "聲明：禮券面額≠整單；租戶實付未知。"
            )
            return _pack(
                c,
                text,
                figures,
                coverage_gap="Full mall / tenant GMV not in IR data rights.",
                missing="Tenant POS / guest-level GMV at leased outlets.",
            )

        if question_id == "Q8":
            vip = m.vip_definition(include_conflict_doc=conflict_vip)
            return {
                "answer_text": vip["answer_text"],
                "question_type": c["question_type"],
                "response_mode": vip["response_mode"],
                "reason_codes": vip["reason_codes"],
                "definitions_used": vip["definitions_used"],
                "figures": [],
                "evidence": [{"type": "semantic", "ref": "config/semantic.yaml"}],
                "coverage_gap": None,
                "missing_for_full": None
                if vip["response_mode"] == "full"
                else "SSOT update to resolve VIP definition conflict",
            }

        if question_id == "Q10":
            issued = m.voucher_issued_amount(con, q)
            redeemed = m.voucher_redeemed_amount(con, q)
            retail = m.retail_self_op_revenue(con, q)
            figures = [
                _figure("voucher_issued_amount", issued, period=q.label, evidence_ref="metrics.voucher_issued"),
                _figure("voucher_redeemed_amount", redeemed, period=q.label, evidence_ref="metrics.voucher_redeemed"),
                _figure("retail_self_op_revenue", retail, period=q.label, evidence_ref="metrics.retail_self_op_revenue"),
            ]
            text = (
                f"{q.label} 禮券發行面額 {issued:.2f}；核銷面額 {redeemed:.2f}。"
                f"對照自營零售營收 {retail:.2f}。"
                "聲明：核銷≠商場 GMV≠IR 零售營收。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q11":
            decomp = m.tier_contribution_change(con, q, prior)
            figures = []
            for tier, val in sorted(decomp["current"].items()):
                if not str(tier).startswith("Tier"):
                    continue
                figures.append(
                    _figure(
                        "tier_ir_revenue_current",
                        val,
                        period=q.label,
                        evidence_ref="metrics.ir_revenue_by_tier",
                        dimensions={"tier": tier},
                    )
                )
            for tier, val in sorted(decomp["prior"].items()):
                if not str(tier).startswith("Tier"):
                    continue
                figures.append(
                    _figure(
                        "tier_ir_revenue_prior",
                        val,
                        period=prior.label,
                        evidence_ref="metrics.ir_revenue_by_tier",
                        dimensions={"tier": tier},
                    )
                )
            for tier, val in sorted(decomp["deltas"].items()):
                figures.append(
                    _figure(
                        "tier_ir_revenue_delta",
                        val,
                        period=f"{prior.label}_to_{q.label}",
                        evidence_ref="metrics.tier_contribution_change",
                        dimensions={"tier": tier},
                    )
                )
            top = decomp["largest_abs_contributor_tier"]
            top_delta = decomp["largest_abs_delta"]
            sum_deltas = decomp["sum_deltas"]
            figures.append(
                _figure(
                    "sum_tier_deltas",
                    sum_deltas,
                    period=f"{prior.label}_to_{q.label}",
                    evidence_ref="metrics.tier_contribution_change",
                )
            )
            text = (
                f"事實：以期末等級快照歸屬自營 IR 認列營收（不含租戶 GMV）。"
                f"比較 {prior.label} → {q.label}。"
                f"絕對變動最大等級為 {top}（Δ={top_delta:.2f}）。"
                f"各 Tier Δ 加總={sum_deltas:.2f}（可核對）。"
                "解釋：此為貢獻分解，非因果歸因。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q12":
            cur = m.observable_dining(con, q, tier="Tier 2")
            prev = m.observable_dining(con, yoy, tier="Tier 2")
            delta = cur["observable_dining_total"] - prev["observable_dining_total"]
            declined = delta < 0
            figures = [
                _figure(
                    "observable_dining_current",
                    cur["observable_dining_total"],
                    period=q.label,
                    evidence_ref="metrics.observable_dining",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "fb_self_op_current",
                    cur["fb_self_op"],
                    period=q.label,
                    evidence_ref="metrics.observable_dining",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "fb_voucher_redeemed_current",
                    cur["fb_voucher_redeemed_face"],
                    period=q.label,
                    evidence_ref="metrics.observable_dining",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "observable_dining_prior_year",
                    prev["observable_dining_total"],
                    period=yoy.label,
                    evidence_ref="metrics.observable_dining",
                    dimensions={"tier": "Tier 2"},
                ),
                _figure(
                    "observable_dining_yoy_delta",
                    delta,
                    period=f"{yoy.label}_to_{q.label}",
                    evidence_ref="metrics.observable_dining",
                    dimensions={"tier": "Tier 2"},
                ),
            ]
            yn = "是" if declined else "否"
            text = (
                f"聲明：可觀察用餐＝自營 F&B ∪ F&B 禮券核銷；不含 IRD、不含租戶餐廳整單。"
                f"Tier 2：{q.label}={cur['observable_dining_total']:.2f}；"
                f"{yoy.label}={prev['observable_dining_total']:.2f}；Δ={delta:.2f}。"
                f"較去年同期是否下降：{yn}。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q14":
            res = m.tenant_only_redeemers_not_active(con, p90)
            figures = [
                _figure(
                    "tenant_only_redeemer_count",
                    res["tenant_only_redeemer_count"],
                    period=p90.label,
                    evidence_ref="metrics.tenant_only_redeemers",
                )
            ]
            text = (
                "不算活躍。"
                f"（過去 90 天僅租戶禮券核銷、無 IR 錢包現金的會員數樣本計數："
                f"{res['tenant_only_redeemer_count']}；規則 I16。）"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        if question_id == "Q15":
            facts = m.package_and_folio_rules(con)
            figures = [
                _figure(
                    "folio_fb_txn_count",
                    facts["folio_fb_txn_count"],
                    period="as_of_snapshot",
                    evidence_ref="metrics.package_and_folio_rules",
                ),
                _figure(
                    "folio_fb_amount",
                    facts["folio_fb_amount"],
                    period="as_of_snapshot",
                    evidence_ref="metrics.package_and_folio_rules",
                ),
            ]
            text = (
                "否：套裝中租戶餐廳早餐與購物禮券走負債／核銷事件，不分別計入 F&B 與零售 IR 營收。"
                "自營晚餐掛房帳歸 F&B（payment_path=folio），不是酒店套裝拆分；錢包現金結帳只計一次。"
                f"（樣本：folio F&B 交易 {facts['folio_fb_txn_count']} 筆、金額 {facts['folio_fb_amount']:.2f}。）"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)

        raise NotImplementedError(f"Runner not implemented for {question_id}")
    finally:
        con.close()


def _pack(
    contract: dict[str, Any],
    answer_text: str,
    figures: list[dict[str, Any]],
    *,
    coverage_gap: str | None,
    missing: str | None,
) -> dict[str, Any]:
    return {
        "answer_text": answer_text,
        "question_type": contract["question_type"],
        "response_mode": contract["response_mode"],
        "reason_codes": list(contract.get("reason_codes") or []),
        "definitions_used": [],
        "figures": figures,
        "evidence": [{"type": "metrics", "ref": "tools.analytics.metrics"}],
        "coverage_gap": coverage_gap,
        "missing_for_full": missing,
    }


def write_goldens(
    *,
    db_path: Path | None = None,
    out_dir: Path | None = None,
    question_ids: list[str] | None = None,
    filename: str | None = None,
) -> Path:
    out = out_dir or GOLDENS_DIR
    out.mkdir(parents=True, exist_ok=True)
    ids = question_ids or ALL_QUESTION_IDS
    payload = {
        "db": str(db_path or DEFAULT_DB_PATH),
        "questions": {qid: answer(qid, db_path=db_path) for qid in ids},
    }
    name = filename or ("v1_goldens.json" if ids == V1_QUESTION_IDS else "q1_q15_goldens.json")
    path = out / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_all_goldens(*, db_path: Path | None = None, out_dir: Path | None = None) -> tuple[Path, Path]:
    """Write full Q1–Q15 (+RevPAR) goldens and refresh V1 subset file."""
    full = write_goldens(db_path=db_path, out_dir=out_dir, question_ids=ALL_QUESTION_IDS, filename="q1_q15_goldens.json")
    v1 = write_goldens(db_path=db_path, out_dir=out_dir, question_ids=V1_QUESTION_IDS, filename="v1_goldens.json")
    return full, v1


def load_goldens(path: Path | None = None) -> dict[str, Any]:
    p = path or (GOLDENS_DIR / "v1_goldens.json")
    return json.loads(p.read_text(encoding="utf-8"))


def require_full_goldens(path: Path | None = None) -> Path:
    """Eval gate: agent eval must not run without full goldens."""
    p = path or (GOLDENS_DIR / "q1_q15_goldens.json")
    if not p.exists():
        raise FileNotFoundError(
            f"Missing goldens at {p}. Run: python scripts/build_goldens.py"
            " — refusing agent eval without goldens (WP-507)."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    missing = [qid for qid in ALL_QUESTION_IDS if qid not in data.get("questions", {})]
    if missing:
        raise FileNotFoundError(
            f"Goldens incomplete; missing {missing}. Run: python scripts/build_goldens.py"
        )
    return p
