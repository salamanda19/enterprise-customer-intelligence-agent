"""Local Streamlit UI: Ask | Explore | SQL (I8).

Run: streamlit run src/explore/ui.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from agent.meta import attach_meta
from agent.orchestrator import handle
from ecia.config_loader import REPO_ROOT, load_app_config, load_yaml
from explore.service import (
    ExploreError,
    aggregate,
    list_tables,
    preview,
    summarize,
    table_columns,
)
from tools.sql.readonly import run_sql


def _contracts() -> list[dict]:
    data = load_yaml(REPO_ROOT / "eval" / "questions" / "contracts.yaml")
    return list(data["questions"])


def _ask_tab() -> None:
    st.subheader("Ask")
    st.caption("Calls the same `handle()` path as CLI / HTTP (deterministic-first).")
    contracts = _contracts()
    ids = [""] + [c["id"] for c in contracts]
    qid = st.selectbox("Question id (optional)", ids, index=0)
    default_prompt = ""
    if qid:
        by_id = {c["id"]: c for c in contracts}
        default_prompt = by_id[qid]["prompt"]
    question = st.text_area("Question", value=default_prompt, height=120)
    if st.button("Run ask", type="primary"):
        if not question.strip() and not qid:
            st.error("Provide a question and/or question id")
            return
        t0 = time.perf_counter()
        result = attach_meta(
            handle(question or default_prompt, question_id=qid or None),
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
        st.markdown(f"**Mode:** `{result.get('response_mode')}`")
        st.markdown(f"**Reason codes:** `{result.get('reason_codes')}`")
        st.write(result.get("answer_text"))
        figures = result.get("figures") or []
        if figures:
            st.markdown("**Figures**")
            st.json(figures)
        with st.expander("Full structured response"):
            st.json(result)


def _explore_tab() -> None:
    st.subheader("Explore")
    cfg = load_app_config().get("explore") or {}
    st.caption(
        f"Push-down summaries (preview_rows={cfg.get('preview_rows')}, "
        f"aggregate_result_cap={cfg.get('aggregate_result_cap')}). "
        "Means are not computed on a pre-LIMIT detail slice."
    )
    try:
        tables = list_tables()
    except ExploreError as exc:
        st.error(str(exc))
        return
    if not tables:
        st.warning("No allowlisted tables found. Run `python scripts/rebuild_db.py`.")
        return

    table = st.selectbox("Table", tables)
    cols = table_columns(table)
    col_names = [c["name"] for c in cols]

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("COUNT(*)"):
            prev = preview(table, limit=1)
            if prev.ok and prev.data:
                st.metric("Row count", prev.data["row_count"])
            else:
                st.error(prev.error or "COUNT failed")
    with c2:
        preview_n = st.number_input(
            "Preview rows",
            min_value=1,
            max_value=1000,
            value=int(cfg.get("preview_rows") or 100),
        )
    with c3:
        use_sample = st.checkbox("Sample preview", value=False)

    if st.button("Preview"):
        res = preview(table, limit=int(preview_n), sample=use_sample)
        if not res.ok:
            st.error(res.error)
        else:
            st.write(f"Table rows: {res.data['row_count']} · showing {res.data['preview_rows']}")
            st.dataframe(res.data["rows"], use_container_width=True)

    st.markdown("---")
    st.markdown("**Column metrics**")
    full_scan = st.checkbox("Full scan for summarize", value=True)
    if st.button("Summarize columns"):
        res = summarize(table, full_scan=full_scan)
        if not res.ok:
            st.error(res.error)
        else:
            st.caption(f"Scan: {res.data.get('scan')}")
            st.dataframe(res.data["summary"], use_container_width=True)
            vc = res.data.get("value_counts") or {}
            if vc:
                for cname, rows in vc.items():
                    st.markdown(f"Top values — `{cname}`")
                    st.dataframe(rows, use_container_width=True)

    st.markdown("---")
    st.markdown("**Group-by (1–2 dims)**")
    dims = st.multiselect("Group by", col_names, max_selections=2)
    metric_fn = st.selectbox("Metric", ["count", "sum", "avg", "min", "max"])
    metric_col = None
    if metric_fn != "count":
        metric_col = st.selectbox("Metric column", col_names)
    if st.button("Aggregate") and dims:
        metrics = [{"fn": metric_fn, "column": metric_col or "*"}]
        res = aggregate(table, group_by=dims, metrics=metrics, full_scan=True)
        if not res.ok:
            st.error(res.error)
        else:
            st.caption(f"Scan: {res.data.get('scan')} · cap={res.data.get('result_cap')}")
            st.dataframe(res.data["rows"], use_container_width=True)
    elif st.button("Aggregate") and not dims:
        st.error("Select 1–2 group-by columns")


def _sql_tab() -> None:
    st.subheader("SQL")
    st.caption("Read-only `run_sql()` — writes rejected; detail results row-capped.")
    sql = st.text_area("SELECT …", height=160, placeholder="SELECT tier, COUNT(*) AS n FROM members GROUP BY 1")
    if st.button("Run SQL", type="primary"):
        res = run_sql(sql)
        if not res.ok:
            st.error(res.error)
            if res.sql:
                st.code(res.sql)
        else:
            st.success(f"{len(res.rows or [])} row(s)")
            st.dataframe(res.rows, use_container_width=True)
            with st.expander("Executed SQL"):
                st.code(res.sql)


def main() -> None:
    st.set_page_config(page_title="ECIA Explore", layout="wide")
    st.title("Enterprise Customer Intelligence Agent")
    st.caption("Local Ask / Explore / SQL — not a product UI; same policy + RO SQL as CLI.")
    tab_ask, tab_explore, tab_sql = st.tabs(["Ask", "Explore", "SQL"])
    with tab_ask:
        _ask_tab()
    with tab_explore:
        _explore_tab()
    with tab_sql:
        _sql_tab()


if __name__ == "__main__":
    main()
