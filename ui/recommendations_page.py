"""
AI Recommendations page — Executive SaaS interface for MenuMind AI.
Features grounded evidence synthesis, interactive approvals, experiment linking,
priority and action filtering, detailed data breakdown tabs, and CSV export.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import streamlit as st
import pandas as pd

from agent.schemas import AgentState, MenuAction, Priority, Recommendation
from agent.orchestrator import run_analysis
from database import repository as repo

logger = logging.getLogger(__name__)

ACTION_STYLES = {
    MenuAction.IMPROVE:               ("#fff8e8", "#f39c12", "🔧", "Improve"),
    MenuAction.REMOVE:                ("#fde8e8", "#e74c3c", "🗑️", "Remove"),
    MenuAction.PROMOTE:               ("#e8f7f4", "#27ae60", "🚀", "Promote"),
    MenuAction.REPRICE:               ("#eef2ff", "#4f46e5", "💲", "Reprice"),
    MenuAction.INSUFFICIENT_EVIDENCE: ("#f8fafc", "#64748b", "❓", "More Info"),
}

PRIORITY_STYLES = {
    Priority.HIGH:   ("#fde8e8", "#e74c3c", "High"),
    Priority.MEDIUM: ("#fff8e8", "#f39c12", "Medium"),
    Priority.LOW:    ("#f0fdf4", "#0d9488", "Low"),
}

APPROVAL_STYLES = {
    "approved":        ("#dcfce7", "#15803d", "✅ Approved"),
    "rejected":        ("#fee2e2", "#b91c1c", "❌ Rejected"),
    "saved_for_later": ("#ffedd5", "#c2410c", "🔖 Saved for Later"),
    "pending":         ("#f1f5f9", "#475569", "⏳ Pending Review"),
}


def render_recommendations_page():
    st.markdown(
        """<div style="margin-bottom:20px;">
            <h1 style="font-size:1.85rem;font-weight:700;color:#0d1b2a;margin-bottom:4px;">
                🤖 AI Recommendations
            </h1>
            <p style="color:#64748b;font-size:0.92rem;margin-bottom:0;">
                Evidence-grounded menu optimization strategies synthesizing sales volume, profit margins, 
                customer reviews, and food waste intelligence.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    run_id = st.session_state.get("active_run_id")
    if not run_id:
        st.info("Please create or select a restaurant on the Overview page first.", icon="ℹ️")
        return

    # ── Top Action & Run Row ────────────────────────────────────────────────
    col_run, col_meta = st.columns([2, 4])
    with col_run:
        btn_label = "▶️  Re-run AI Analysis" if st.session_state.get("agent_state") else "▶️  Run AI Analysis"
        if st.button(btn_label, type="primary", use_container_width=True):
            _run_agent(run_id)

    with col_meta:
        rest_name = st.session_state.get("restaurant_info", {}).get("name", "Active Restaurant")
        st.markdown(
            f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                padding:8px 14px;font-size:0.86rem;color:#475569;display:flex;align-items:center;height:100%;">
                <span>📍 Target Restaurant: <strong style="color:#0f172a;">{rest_name}</strong> &nbsp;|&nbsp; Run ID: <code>#{run_id}</code></span>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Fetch Live & Persisted Recommendations ──────────────────────────────
    state: Optional[AgentState] = st.session_state.get("agent_state")
    live_recs: list[Recommendation] = state.recommendations if state else []
    db_recs = repo.list_recommendations(run_id) if run_id else []

    # Map DB records by (item_name, action)
    db_rec_lookup: dict[tuple[str, str], dict] = {
        (str(r["item_name"]).strip().lower(), str(r["action"]).upper()): r
        for r in db_recs
    }

    # Normalize to a unified recommendation list
    unified_items: list[dict] = []
    if live_recs:
        for rec in live_recs:
            key = (rec.item_name.strip().lower(), rec.action.value.upper())
            db_match = db_rec_lookup.get(key)
            if not db_match:
                rec_id = repo.save_recommendation(run_id, rec.model_dump(mode="json"))
                db_match = {"id": rec_id}
                db_rec_lookup[key] = db_match
            rec_id = db_match.get("id")
            approval = repo.get_approval(rec_id) if rec_id else None
            unified_items.append({
                "id": rec_id,
                "rec_obj": rec,
                "item_name": rec.item_name,
                "action": rec.action,
                "priority": rec.priority,
                "confidence_score": rec.confidence_score,
                "title": getattr(rec, "title", None) or f"{rec.action.value.replace('_', ' ').title()}: {rec.item_name}",
                "suggested_action": getattr(rec, "suggested_action", None) or rec.reasoning[:140],
                "reasoning": rec.reasoning,
                "alternative_actions": rec.alternative_actions,
                "expected_benefits": rec.expected_benefits,
                "potential_risks": rec.potential_risks,
                "missing_information": rec.missing_information,
                "next_steps": rec.next_steps,
                "sales_metrics": rec.sales_metrics or {},
                "review_themes": rec.review_themes or {},
                "profitability": rec.profitability or {},
                "success_metrics": rec.success_metrics,
                "approval": approval,
                "approval_status": approval["decision"] if approval else "pending",
            })
    elif db_recs:
        for r in db_recs:
            rec_id = r.get("id")
            approval = repo.get_approval(rec_id) if rec_id else None
            action_raw = str(r.get("action", "INSUFFICIENT_EVIDENCE")).upper()
            try:
                action = MenuAction(action_raw)
            except ValueError:
                action = MenuAction.INSUFFICIENT_EVIDENCE
            prio_raw = str(r.get("priority", "low")).lower()
            try:
                priority = Priority(prio_raw)
            except ValueError:
                priority = Priority.LOW

            unified_items.append({
                "id": rec_id,
                "rec_obj": None,
                "item_name": r.get("item_name", "Unknown"),
                "action": action,
                "priority": priority,
                "confidence_score": float(r.get("confidence_score", 0.5)),
                "title": f"{action.value.replace('_', ' ').title()}: {r.get('item_name')}",
                "suggested_action": str(r.get("reasoning", ""))[:140],
                "reasoning": r.get("reasoning", ""),
                "alternative_actions": r.get("alternative_actions", []),
                "expected_benefits": r.get("expected_benefits", ""),
                "potential_risks": r.get("potential_risks", ""),
                "missing_information": r.get("missing_information", ""),
                "next_steps": r.get("next_steps", []),
                "sales_metrics": r.get("sales_metrics") or {},
                "review_themes": r.get("review_themes") or {},
                "profitability": r.get("profitability") or {},
                "success_metrics": r.get("success_metrics", ""),
                "approval": approval,
                "approval_status": approval["decision"] if approval else "pending",
            })

    if not unified_items:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:48px 32px;text-align:center;
                border:1px solid #e2e8f0;margin-top:20px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:2.8rem;margin-bottom:12px;">💡</div>
                <div style="font-size:1.15rem;font-weight:700;color:#0d1b2a;margin-bottom:8px;">
                    No Recommendations Available Yet
                </div>
                <div style="color:#64748b;font-size:0.92rem;max-width:540px;margin:0 auto 16px auto;line-height:1.5;">
                    MenuMind synthesizes your menu, sales numbers, ingredient costs, guest reviews, and kitchen waste 
                    to generate tactical recommendations.
                </div>
                <div style="color:#475569;font-size:0.86rem;">
                    Click <strong>▶️ Run AI Analysis</strong> above to generate real-time recommendations.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # ── Executive KPI Summary Cards ─────────────────────────────────────────
    total_recs = len(unified_items)
    promote_count = sum(1 for u in unified_items if u["action"] == MenuAction.PROMOTE)
    reprice_count = sum(1 for u in unified_items if u["action"] == MenuAction.REPRICE)
    improve_count = sum(1 for u in unified_items if u["action"] == MenuAction.IMPROVE)
    remove_count = sum(1 for u in unified_items if u["action"] == MenuAction.REMOVE)
    approved_count = sum(1 for u in unified_items if u["approval_status"] == "approved")
    pending_count = sum(1 for u in unified_items if u["approval_status"] == "pending")

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Items", total_recs)
    k2.metric("🚀 Promote", promote_count)
    k3.metric("💲 Reprice", reprice_count)
    k4.metric("🔧 Improve", improve_count)
    k5.metric("🗑️ Remove", remove_count)
    k6.metric("✅ Approved", f"{approved_count}/{total_recs}")

    st.markdown("<hr style='margin:16px 0 20px 0;border:none;border-top:1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # ── Interactive Filter & Search Controls ────────────────────────────────
    f1, f2, f3, f4 = st.columns([3, 2, 2, 3])
    with f1:
        search_query = st.text_input(
            "Search item:",
            placeholder="🔍 Search by dish name...",
            label_visibility="collapsed",
        ).strip().lower()

    with f2:
        action_options = ["All Actions"] + [a.value for a in MenuAction]
        selected_action = st.selectbox("Action filter:", options=action_options, label_visibility="collapsed")

    with f3:
        status_options = ["All Statuses", "Pending Review", "Approved", "Rejected", "Saved for Later"]
        selected_status = st.selectbox("Status filter:", options=status_options, label_visibility="collapsed")

    with f4:
        # CSV Export Button
        export_rows = []
        for u in unified_items:
            export_rows.append({
                "Item Name": u["item_name"],
                "Action": u["action"].value if hasattr(u["action"], "value") else str(u["action"]),
                "Priority": u["priority"].value if hasattr(u["priority"], "value") else str(u["priority"]),
                "Confidence": f"{u['confidence_score']:.0%}",
                "Headline": u["title"],
                "Suggested Action": u["suggested_action"],
                "Reasoning": u["reasoning"],
                "Expected Benefits": u["expected_benefits"],
                "Potential Risks": u["potential_risks"],
                "Success Metrics": u["success_metrics"],
                "Decision": u["approval_status"],
            })
        export_df = pd.DataFrame(export_rows)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Export Recommendations CSV",
            data=csv_bytes,
            file_name=f"menumind_recommendations_run_{run_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ── Filter items ────────────────────────────────────────────────────────
    filtered_items = []
    status_map = {
        "Pending Review": "pending",
        "Approved": "approved",
        "Rejected": "rejected",
        "Saved for Later": "saved_for_later",
    }
    for u in unified_items:
        if search_query and search_query not in u["item_name"].lower():
            continue
        if selected_action != "All Actions" and u["action"].value != selected_action:
            continue
        if selected_status != "All Statuses" and u["approval_status"] != status_map.get(selected_status):
            continue
        filtered_items.append(u)

    st.markdown(
        f"<div style='font-size:0.88rem;color:#64748b;margin:12px 0 16px 0;'>"
        f"Showing <strong>{len(filtered_items)}</strong> of {total_recs} recommendations"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Render Cards ────────────────────────────────────────────────────────
    for item in filtered_items:
        _render_recommendation_card(item, run_id)


def _render_recommendation_card(item: dict, run_id: int):
    action: MenuAction = item["action"]
    priority: Priority = item["priority"]
    approval_status = item["approval_status"]

    bg, border, icon, action_label = ACTION_STYLES.get(action, ("#f8fafc", "#64748b", "ℹ️", "Info"))
    p_bg, p_border, p_label = PRIORITY_STYLES.get(priority, ("#f8fafc", "#64748b", "Low"))
    app_bg, app_color, app_label = APPROVAL_STYLES.get(approval_status, ("#f1f5f9", "#475569", "Pending"))

    rec_id = item["id"]
    confidence_pct = int(item["confidence_score"] * 100)
    conf_color = "#15803d" if confidence_pct >= 75 else ("#b45309" if confidence_pct >= 50 else "#64748b")

    st.markdown(
        f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:5px solid {border};
            border-radius:12px;padding:18px 22px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <!-- Header Row -->
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
                <span style="font-size:1.35rem;">{icon}</span>
                <span style="font-size:1.1rem;font-weight:700;color:#0d1b2a;">{item['item_name']}</span>
                
                <!-- Action Badge -->
                <span style="background:{border}18;color:{border};border-radius:20px;padding:3px 12px;
                    font-size:0.78rem;font-weight:700;letter-spacing:0.3px;">
                    {action_label.upper()}
                </span>
                
                <!-- Priority Badge -->
                <span style="background:{p_bg};color:{p_border};border:1px solid {p_border}33;
                    border-radius:20px;padding:3px 11px;font-size:0.76rem;font-weight:600;">
                    {p_label} Priority
                </span>
                
                <!-- Decision Badge -->
                <span style="background:{app_bg};color:{app_color};border-radius:20px;padding:3px 12px;
                    font-size:0.76rem;font-weight:700;margin-left:auto;">
                    {app_label}
                </span>
                
                <!-- Confidence Score -->
                <span style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:20px;padding:3px 10px;
                    font-size:0.76rem;color:{conf_color};font-weight:700;">
                    🎯 {confidence_pct}% Confidence
                </span>
            </div>

            <!-- Title / Headline -->
            <div style="font-size:0.96rem;font-weight:600;color:#1e293b;margin:6px 0 8px 0;">
                {item['title']}
            </div>

            <!-- Suggested Action Callout -->
            <div style="background:{bg};border:1px solid {border}33;border-radius:8px;padding:10px 14px;
                font-size:0.88rem;color:#1e293b;line-height:1.5;margin-bottom:10px;">
                <strong style="color:{border};">Suggested Action:</strong> {item['suggested_action']}
            </div>

            <!-- Reasoning Summary -->
            <div style="color:#475569;font-size:0.87rem;line-height:1.55;">
                {item['reasoning']}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Deep Dive Evidence Tabs ─────────────────────────────────────────────
    with st.expander(f"🔍 Detailed Evidence & Action Plan for {item['item_name']}"):
        t_evidence, t_plan, t_risks, t_metrics = st.tabs([
            "📊 Supporting Evidence",
            "💡 Action Plan & Next Steps",
            "⚖️ Benefits & Risks",
            "🎯 Success Metrics",
        ])

        with t_evidence:
            s_metrics = item.get("sales_metrics") or {}
            p_metrics = item.get("profitability") or {}
            r_metrics = item.get("review_themes") or {}

            c_e1, c_e2, c_e3 = st.columns(3)
            with c_e1:
                st.markdown("**Sales Performance**")
                qty = s_metrics.get("quantity_sold", s_metrics.get("total_quantity", 0))
                rev = s_metrics.get("revenue", s_metrics.get("total_revenue", 0.0))
                st.write(f"• Units Sold: **{qty}**")
                st.write(f"• Recorded Revenue: **${rev:,.2f}**")
                if s_metrics.get("sales_rank"):
                    st.write(f"• Sales Rank: **#{s_metrics.get('sales_rank')}**")

            with c_e2:
                st.markdown("**Profitability Profile**")
                margin = p_metrics.get("margin_pct")
                cost = p_metrics.get("total_cost", p_metrics.get("ingredient_cost"))
                if margin is not None and p_metrics.get("calculable", True):
                    st.write(f"• Contribution Margin: **{margin:.1f}%**")
                    if cost is not None:
                        st.write(f"• Total Recipe Cost: **${cost:.2f}**")
                    if p_metrics.get("selling_price"):
                        st.write(f"• Menu Price: **${p_metrics.get('selling_price'):.2f}**")
                else:
                    st.info("Recipe cost data not uploaded or insufficient to calculate margin.")

            with c_e3:
                st.markdown("**Customer Sentiment**")
                rev_count = r_metrics.get("review_count", 0)
                avg_rat = r_metrics.get("avg_rating")
                neg_pct = r_metrics.get("negative_pct", 0.0)
                pos_pct = r_metrics.get("positive_pct", 0.0)
                st.write(f"• Total Reviews / Mentions: **{rev_count}**")
                if avg_rat is not None:
                    st.write(f"• Average Rating: **{avg_rat:.1f} / 5.0**")
                if rev_count > 0:
                    st.write(f"• Positive / Negative: **{pos_pct:.0f}% / {neg_pct:.0f}%**")

            if item.get("missing_information"):
                st.markdown(
                    f"""<div style="background:#fffbeb;border:1px solid #fef3c7;border-radius:6px;
                        padding:8px 12px;font-size:0.83rem;color:#92400e;margin-top:10px;">
                        <strong>ℹ️ Data Gaps:</strong> {item['missing_information']}
                    </div>""",
                    unsafe_allow_html=True,
                )

        with t_plan:
            st.markdown("**Recommended Operational Checklist:**")
            if item.get("next_steps"):
                for idx, step in enumerate(item["next_steps"], 1):
                    st.markdown(f"**{idx}.** {step}")
            else:
                st.write("No sequential checklist available.")

            if item.get("alternative_actions"):
                st.markdown("<br>**Alternative Actions Evaluated:**", unsafe_allow_html=True)
                for alt in item["alternative_actions"]:
                    st.write(f"• {alt}")

        with t_risks:
            cr1, cr2 = st.columns(2)
            with cr1:
                st.markdown(
                    f"""<div style="background:#f0fdf4;border-left:3px solid #16a34a;padding:10px 14px;border-radius:6px;">
                        <strong style="color:#15803d;">Expected Benefits:</strong><br>
                        <span style="font-size:0.86rem;color:#166534;">{item['expected_benefits'] or 'Direct margin or volume expansion.'}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with cr2:
                st.markdown(
                    f"""<div style="background:#fff1f2;border-left:3px solid #e11d48;padding:10px 14px;border-radius:6px;">
                        <strong style="color:#be123c;">Potential Risks:</strong><br>
                        <span style="font-size:0.86rem;color:#9f1239;">{item['potential_risks'] or 'Customer adjustment period or kitchen pacing.'}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

        with t_metrics:
            st.markdown("**Success Criteria & Measurement:**")
            st.write(item.get("success_metrics") or "Track weekly order velocity and margin variance post-implementation.")

    # ── Interactive Approval Controls ───────────────────────────────────────
    card_key = f"rec_{rec_id}_{item['item_name']}"
    bc1, bc2, bc3, bc4 = st.columns(4)

    with bc1:
        is_app = (approval_status == "approved")
        if st.button("✅ Approve", key=f"app_{card_key}", type="primary" if is_app else "secondary", use_container_width=True):
            _persist_decision(rec_id, item, run_id, "approved")

    with bc2:
        is_rej = (approval_status == "rejected")
        if st.button("❌ Reject", key=f"rej_{card_key}", use_container_width=True):
            _persist_decision(rec_id, item, run_id, "rejected")

    with bc3:
        is_sav = (approval_status == "saved_for_later")
        if st.button("🔖 Save for Later", key=f"sav_{card_key}", use_container_width=True):
            _persist_decision(rec_id, item, run_id, "saved_for_later")

    with bc4:
        if st.button("🧪 Create Experiment", key=f"exp_{card_key}", use_container_width=True):
            rec_payload = item["rec_obj"].model_dump(mode="json") if item.get("rec_obj") else item
            st.session_state["create_experiment_for"] = rec_payload
            st.session_state["_nav_to"] = "🧪  Experiments"
            st.rerun()

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


def _persist_decision(rec_id: Optional[int], item: dict, run_id: int, decision: str):
    if not rec_id:
        rec_obj = item.get("rec_obj")
        payload = rec_obj.model_dump(mode="json") if rec_obj else item
        rec_id = repo.save_recommendation(run_id, payload)
    repo.save_approval(rec_id, decision)
    st.toast(f"Decision saved: '{decision.replace('_', ' ').title()}' for {item['item_name']}", icon="✅")
    st.rerun()


def _run_agent(run_id: int):
    menu_df = st.session_state.get("menu_df")
    if menu_df is None or menu_df.empty:
        st.error("Upload menu data before running analysis.")
        return

    sales_df = st.session_state.get("sales_df")
    reviews_df = st.session_state.get("reviews_df")
    costs_df = st.session_state.get("costs_df")
    waste_records = repo.list_waste_records(run_id)
    waste_df = pd.DataFrame(waste_records) if waste_records else None
    restaurant_info = st.session_state.get("restaurant_info", {})
    restaurant_name = restaurant_info.get("name", "Active Restaurant")

    prog = st.progress(0, text="Initializing MenuMind AI Agent…")
    steps: list[str] = []

    def on_progress(msg: str):
        steps.append(msg)
        prog.progress(min(int(len(steps) / 8 * 100), 95), text=msg[:80])

    with st.spinner("Analyzing menu, sales, profitability, reviews, and waste…"):
        state = run_analysis(
            run_id=run_id,
            restaurant_name=restaurant_name,
            menu_df=menu_df,
            sales_df=sales_df,
            reviews_df=reviews_df,
            costs_df=costs_df,
            waste_df=waste_df,
            progress_callback=on_progress,
        )

    prog.progress(100, text="Complete!")
    st.session_state["agent_state"] = state

    # Save generated recommendations to SQLite DB
    for rec in state.recommendations:
        repo.save_recommendation(run_id, rec.model_dump(mode="json"))

    quality = st.session_state.get("data_quality_score", 1.0)
    repo.update_run_status(run_id, "completed", quality)

    if state.error:
        st.warning(f"Agent analysis notice: {state.error}")
    else:
        st.success(f"✅ Generated {len(state.recommendations)} actionable recommendations.")
    st.rerun()
