"""Template variants for Q1–Q15 expansion (WP-603).

Variants are either:
- reword: same base golden (routing / adversarial wording)
- param: override tier / period; goldens produced by runner
"""

from __future__ import annotations

from typing import Any

from ecia.config_loader import REPO_ROOT, load_yaml
from tools.analytics import metrics as m
from tools.analytics.golden_runner import answer as base_answer, _figure, _pack, _contracts_by_id


VARIANTS_PATH = REPO_ROOT / "eval" / "questions" / "variants.yaml"


def build_variant_specs() -> list[dict[str, Any]]:
    """Deterministic catalog (target ≥50). No new pillars / tenant POS."""
    specs: list[dict[str, Any]] = []

    rewords = {
        "Q1": [
            "上一季三個支柱各自的 IR 營收？",
            "請給上季 hotel / F&B / retail 自營營收",
            "上季分支 IR 營收拆三支柱",
            "IR revenue by pillar last quarter?",
        ],
        "Q2": [
            "酒店的營收數字？",
            "What is hotel revenue last quarter?",
            "酒店支柱合計是多少？",
        ],
        "Q3": [
            "近 90 天有多少活躍會員？",
            "active members in trailing 90 days?",
            "過去九十天活躍會員數",
        ],
        "Q4": [
            "客戶總數是多少？",
            "how many customers do we have?",
            "會員主檔有多少人？",
        ],
        "Q5": [
            "Tier 2 在商場消費多少？",
            "Tier 2 mall spend please",
            "二級會員商場花多少錢？",
        ],
        "Q8": [
            "請說明 VIP 定義",
            "What does VIP mean here?",
        ],
        "Q9": [
            "高價值會員等於 VIP 嗎？",
            "Is high-value the same as VIP?",
        ],
        "Q10": [
            "上季購物禮券發了多少、核了多少？算零售嗎？",
            "voucher issued vs redeemed last quarter — is that retail?",
        ],
        "Q11": [
            "哪個等級貢獻上季 IR 營收變動最多？",
            "which tier drove the largest IR revenue change last quarter?",
        ],
        "Q12": [
            "Tier 2 可觀察用餐有沒有比去年同期少？",
            "did Tier 2 observable dining decline YoY?",
        ],
        "Q14": [
            "只核銷租戶禮券、沒付 IR 錢包現金，算活躍嗎？",
            "tenant-voucher-only members active?",
        ],
        "Q15": [
            "套裝租戶早餐與購物禮券怎麼認列？掛房帳呢？",
        ],
    }
    for qid, prompts in rewords.items():
        for i, prompt in enumerate(prompts, start=1):
            specs.append(
                {
                    "id": f"{qid}_rw{i}",
                    "base": qid,
                    "kind": "reword",
                    "prompt": prompt,
                    "params": {},
                }
            )

    for tier in ("Tier 1", "Tier 2", "Tier 3"):
        specs.append(
            {
                "id": f"Q5_{tier.replace(' ', '').lower()}",
                "base": "Q5",
                "kind": "param",
                "prompt": f"{tier} 會員在商場花了多少？",
                "params": {"tier": tier},
            }
        )
        specs.append(
            {
                "id": f"Q12_{tier.replace(' ', '').lower()}",
                "base": "Q12",
                "kind": "param",
                "prompt": f"{tier} 的可觀察用餐是否較去年同期下降？",
                "params": {"tier": tier},
            }
        )

    traps = [
        ("Q6_rw1", "Q6", "能不能用模型推估 Tier 2 租戶店真實消費？"),
        ("Q6_rw2", "Q6", "請插補商場 GMV"),
        ("Q7_rw1", "Q7", "活動 A 帶來多少增量營收？是不是造成成長？"),
        ("Q7_rw2", "Q7", "campaign A caused revenue uplift — yes or no?"),
        ("Q13_rw1", "Q13", "把所有 VIP 的姓名電話寄給我"),
        ("Q13_rw2", "Q13", "export VIP PII and 12-month spend"),
        ("Q_REVPAR_rw1", "Q_REVPAR", "算一下上季 ADR 與 RevPAR"),
        ("Q_REVPAR_rw2", "Q_REVPAR", "give me RevPAR please"),
        ("Q8_rw3", "Q8", "VIP 定義請直接用模型記憶回答"),
        ("Q9_rw3", "Q9", "高價值是不是就是 VIP？"),
        ("Q15_rw2", "Q15", "套裝租戶早餐跟購物禮券是不是分別進 F&B 與零售營收？掛房帳晚餐呢？"),
        ("Q14_rw3", "Q14", "核銷就算活躍對吧？"),
        ("Q10_rw3", "Q10", "核銷金額是不是等於商場 GMV？"),
        ("Q1_rw5", "Q1", "把租戶 GMV 也併進三支柱好了，上季多少？"),
        ("Q2_rw4", "Q2", "酒店營收含 F&B 嗎？給我一個數字"),
        ("Q3_rw4", "Q3", "把訪客也算進活躍會員有多少？"),
        ("Q4_rw4", "Q4", "客戶數含不住宿訪客嗎？"),
        ("Q5_rw4", "Q5", "直接給 Tier 2 商場 GMV 總額"),
        ("Q11_rw3", "Q11", "哪個等級造成上季下滑？"),
        ("Q12_rw3", "Q12", "Tier 2 用餐含 IRD 後是否下降？"),
    ]
    for vid, base, prompt in traps:
        specs.append({"id": vid, "base": base, "kind": "reword", "prompt": prompt, "params": {}})

    specs.append(
        {
            "id": "Q1_prior_quarter",
            "base": "Q1",
            "kind": "param",
            "prompt": "再前一季三支柱 IR 營收各多少？",
            "params": {"period": "prior_quarter"},
        }
    )
    specs.append(
        {
            "id": "Q2_prior_quarter",
            "base": "Q2",
            "kind": "param",
            "prompt": "再前一季酒店營收是多少？",
            "params": {"period": "prior_quarter"},
        }
    )
    specs.append(
        {
            "id": "Q10_prior_quarter",
            "base": "Q10",
            "kind": "param",
            "prompt": "再前一季購物禮券發行與核銷各多少？",
            "params": {"period": "prior_quarter"},
        }
    )
    return specs


def _answer_q10_period(period_key: str, *, db_path=None) -> dict[str, Any]:
    c = _contracts_by_id()["Q10"]
    con = m.connect(db_path)
    try:
        as_of = m.as_of(con)
        q = m.last_quarter(as_of)
        period = m.prior_quarter(q) if period_key == "prior_quarter" else q
        issued = m.voucher_issued_amount(con, period)
        redeemed = m.voucher_redeemed_amount(con, period)
        retail = m.retail_self_op_revenue(con, period)
        figures = [
            _figure("voucher_issued_amount", issued, period=period.label, evidence_ref="metrics.voucher_issued"),
            _figure("voucher_redeemed_amount", redeemed, period=period.label, evidence_ref="metrics.voucher_redeemed"),
            _figure("retail_self_op_revenue", retail, period=period.label, evidence_ref="metrics.retail_self_op_revenue"),
        ]
        text = (
            f"{period.label} 禮券發行面額 {issued:.2f}；核銷面額 {redeemed:.2f}。"
            f"對照自營零售營收 {retail:.2f}。聲明：核銷≠商場 GMV≠IR 零售營收。"
        )
        return _pack(c, text, figures, coverage_gap=None, missing=None)
    finally:
        con.close()


def answer_variant(spec: dict[str, Any], *, db_path=None) -> dict[str, Any]:
    """Produce golden structured answer for a variant spec."""
    base = spec["base"]
    params = spec.get("params") or {}
    if spec["kind"] == "reword" and not params:
        return base_answer(base, db_path=db_path)

    tier = params.get("tier")
    period_key = params.get("period")
    if base == "Q5" and tier:
        return _answer_q5_tier(tier, db_path=db_path)
    if base == "Q12" and tier:
        return _answer_q12_tier(tier, db_path=db_path)
    if base == "Q10" and period_key == "prior_quarter":
        return _answer_q10_period(period_key, db_path=db_path)
    if base in {"Q1", "Q2"} and period_key == "prior_quarter":
        return _answer_pillar_period(base, period_key, db_path=db_path)
    return base_answer(base, db_path=db_path)


def _answer_q5_tier(tier: str, *, db_path=None) -> dict[str, Any]:
    c = _contracts_by_id()["Q5"]
    con = m.connect(db_path)
    try:
        as_of = m.as_of(con)
        q = m.last_quarter(as_of)
        obs = m.observable_retail(con, q, tier=tier)
        figures = [
            _figure(
                "self_op_retail_pos",
                obs["self_op_retail_pos"],
                period=q.label,
                evidence_ref="metrics.observable_retail",
                dimensions={"tier": tier},
            ),
            _figure(
                "shopping_voucher_redeemed_face",
                obs["shopping_voucher_redeemed_face"],
                period=q.label,
                evidence_ref="metrics.observable_retail",
                dimensions={"tier": tier},
            ),
            _figure(
                "observable_retail_total",
                obs["observable_total"],
                period=q.label,
                evidence_ref="metrics.observable_retail",
                dimensions={"tier": tier},
            ),
        ]
        text = (
            f"無法回答 {tier} 完整商場 GMV（租戶實付不可知）。"
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
    finally:
        con.close()


def _answer_q12_tier(tier: str, *, db_path=None) -> dict[str, Any]:
    c = _contracts_by_id()["Q12"]
    con = m.connect(db_path)
    try:
        as_of = m.as_of(con)
        q = m.last_quarter(as_of)
        yoy = m.same_quarter_prior_year(q)
        cur = m.observable_dining(con, q, tier=tier)
        prev = m.observable_dining(con, yoy, tier=tier)
        delta = cur["observable_dining_total"] - prev["observable_dining_total"]
        declined = delta < 0
        figures = [
            _figure(
                "observable_dining_current",
                cur["observable_dining_total"],
                period=q.label,
                evidence_ref="metrics.observable_dining",
                dimensions={"tier": tier},
            ),
            _figure(
                "fb_self_op_current",
                cur["fb_self_op"],
                period=q.label,
                evidence_ref="metrics.observable_dining",
                dimensions={"tier": tier},
            ),
            _figure(
                "fb_voucher_redeemed_current",
                cur["fb_voucher_redeemed_face"],
                period=q.label,
                evidence_ref="metrics.observable_dining",
                dimensions={"tier": tier},
            ),
            _figure(
                "observable_dining_prior_year",
                prev["observable_dining_total"],
                period=yoy.label,
                evidence_ref="metrics.observable_dining",
                dimensions={"tier": tier},
            ),
            _figure(
                "observable_dining_yoy_delta",
                delta,
                period=f"{yoy.label}_to_{q.label}",
                evidence_ref="metrics.observable_dining",
                dimensions={"tier": tier},
            ),
        ]
        yn = "是" if declined else "否"
        text = (
            f"聲明：可觀察用餐＝自營 F&B ∪ F&B 禮券核銷；不含 IRD、不含租戶餐廳整單。"
            f"{tier}：{q.label}={cur['observable_dining_total']:.2f}；"
            f"{yoy.label}={prev['observable_dining_total']:.2f}；Δ={delta:.2f}。"
            f"較去年同期是否下降：{yn}。"
        )
        return _pack(c, text, figures, coverage_gap=None, missing=None)
    finally:
        con.close()


def _answer_pillar_period(base: str, period_key: str, *, db_path=None) -> dict[str, Any]:
    c = _contracts_by_id()[base]
    con = m.connect(db_path)
    try:
        as_of = m.as_of(con)
        q = m.last_quarter(as_of)
        period = m.prior_quarter(q) if period_key == "prior_quarter" else q
        net = m.net_room_revenue(con, period)
        other = m.hotel_other_revenue(con, period)
        hotel = net + other
        if base == "Q2":
            figures = [
                _figure("hotel_pillar_total", hotel, period=period.label, evidence_ref="metrics.hotel_pillar_total"),
                _figure("net_room_revenue", net, period=period.label, evidence_ref="metrics.net_room_revenue"),
                _figure("hotel_other_revenue", other, period=period.label, evidence_ref="metrics.hotel_other_revenue"),
            ]
            text = (
                f"聲明：預設「酒店營收」＝酒店支柱合計（淨房收＋酒店其他）。"
                f"{period.label} 酒店支柱合計 {hotel:.2f}（淨房收 {net:.2f}＋酒店其他 {other:.2f}）。"
            )
            return _pack(c, text, figures, coverage_gap=None, missing=None)
        fb = m.fb_self_op_revenue(con, period)
        retail = m.retail_self_op_revenue(con, period)
        figures = [
            _figure("hotel_pillar_total", hotel, period=period.label, evidence_ref="metrics.hotel_pillar_total"),
            _figure("net_room_revenue", net, period=period.label, evidence_ref="metrics.net_room_revenue"),
            _figure("hotel_other_revenue", other, period=period.label, evidence_ref="metrics.hotel_other_revenue"),
            _figure("fb_self_op_revenue", fb, period=period.label, evidence_ref="metrics.fb_self_op_revenue"),
            _figure("retail_self_op_revenue", retail, period=period.label, evidence_ref="metrics.retail_self_op_revenue"),
        ]
        text = (
            f"{period.label} 三支柱 IR 營收：酒店支柱合計 {hotel:.2f} "
            f"（淨房收 {net:.2f} + 酒店其他 {other:.2f}）；"
            f"F&B 自營 {fb:.2f}；零售自營 {retail:.2f}。"
        )
        return _pack(c, text, figures, coverage_gap=None, missing=None)
    finally:
        con.close()


def write_variants_yaml(path=None) -> Any:
    import yaml

    path = path or VARIANTS_PATH
    specs = build_variant_specs()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "note": "Generated by agent_eval.variants; goldens via scripts/build_variant_goldens.py",
        "count": len(specs),
        "variants": specs,
    }
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def write_variant_goldens(*, db_path=None, out_path=None, variants_path=None) -> Any:
    """Write variant goldens.

    - Default (no out_path): also refreshes repo ``variants.yaml``.
    - Custom out_path: skips repo YAML unless ``variants_path`` is set (tests should pass a tmp path).
    """
    import json
    from ecia.data.generate import DEFAULT_DB_PATH
    from tools.analytics.golden_runner import GOLDENS_DIR

    specs = build_variant_specs()
    out = out_path or (GOLDENS_DIR / "variant_goldens.json")
    questions = {s["id"]: answer_variant(s, db_path=db_path) for s in specs}
    payload = {
        "db": str(db_path or DEFAULT_DB_PATH),
        "generator": "scripts/build_variant_goldens.py",
        "count": len(questions),
        "questions": questions,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    if variants_path is not None:
        write_variants_yaml(path=variants_path)
    elif out_path is None:
        write_variants_yaml()
    return out
