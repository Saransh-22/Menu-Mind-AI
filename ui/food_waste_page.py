"""
Food Waste Intelligence module — Grounded kitchen waste logging, image recognition,
and sales velocity-driven spoilage risk analytics.
Clearly distinguishes measured kitchen waste from estimated predictive spoilage risks.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import repository as repo
from services.waste_analysis_service import (
    analyze_food_image,
    calculate_waste_cost,
    analyze_spoilage_risk,
)

logger = logging.getLogger(__name__)


def _section(title: str, subtitle: Optional[str] = None):
    st.markdown(
        f"""<div style="margin:22px 0 10px 0;">
            <div class="section-title" style="margin-bottom:2px;">{title}</div>
            {f'<div style="color:#6b7a8d;font-size:0.83rem;margin-top:2px;">{subtitle}</div>' if subtitle else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def render_food_waste_page():
    st.markdown(
        """<div style="margin-bottom:20px;">
            <h1 style="margin:0 0 6px 0;">♻️ Food Waste Intelligence & Spoilage Prevention</h1>
            <p style="color:#6b7a8d;font-size:0.92rem;margin:0;">
                Quantify kitchen waste, verify image detections, and identify low-velocity dishes at risk of spoilage.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    run_id = st.session_state.get("active_run_id")
    if not run_id:
        st.info("ℹ️ Select or create a restaurant on the Overview or Data Upload page first to record waste data.")
        return

    sales_df = st.session_state.get("sales_df")
    menu_df = st.session_state.get("menu_df")
    costs_df = st.session_state.get("costs_df")

    # ── Calculate both Measured Waste and Predictive Spoilage Risk ─────────
    records = repo.list_waste_records(run_id)
    measured_summary = calculate_waste_cost(records) if records else {
        "total_waste_cost": 0.0,
        "calculable_records": 0,
        "uncalculable_records": 0,
        "by_ingredient": {},
        "limitations": [],
    }

    spoilage_summary = analyze_spoilage_risk(sales_df, menu_df, costs_df)

    # ── Executive KPI Summary Banner ──────────────────────────────────────
    col_measured, col_predictive = st.columns(2)

    with col_measured:
        st.markdown(
            f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid #059669;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.02);margin-bottom:18px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.06em;color:#059669;font-weight:700;">
                        🟢 Measured Kitchen Waste
                    </span>
                    <span style="font-size:0.75rem;background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:10px;font-weight:600;">
                        Physical Logs
                    </span>
                </div>
                <div style="display:flex;align-items:baseline;gap:12px;">
                    <span style="font-size:1.6rem;font-weight:800;color:#0f172a;">₹{measured_summary['total_waste_cost']:,.2f}</span>
                    <span style="font-size:0.82rem;color:#64748b;">across {len(records)} logged incident(s)</span>
                </div>
                <div style="font-size:0.8rem;color:#475569;margin-top:4px;">
                    Verified by kitchen staff based on actual weighed/counted discards.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    with col_predictive:
        high_risk_count = spoilage_summary.get("high_risk_count", 0)
        weekly_risk = spoilage_summary.get("total_weekly_exposure", 0.0)
        slow_count = len(spoilage_summary.get("slow_moving_items", []))
        st.markdown(
            f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid #f59e0b;border-radius:12px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.02);margin-bottom:18px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.06em;color:#d97706;font-weight:700;">
                        ⚠️ Predictive Spoilage Risk
                    </span>
                    <span style="font-size:0.75rem;background:#fef3c7;color:#b45309;padding:2px 8px;border-radius:10px;font-weight:600;">
                        Sales Velocity Model
                    </span>
                </div>
                <div style="display:flex;align-items:baseline;gap:12px;">
                    <span style="font-size:1.6rem;font-weight:800;color:#0f172a;">₹{weekly_risk:,.2f}</span>
                    <span style="font-size:0.82rem;color:#64748b;">7-day capital exposure ({slow_count} slow dishes)</span>
                </div>
                <div style="font-size:0.8rem;color:#475569;margin-top:4px;">
                    Estimated potential discard risk driven by low sales velocity and recipe costs.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Tabs Navigation ───────────────────────────────────────────────────
    tab_capture, tab_log, tab_analytics, tab_spoilage = st.tabs([
        "📷  Kitchen Image Capture",
        "📝  Log Measured Waste",
        "📊  Measured Waste Analytics",
        "⚠️  Predictive Spoilage Risk",
    ])

    # ────────────────────────── Tab 1: Image Capture ──────────────────────
    with tab_capture:
        _section("📷 Kitchen Waste Visual Recognition", "Upload food waste photos for automated ingredient candidate detection.")
        st.caption("Gemini Vision identifies visible food items to assist logging. Staff must verify quantities — AI does not infer weight or food safety.")

        image = st.file_uploader(
            "Upload food waste image (JPEG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            key="waste_image_uploader",
        )
        if image:
            img_c, btn_c = st.columns([2, 1])
            with img_c:
                st.image(image, caption=f"Selected: {image.name}", use_container_width=True)
            with btn_c:
                st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
                if st.button("🔍  Analyze Image with AI", type="primary", use_container_width=True):
                    try:
                        with st.spinner("Analyzing visible items using Gemini Vision…"):
                            result = analyze_food_image(image.getvalue(), image.type or "image/jpeg")
                        st.session_state["waste_image_result"] = result
                        st.session_state["waste_image_name"] = image.name
                        repo.save_waste_image(
                            run_id, image.name, image.type or "image/jpeg",
                            result.get("items", []), result.get("image_limitations", [])
                        )
                        st.success("✅ Image analyzed! Detected items saved. Switch to the 'Log Measured Waste' tab to record weights.")
                    except Exception as exc:
                        st.error(f"Image analysis error: {exc}")
                        st.info("You can still record waste manually in the 'Log Measured Waste' tab.")

        res = st.session_state.get("waste_image_result")
        if res:
            items = res.get("items", [])
            _section("Detected Candidate Items")
            if items:
                items_df = pd.DataFrame(items)
                st.dataframe(items_df, use_container_width=True, hide_index=True)
                st.caption("⚠️ Visual suggestions only. Enter verified quantities and costs in the Log Waste tab.")
            else:
                st.info("No distinct food items were identified with sufficient confidence in this image.")
            for lim in res.get("image_limitations", []):
                st.caption(f"ℹ️ {lim}")

    # ────────────────────────── Tab 2: Log Waste ──────────────────────────
    with tab_log:
        _section("📝 Record Verified Kitchen Waste", "Log physical kitchen waste with verified quantity and unit costs.")
        res = st.session_state.get("waste_image_result")
        detected_names = [i.get("name", "") for i in (res or {}).get("items", []) if i.get("name")]

        with st.form("verified_waste_form", clear_on_submit=True):
            f1, f2 = st.columns(2)
            with f1:
                default_name = detected_names[0] if detected_names else ""
                ingredient = st.text_input(
                    "Ingredient / Food Item *",
                    value=default_name,
                    placeholder="e.g. Cooked rice, Pizza dough, Tomatoes, Bread slices",
                    help="Name of the discarded ingredient or dish.",
                )
            with f2:
                associated_dish = st.text_input(
                    "Associated Menu Dish (Optional)",
                    placeholder="e.g. Margherita Pizza, Fried Rice, Caesar Salad",
                    help="Connect this ingredient waste to a specific menu recipe.",
                )

            c1, c2, c3 = st.columns(3)
            with c1:
                quantity = c1.number_input("Quantity Discarded *", min_value=0.0, step=0.1, help="Actual measured quantity discarded.")
            with c2:
                unit = c2.selectbox("Unit of Measurement *", ["kg", "g", "litre", "ml", "pieces", "portions"])
            with c3:
                unit_cost = c3.number_input("Cost per Unit (₹) *", min_value=0.0, step=1.0, help="Unit cost in ₹ to compute actual loss.")

            c4, c5 = st.columns(2)
            with c4:
                reason = c4.selectbox(
                    "Primary Reason for Waste *",
                    ["Over-preparation", "Spoilage / Expired", "Plate Leftovers", "Preparation Waste / Trimming", "Accidental Spillage", "Other"],
                )
            with c5:
                use_detection = st.checkbox(
                    "Link record to recent image detection",
                    value=bool(detected_names),
                    help="Attaches image metadata to this verified record.",
                )

            submitted = st.form_submit_button("💾  Save Verified Waste Record", type="primary", use_container_width=True)
            if submitted:
                if not ingredient.strip():
                    st.error("Please enter an ingredient or food item name.")
                elif quantity <= 0:
                    st.error("Quantity must be greater than zero.")
                elif unit_cost <= 0:
                    st.warning("Unit cost is 0. Cost calculation will record ₹0.00 loss.")
                else:
                    matched = next(
                        (x for x in (res or {}).get("items", []) if x.get("name", "").lower() == ingredient.strip().lower()),
                        None,
                    ) if use_detection else None

                    repo.save_waste_record(run_id, {
                        "ingredient_name": ingredient.strip(),
                        "quantity": quantity,
                        "unit": unit,
                        "unit_cost": unit_cost,
                        "waste_reason": reason,
                        "associated_dish": associated_dish.strip(),
                        "image_item_name": matched.get("name") if matched else None,
                        "image_confidence": matched.get("confidence") if matched else None,
                        "verified_by_user": True,
                    })
                    st.success(f"✅ Verified waste record saved: {quantity} {unit} of {ingredient.strip()} (₹{quantity * unit_cost:,.2f})")
                    st.rerun()

    # ────────────────────────── Tab 3: Measured Waste Analytics ───────────
    with tab_analytics:
        _section("📊 Measured Kitchen Waste Analytics", "Visual breakdown of recorded physical waste logs.")

        if not records:
            st.markdown(
                """<div style="background:#ffffff;border-radius:12px;padding:40px 20px;text-align:center;border:1px dashed #cbd5e1;">
                    <div style="font-size:2em;margin-bottom:8px;">📝</div>
                    <div style="font-weight:600;color:#0d1b2a;margin-bottom:4px;">No Kitchen Waste Recorded Yet</div>
                    <div style="color:#64748b;font-size:0.85rem;">Use the 'Log Measured Waste' tab to record kitchen discards.</div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            w_df = pd.DataFrame(records)

            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                _section("💸 Waste Cost by Ingredient")
                if measured_summary["by_ingredient"]:
                    ing_df = pd.DataFrame(
                        list(measured_summary["by_ingredient"].items()),
                        columns=["Ingredient", "Cost (₹)"],
                    ).sort_values("Cost (₹)", ascending=False)

                    fig_ing = go.Figure(go.Bar(
                        x=ing_df["Cost (₹)"],
                        y=ing_df["Ingredient"],
                        orientation="h",
                        marker_color="#ef4444",
                        text=[f"₹{v:,.2f}" for v in ing_df["Cost (₹)"]],
                        textposition="outside",
                        hovertemplate="<b>%{y}</b>: ₹%{x:,.2f}<extra></extra>",
                    ))
                    fig_ing.update_layout(
                        plot_bgcolor="#ffffff",
                        paper_bgcolor="#ffffff",
                        height=280,
                        margin=dict(t=10, b=20, l=10, r=80),
                        yaxis=dict(autorange="reversed", gridcolor="#f1f5f9"),
                        xaxis=dict(gridcolor="#f1f5f9", tickprefix="₹", tickformat=",.0f"),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_ing, use_container_width=True)
                else:
                    st.caption("No cost data available for recorded ingredients.")

            with c_chart2:
                _section("📋 Waste Breakdown by Reason")
                if "waste_reason" in w_df.columns:
                    reasons = w_df["waste_reason"].value_counts().reset_index()
                    reasons.columns = ["Reason", "Count"]
                    fig_reason = go.Figure(go.Pie(
                        labels=reasons["Reason"],
                        values=reasons["Count"],
                        hole=0.58,
                        marker=dict(colors=["#ef4444", "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6"]),
                        textinfo="percent+label",
                        hovertemplate="<b>%{label}</b>: %{value} logs (%{percent})<extra></extra>",
                    ))
                    fig_reason.update_layout(
                        paper_bgcolor="#ffffff",
                        height=280,
                        margin=dict(t=10, b=10, l=10, r=10),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_reason, use_container_width=True)

            # Records Table
            _section("📋 Verified Waste Records Log")
            t_col1, t_col2 = st.columns([3, 1])
            with t_col2:
                csv_waste = w_df.to_csv(index=False)
                st.download_button(
                    "📥 Export Waste Logs (CSV)",
                    data=csv_waste,
                    file_name="menumind_waste_records.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            show_cols = [c for c in ("ingredient_name", "quantity", "unit", "unit_cost", "waste_reason", "associated_dish", "created_at") if c in w_df.columns]
            table_display = w_df[show_cols].copy()
            if "unit_cost" in table_display.columns and "quantity" in table_display.columns:
                table_display["Total Loss (₹)"] = (
                    pd.to_numeric(table_display["quantity"], errors="coerce") *
                    pd.to_numeric(table_display["unit_cost"], errors="coerce")
                ).apply(lambda v: f"₹{v:,.2f}" if pd.notna(v) else "—")
                table_display["unit_cost"] = table_display["unit_cost"].apply(lambda v: f"₹{v:,.2f}" if pd.notna(v) else "—")

            st.dataframe(table_display, use_container_width=True, hide_index=True)

    # ────────────────────────── Tab 4: Predictive Spoilage Risk ───────────
    with tab_spoilage:
        _section("⚠️ Sales Velocity & Predictive Spoilage Exposure", "Identifies slow-moving dishes at risk of spoilage based on real sales velocity and recipe costs.")
        st.caption("Data Integrity Guarantee: Clearly distinguishes physical kitchen discards from predictive inventory exposure.")

        slow_items = spoilage_summary.get("slow_moving_items", [])
        if not slow_items:
            if sales_df is None or sales_df.empty:
                st.info("ℹ️ Upload sales data in the Data Upload module to calculate sales velocity and spoilage risks.")
            else:
                st.success("🎉 Great performance! No dishes were identified as high-risk slow-movers based on current sales velocity.")
        else:
            sr1, sr2, sr3 = st.columns(3)
            with sr1:
                st.metric("Slow-Moving Dishes", len(slow_items), help="Dishes in bottom demand velocity requiring inventory optimization.")
            with sr2:
                st.metric("Median Daily Velocity", f"{spoilage_summary.get('median_velocity', 0.0):.1f} units/day")
            with sr3:
                st.metric("7-Day Capital at Risk", f"₹{spoilage_summary.get('total_weekly_exposure', 0.0):,.2f}", help="Estimated cost of buffer ingredients that risk spoiling if sales remain stagnant.")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            col_table, col_chart = st.columns([3, 2])
            with col_table:
                st.markdown("##### 🚨 Dishes with Low Demand & Spoilage Risk")
                slow_df = pd.DataFrame(slow_items)
                display_slow = slow_df[[
                    "item_name", "units_sold", "daily_velocity", "weekly_exposure", "risk_level"
                ]].copy()
                display_slow.columns = ["Menu Dish", "Total Sold", "Daily Velocity", "Weekly Exposure (₹)", "Risk Level"]
                display_slow["Weekly Exposure (₹)"] = display_slow["Weekly Exposure (₹)"].apply(lambda v: f"₹{v:,.2f}")
                st.dataframe(display_slow, use_container_width=True, hide_index=True)

            with col_chart:
                st.markdown("##### 💸 Weekly Exposure by Dish")
                fig_exp = go.Figure(go.Bar(
                    x=[i["weekly_exposure"] for i in slow_items[:8]],
                    y=[i["item_name"] for i in slow_items[:8]],
                    orientation="h",
                    marker_color="#f59e0b",
                    text=[f"₹{i['weekly_exposure']:,.0f}" for i in slow_items[:8]],
                    textposition="outside",
                    hovertemplate="<b>%{y}</b>: ₹%{x:,.2f}<extra></extra>",
                ))
                fig_exp.update_layout(
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="#ffffff",
                    height=280,
                    margin=dict(t=10, b=20, l=10, r=60),
                    yaxis=dict(autorange="reversed", gridcolor="#f1f5f9"),
                    xaxis=dict(gridcolor="#f1f5f9", tickprefix="₹", tickformat=",.0f"),
                    showlegend=False,
                )
                st.plotly_chart(fig_exp, use_container_width=True)

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # Actionable Practical Interventions
            _section("💡 Actionable Kitchen Waste Reduction Strategies")
            act_cols = st.columns(2)
            for idx, action in enumerate(spoilage_summary.get("action_items", [])):
                col = act_cols[idx % 2]
                title_part, desc_part = action.split(":", 1) if ":" in action else (action, "")
                col.markdown(
                    f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid #3b82f6;border-radius:10px;padding:12px 16px;margin-bottom:10px;">
                        <div style="font-weight:700;color:#0f172a;font-size:0.92rem;">{title_part}</div>
                        <div style="color:#64748b;font-size:0.83rem;margin-top:4px;">{desc_part.strip()}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            for lim in spoilage_summary.get("limitations", []):
                st.caption(f"ℹ️ {lim}")
