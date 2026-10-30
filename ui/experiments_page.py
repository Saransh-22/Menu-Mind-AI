"""
Experiments page — premium redesign.
All orchestrator, form, result comparison logic preserved.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from database import repository as repo
from agent.schemas import ExperimentPlan
from services.analytics_service import analyze_sales

logger = logging.getLogger(__name__)

STATUS_STYLES = {
    "proposed":  ("#e8f0ff", "#6c63ff", "💡"),
    "approved":  ("#e8f7f4", "#27ae60", "✅"),
    "active":    ("#fff8e8", "#f39c12", "🔄"),
    "completed": ("#f0f0f0", "#455060", "🏁"),
    "cancelled": ("#fde8e8", "#e74c3c", "❌"),
}


def _section(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)


def render_experiments_page():
    st.markdown(
        "<h1 style='margin-bottom:4px;'>🧪 Experiments & Outcomes</h1>"
        "<p style='color:#6b7a8d;font-size:0.92rem;margin-bottom:24px;'>Propose, track and evaluate menu experiments.</p>",
        unsafe_allow_html=True,
    )

    run_id = st.session_state.get("active_run_id")
    if not run_id:
        st.info("Create or load a restaurant on the Overview page first.", icon="ℹ️")
        return

    experiments = repo.list_experiments(run_id)

    # ── Summary row ────────────────────────────────────────────────────────
    status_counts = {}
    for exp in experiments:
        s = exp.get("status", "proposed")
        status_counts[s] = status_counts.get(s, 0) + 1

    if experiments:
        cols = st.columns(5)
        for col, (status, icon_str) in zip(cols, [
            ("proposed", "💡"), ("approved", "✅"), ("active", "🔄"),
            ("completed", "🏁"), ("cancelled", "❌")
        ]):
            col.metric(f"{icon_str} {status.capitalize()}", status_counts.get(status, 0))
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Create form ────────────────────────────────────────────────────────
    with st.expander(
        "➕  Create New Experiment",
        expanded=bool(st.session_state.get("create_experiment_for")),
    ):
        _render_create_form(run_id)

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Experiment list ────────────────────────────────────────────────────
    if not experiments:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:40px 32px;text-align:center;
                border:1px solid #e8edf4;">
                <div style="font-size:2em;margin-bottom:10px;">🧪</div>
                <div style="font-size:1.05rem;font-weight:600;color:#0d1b2a;margin-bottom:8px;">No Experiments Yet</div>
                <div style="color:#8896a8;font-size:0.88rem;">Create an experiment above, or approve a recommendation in AI Recommendations.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    _section(f"All Experiments ({len(experiments)})")
    for exp in experiments:
        _render_experiment_card(exp, run_id)


def _render_create_form(run_id: int):
    prefill = st.session_state.pop("create_experiment_for", None) or {}

    with st.form(key="create_experiment_form"):
        default_title = (prefill.get("item_name", "") + " — Price Test") if prefill else ""
        title = st.text_input("Experiment Title *", value=default_title, placeholder="e.g. Margherita Pizza Price Test")
        hypothesis = st.text_area(
            "Hypothesis *",
            value=f"Adjusting {prefill.get('item_name', 'the item')} will improve performance." if prefill else "",
            placeholder="e.g. Increasing the price of Margherita Pizza by ₹20 will maintain quantity sold.",
        )
        intervention = st.text_area(
            "Proposed Intervention",
            placeholder="e.g. Increase price from ₹299 to ₹319",
        )

        col1, col2 = st.columns(2)
        baseline_start = col1.date_input("Baseline Start", value=date.today() - timedelta(days=30))
        baseline_end = col2.date_input("Baseline End", value=date.today())
        col3, col4 = st.columns(2)
        test_start = col3.date_input("Test Start", value=date.today() + timedelta(days=1))
        test_end = col4.date_input("Test End", value=date.today() + timedelta(days=29))

        success_criteria = st.text_area(
            "Success Criteria",
            placeholder="e.g. Revenue for item increases by ≥5% without reducing quantity by >10%",
        )
        guardrail_metrics = st.text_area(
            "Guardrail Metrics",
            placeholder="e.g. Overall restaurant revenue does not decline by >3%",
        )

        if st.form_submit_button("💾  Save Experiment", type="primary"):
            if not title or not hypothesis:
                st.error("Title and hypothesis are required.")
            else:
                exp_id = repo.create_experiment(run_id, {
                    "title": title, "hypothesis": hypothesis, "intervention": intervention,
                    "baseline_start": str(baseline_start), "baseline_end": str(baseline_end),
                    "test_start": str(test_start), "test_end": str(test_end),
                    "success_criteria": success_criteria, "guardrail_metrics": guardrail_metrics,
                    "recommendation_id": prefill.get("id"), "status": "proposed",
                })
                st.success(f"✅ Experiment created (ID: {exp_id}).")
                st.rerun()


def _render_experiment_card(exp: dict, run_id: int):
    status = exp.get("status", "proposed")
    bg, border, icon = STATUS_STYLES.get(status, ("#f5f6f8", "#8896a8", "ℹ️"))
    exp_id = exp["id"]

    st.markdown(
        f"""<div style="background:{bg};border-radius:14px;border-left:5px solid {border};
            padding:18px 22px;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-size:1.3em;">{icon}</span>
                <strong style="font-size:1.0rem;color:#0d1b2a;">{exp.get("title","Untitled")}</strong>
                <span style="background:{border}20;color:{border};border-radius:20px;
                    padding:3px 11px;font-size:0.78rem;font-weight:700;">{status.upper()}</span>
                <span style="margin-left:auto;font-size:0.8rem;color:#6b7a8d;">
                    {exp.get("baseline_start","?")} → {exp.get("test_end","?")}
                </span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.expander(f"Details — {exp.get('title','Untitled')}"):
        c1, c2 = st.columns(2)
        c1.write(f"**Hypothesis:** {exp.get('hypothesis','—')}")
        c2.write(f"**Intervention:** {exp.get('intervention','—')}")
        st.write(
            f"**Baseline:** {exp.get('baseline_start')} → {exp.get('baseline_end')} &nbsp;|&nbsp; "
            f"**Test:** {exp.get('test_start')} → {exp.get('test_end')}"
        )
        if exp.get("success_criteria"):
            st.write(f"**Success Criteria:** {exp['success_criteria']}")
        if exp.get("guardrail_metrics"):
            st.write(f"**Guardrails:** {exp['guardrail_metrics']}")

        # Status controls
        if status == "proposed":
            bc = st.columns(2)
            if bc[0].button("✅ Approve", key=f"approve_exp_{exp_id}"):
                repo.update_experiment_status(exp_id, "approved")
                st.rerun()
            if bc[1].button("❌ Cancel", key=f"cancel_exp_{exp_id}"):
                repo.update_experiment_status(exp_id, "cancelled")
                st.rerun()
        elif status == "approved":
            if st.button("▶️ Mark Active", key=f"active_exp_{exp_id}"):
                repo.update_experiment_status(exp_id, "active")
                st.rerun()
        elif status == "active":
            st.markdown("**📊 Upload Follow-Up Sales Data**")
            followup = st.file_uploader(
                "Upload follow-up sales CSV/XLSX",
                type=["csv", "xlsx"],
                key=f"followup_{exp_id}",
            )
            if followup:
                from services.ingestion_service import ingest_sales
                from services.preprocessing_service import clean_sales
                raw = followup.read()
                df, _, _ = ingest_sales(raw, followup.name)
                menu_df = st.session_state.get("menu_df")
                df_clean, _, _ = clean_sales(df, menu_df)
                baseline_sales = st.session_state.get("sales_df")
                if baseline_sales is not None:
                    _compare_results(exp_id, exp, baseline_sales, df_clean)
            if st.button("🏁 Mark Completed", key=f"complete_exp_{exp_id}"):
                repo.update_experiment_status(exp_id, "completed")
                st.rerun()

        # Existing results
        results = repo.get_experiment_results(exp_id)
        if results:
            st.markdown("**📈 Measured Outcomes**")
            df_res = pd.DataFrame(results)
            show = [c for c in ("metric_name", "baseline_value", "test_value", "change_pct", "notes") if c in df_res.columns]
            st.dataframe(df_res[show], use_container_width=True, hide_index=True)
            st.caption("⚠️ Comparison shows measured differences only — not causal evidence without a controlled test.")


def _compare_results(exp_id: int, exp: dict, baseline_df: pd.DataFrame, followup_df: pd.DataFrame):
    for df in (baseline_df, followup_df):
        for col in ("revenue", "quantity_sold"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    base_rev = float(baseline_df["revenue"].sum()) if "revenue" in baseline_df.columns else 0
    test_rev = float(followup_df["revenue"].sum()) if "revenue" in followup_df.columns else 0
    base_qty = float(baseline_df["quantity_sold"].sum()) if "quantity_sold" in baseline_df.columns else 0
    test_qty = float(followup_df["quantity_sold"].sum()) if "quantity_sold" in followup_df.columns else 0

    def pct(b, t): return round((t - b) / b * 100, 2) if b != 0 else None

    results = [
        {"metric_name": "Total Revenue (₹)", "baseline_value": round(base_rev, 2), "test_value": round(test_rev, 2), "change_pct": pct(base_rev, test_rev), "notes": ""},
        {"metric_name": "Total Units Sold", "baseline_value": round(base_qty, 2), "test_value": round(test_qty, 2), "change_pct": pct(base_qty, test_qty), "notes": ""},
    ]

    # Calculate average selling price comparison
    base_asp = (base_rev / base_qty) if base_qty > 0 else 0
    test_asp = (test_rev / test_qty) if test_qty > 0 else 0
    results.append({
        "metric_name": "Average Selling Price (₹)",
        "baseline_value": round(base_asp, 2),
        "test_value": round(test_asp, 2),
        "change_pct": pct(base_asp, test_asp),
        "notes": "",
    })

    repo.save_experiment_result(exp_id, results)
    st.success("Comparison calculated and saved.")
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    st.warning("This shows observational before/after differences — not causal proof of the intervention's effect.")
    st.rerun()
