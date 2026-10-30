"""
Dashboard — premium onboarding + restaurant overview.
Integrates: restaurant creation, CSV upload, Run Analysis button.
"""
from __future__ import annotations

import io
import logging
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from database import repository as repo
from services.ingestion_service import ingest_menu, ingest_sales, ingest_reviews, ingest_costs
from services.preprocessing_service import clean_menu, clean_sales, clean_reviews, clean_costs
from services.review_retrieval_service import autocomplete_restaurant_name

logger = logging.getLogger(__name__)

# ── CSV Templates ──────────────────────────────────────────────────────────────
_MENU_TPL = "restaurant_id,item_id,item_name,category,description,price\nREST001,ITEM001,Margherita Pizza,Pizza,Classic tomato and mozzarella pizza,12.99\nREST001,ITEM002,Caesar Salad,Salad,Romaine lettuce with Caesar dressing,9.99\n"
_SALES_TPL = "restaurant_id,item_id,date,quantity_sold,revenue,discount,transaction_id\nREST001,ITEM001,2024-01-15,3,38.97,0,TXN001\nREST001,ITEM002,2024-01-15,1,9.99,0,TXN002\n"
_REVIEWS_TPL = "restaurant_id,review_id,item_name,rating,review_text,review_date,source,source_url\nREST001,REV001,Margherita Pizza,4,Great crispy crust!,2024-01-20,Platform,https://example.com\n"
_COSTS_TPL = "restaurant_id,item_id,ingredient_cost,packaging_cost\nREST001,ITEM001,4.50,0.50\nREST001,ITEM002,2.20,0.30\n"


def _page_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""<div style="margin-bottom:24px;">
            <h1 style="margin:0 0 4px 0;">{title}</h1>
            {"<p style='color:#6b7a8d;font-size:0.92rem;margin:0;'>" + subtitle + "</p>" if subtitle else ""}
        </div>""",
        unsafe_allow_html=True,
    )


def _card(content_html: str, padding: str = "20px 24px"):
    st.markdown(
        f"""<div style="background:#ffffff;border-radius:14px;padding:{padding};
            border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.05);margin-bottom:16px;">
            {content_html}</div>""",
        unsafe_allow_html=True,
    )


def _quality_badge(score: float) -> str:
    if score >= 0.85:
        return "🟢"
    if score >= 0.60:
        return "🟡"
    return "🔴"


def render_dashboard():
    run_id = st.session_state.get("active_run_id")

    if not run_id:
        _render_onboarding()
    else:
        _render_active_overview(run_id)


# ──────────────────────────── Onboarding ──────────────────────────────────────

def _render_onboarding():
    _page_header("🍽️ Welcome to MenuMind AI", "Set up your restaurant to start AI-powered menu analysis.")

    tab_new, tab_existing = st.tabs(["✨  New Restaurant", "📂  Load Existing"])

    with tab_new:
        _render_new_restaurant_form()

    with tab_existing:
        _render_existing_restaurant_selector()


def _render_new_restaurant_form():
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Restaurant Details ─────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>🏪 Restaurant Details</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    name = col1.text_input(
        "Restaurant Name *",
        key="dash_rest_name",
        placeholder="e.g. Haldiram's, Barbeque Nation",
        help="Type at least 2 characters to see autocomplete suggestions.",
    )
    city = col2.text_input("City *", key="dash_rest_city", placeholder="e.g. Mumbai, Delhi")

    if name and len(name.strip()) >= 2:
        suggestions = autocomplete_restaurant_name(name.strip(), city=city.strip(), limit=5)
        if suggestions:
            st.markdown(
                "<span style='font-size:0.8rem;color:#6b7a8d;font-weight:600;'>SUGGESTIONS: </span>",
                unsafe_allow_html=True,
            )
            scols = st.columns(min(len(suggestions), 5))
            for i, sug in enumerate(suggestions[:5]):
                if scols[i].button(sug, key=f"dash_sug_{i}", help="Click to use this suggestion"):
                    st.session_state["dash_rest_name"] = sug
                    st.rerun()

    col3, col4 = st.columns(2)
    location = col3.text_input("Location / Address", placeholder="e.g. Connaught Place, New Delhi")
    category = col4.text_input("Cuisine / Category", placeholder="e.g. North Indian, Fast Food")

    col5, col6, col7 = st.columns([2, 1, 1])
    website = col5.text_input("Website URL (optional)", placeholder="https://example.com")
    period_start = col6.date_input("Analysis Start", value=date(2024, 1, 1))
    period_end = col7.date_input("Analysis End", value=date.today())

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── CSV Upload Section ─────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title'>📁 Upload Data Files</div>",
        unsafe_allow_html=True,
    )

    # Template downloads
    with st.expander("📥 Download CSV Templates", expanded=False):
        tc = st.columns(4)
        tc[0].download_button("menu.csv", _MENU_TPL, "menu_template.csv", mime="text/csv")
        tc[1].download_button("sales.csv", _SALES_TPL, "sales_template.csv", mime="text/csv")
        tc[2].download_button("reviews.csv", _REVIEWS_TPL, "reviews_template.csv", mime="text/csv")
        tc[3].download_button("costs.csv", _COSTS_TPL, "costs_template.csv", mime="text/csv")
        st.caption("Template rows are examples only.")

    uc1, uc2 = st.columns(2)
    with uc1:
        st.markdown("**📋 Menu Data** <span style='color:#e74c3c;font-size:0.8em'>Required</span>", unsafe_allow_html=True)
        menu_file = st.file_uploader("", type=["csv", "xlsx", "xls"], key="onboard_menu", label_visibility="collapsed")
        if menu_file:
            st.caption(f"✅ {menu_file.name}")

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown("**💰 Cost Data** <span style='color:#6b7a8d;font-size:0.8em'>Optional</span>", unsafe_allow_html=True)
        costs_file = st.file_uploader("", type=["csv", "xlsx", "xls"], key="onboard_costs", label_visibility="collapsed")
        if costs_file:
            st.caption(f"✅ {costs_file.name}")

    with uc2:
        st.markdown("**📈 Sales Data** <span style='color:#e74c3c;font-size:0.8em'>Required</span>", unsafe_allow_html=True)
        sales_file = st.file_uploader("", type=["csv", "xlsx", "xls"], key="onboard_sales", label_visibility="collapsed")
        if sales_file:
            st.caption(f"✅ {sales_file.name}")

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.markdown("**⭐ Customer Reviews** <span style='color:#6b7a8d;font-size:0.8em'>Optional</span>", unsafe_allow_html=True)
        reviews_file = st.file_uploader("", type=["csv", "xlsx", "xls"], key="onboard_reviews", label_visibility="collapsed")
        if reviews_file:
            st.caption(f"✅ {reviews_file.name}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Run Analysis Button ────────────────────────────────────────────────
    run_col, _ = st.columns([1, 3])
    with run_col:
        run_clicked = st.button(
            "🚀  Run Analysis",
            type="primary",
            use_container_width=True,
        )

    if run_clicked:
        _handle_run_analysis(
            name, city, location, website, category,
            period_start, period_end,
            menu_file, sales_file, reviews_file, costs_file,
        )


def _handle_run_analysis(
    name, city, location, website, category,
    period_start, period_end,
    menu_file, sales_file, reviews_file, costs_file,
):
    # ── Validate ──────────────────────────────────────────────────────────
    errors = []
    if not name.strip():
        errors.append("Restaurant name is required.")
    if not city.strip():
        errors.append("City is required.")
    if not menu_file:
        errors.append("Menu Data (CSV/XLSX) is required.")
    if not sales_file:
        errors.append("Sales Data (CSV/XLSX) is required.")
    if errors:
        for e in errors:
            st.error(e)
        return

    progress = st.progress(0, text="Setting up restaurant profile…")

    # ── Create or reuse restaurant without duplicates ─────────────────────
    rest_id, _ = repo.get_or_create_restaurant(
        name=name.strip(),
        city=city.strip(),
        location=location.strip(),
        website=website.strip(),
        category=category.strip(),
    )

    run_id = repo.create_analysis_run(rest_id, str(period_start), str(period_end), "")
    st.session_state["active_run_id"] = run_id
    st.session_state["active_restaurant_id"] = rest_id
    st.session_state["restaurant_info"] = {
        "id": rest_id,
        "name": name.strip(), "city": city.strip(), "location": location,
        "website": website, "category": category,
    }
    progress.progress(15, text="Processing Menu data…")

    quality_reports = []

    # ── Menu ─────────────────────────────────────────────────────────────
    df, _, warnings = ingest_menu(menu_file.read(), menu_file.name)
    for w in warnings:
        st.warning(f"Menu: {w}")
    df_clean, report = clean_menu(df)
    st.session_state["menu_df"] = df_clean
    quality_reports.append(report)
    progress.progress(35, text="Processing Sales data…")

    # ── Sales ─────────────────────────────────────────────────────────────
    df, _, warnings = ingest_sales(sales_file.read(), sales_file.name)
    for w in warnings:
        st.warning(f"Sales: {w}")
    menu_df = st.session_state.get("menu_df")
    df_clean, report, _ = clean_sales(df, menu_df)
    st.session_state["sales_df"] = df_clean
    quality_reports.append(report)
    progress.progress(55, text="Processing optional files…")

    # ── Reviews (optional) ────────────────────────────────────────────────
    if reviews_file:
        df, _, warnings = ingest_reviews(reviews_file.read(), reviews_file.name)
        for w in warnings:
            st.warning(f"Reviews: {w}")
        df_clean, report = clean_reviews(df)
        st.session_state["reviews_df"] = df_clean
        quality_reports.append(report)

    # ── Costs (optional) ──────────────────────────────────────────────────
    if costs_file:
        df, _, warnings = ingest_costs(costs_file.read(), costs_file.name)
        for w in warnings:
            st.warning(f"Costs: {w}")
        df_clean, report = clean_costs(df)
        st.session_state["costs_df"] = df_clean
        quality_reports.append(report)

    st.session_state["quality_reports"] = quality_reports
    if quality_reports:
        avg_q = sum(r.quality_score for r in quality_reports) / len(quality_reports)
        st.session_state["data_quality_score"] = avg_q

    progress.progress(75, text="Running AI analysis pipeline…")

    # ── Run the agent pipeline ────────────────────────────────────────────
    from agent.orchestrator import run_analysis as _run_analysis
    steps: list[str] = []

    def _on_progress(msg: str):
        steps.append(msg)
        progress.progress(
            min(75 + int(len(steps) * 2.5), 97),
            text=msg[:80],
        )

    waste_records = repo.list_waste_records(run_id)
    waste_df = pd.DataFrame(waste_records) if waste_records else None

    restaurant_name_for_agent = name.strip()
    if city.strip():
        restaurant_name_for_agent += f", {city.strip()}"

    state = _run_analysis(
        run_id=run_id,
        restaurant_name=restaurant_name_for_agent,
        menu_df=st.session_state.get("menu_df"),
        sales_df=st.session_state.get("sales_df"),
        reviews_df=st.session_state.get("reviews_df"),
        costs_df=st.session_state.get("costs_df"),
        waste_df=waste_df,
        progress_callback=_on_progress,
    )
    st.session_state["agent_state"] = state

    # Persist recommendations
    for rec in state.recommendations:
        repo.save_recommendation(run_id, rec.model_dump(mode="json"))

    quality = st.session_state.get("data_quality_score", 1.0)
    repo.update_run_status(run_id, "completed", quality)

    progress.progress(100, text="Analysis complete!")

    if state.error:
        st.warning(f"Analysis completed with a warning: {state.error}")
    else:
        st.success(
            f"✅ Analysis complete for **{name.strip()}** — "
            f"{len(state.recommendations)} recommendations generated."
        )

    # Navigate to Sales Analytics
    st.session_state["_nav_to"] = "📈  Sales Analytics"
    st.rerun()


def _render_existing_restaurant_selector():
    restaurants = repo.list_restaurants()
    if not restaurants:
        st.info("No restaurants created yet. Use the 'New Restaurant' tab to get started.", icon="👆")
        return

    rest_map = {f"{r['name']} ({r.get('city') or 'No City'})": r for r in restaurants}
    selected_label = st.selectbox("Select Restaurant:", list(rest_map.keys()))
    rest_data = rest_map[selected_label]
    rest_id = rest_data["id"]

    # Display restaurant summary card
    st.markdown(
        f"""<div style="background:#ffffff;border-radius:12px;padding:16px 20px;
            border:1px solid #e8edf4;margin:12px 0 16px 0;">
            <div style="font-weight:700;font-size:1.05rem;color:#0d1b2a;">{rest_data['name']}</div>
            <div style="font-size:0.86rem;color:#6b7a8d;margin-top:4px;">
                Cuisine: <strong>{rest_data.get('category') or 'Not specified'}</strong> · 
                City: <strong>{rest_data.get('city') or 'Not specified'}</strong> · 
                Location: <strong>{rest_data.get('location') or 'Not specified'}</strong>
            </div>
            {"<div style='font-size:0.82rem;color:#38bda3;margin-top:4px;'>" + rest_data.get('website', '') + "</div>" if rest_data.get('website') else ""}
        </div>""",
        unsafe_allow_html=True,
    )

    runs = repo.list_runs_for_restaurant(rest_id)
    if not runs:
        st.info("No analysis runs recorded yet for this restaurant.")
        if st.button("📁 Upload Datasets & Run First Analysis", type="primary"):
            st.session_state["active_restaurant_id"] = rest_id
            st.session_state["restaurant_info"] = dict(rest_data)
            st.session_state["_nav_to"] = "📁  Data Upload"
            st.rerun()
        return

    run_options = {
        f"Run #{r['id']} · {r['status'].capitalize()} · Quality: {int((r.get('data_quality_score') or 1.0) * 100)}% · {r['created_at'][:16]}": r["id"]
        for r in runs
    }
    selected_run = st.selectbox("Select Analysis Run:", list(run_options.keys()))

    c_load, c_new = st.columns([1, 1])
    with c_load:
        if st.button("▶️  Load Selected Run", type="primary", use_container_width=True):
            run_id = run_options[selected_run]
            st.session_state["active_run_id"] = run_id
            st.session_state["active_restaurant_id"] = rest_id
            st.session_state["restaurant_info"] = dict(rest_data)
            st.success(f"Loaded run #{run_id} for **{rest_data['name']}**.")
            st.rerun()

    with c_new:
        if st.button("📁  Upload New Data & Re-Analyze", use_container_width=True):
            st.session_state["active_restaurant_id"] = rest_id
            st.session_state["restaurant_info"] = dict(rest_data)
            st.session_state["_nav_to"] = "📁  Data Upload"
            st.rerun()


# ──────────────────────────── Active Overview ─────────────────────────────────

def _render_active_overview(run_id: int):
    restaurant_info = st.session_state.get("restaurant_info", {})
    rest_name = restaurant_info.get("name", "Unknown Restaurant")
    rest_city = restaurant_info.get("city", "")
    rest_cat = restaurant_info.get("category", "")
    rest_loc = restaurant_info.get("location", "")

    # ── Restaurant hero card ───────────────────────────────────────────────
    meta_parts = [p for p in [rest_cat, rest_city, rest_loc] if p]
    meta_str = " · ".join(meta_parts)
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#0f3460,#0a4a7c);
            border-radius:16px;padding:24px 28px;margin-bottom:24px;
            box-shadow:0 4px 20px rgba(15,52,96,0.25);">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="font-size:2.5em;">🍽️</div>
                <div>
                    <div style="font-size:1.35rem;font-weight:800;color:#ffffff;">{rest_name}</div>
                    <div style="font-size:0.88rem;color:#7ab4e0;margin-top:3px;">{meta_str}</div>
                </div>
                <div style="margin-left:auto;text-align:right;">
                    <div style="background:#ffffff18;border-radius:8px;padding:6px 14px;
                         font-size:0.82rem;color:#c8d6e5;">Analysis Run #{run_id}</div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── KPI Cards ─────────────────────────────────────────────────────────
    menu_df = st.session_state.get("menu_df")
    sales_df = st.session_state.get("sales_df")
    reviews_df = st.session_state.get("reviews_df")
    agent_state = st.session_state.get("agent_state")
    quality = st.session_state.get("data_quality_score")

    # Compute revenue
    total_rev = 0.0
    total_units = 0
    best_item = "—"
    if sales_df is not None:
        if "revenue" in sales_df.columns:
            total_rev = float(pd.to_numeric(sales_df["revenue"], errors="coerce").fillna(0).sum())
        elif "quantity_sold" in sales_df.columns and menu_df is not None and "price" in menu_df.columns:
            # Impute revenue from menu prices
            merged = sales_df.copy()
            price_map = dict(zip(menu_df["item_name"], menu_df["price"])) if "item_name" in menu_df.columns else {}
            name_col = "_matched_menu_name" if "_matched_menu_name" in merged.columns else (
                "item_name" if "item_name" in merged.columns else None
            )
            if name_col:
                merged["_price"] = merged[name_col].map(price_map)
                merged["_rev"] = pd.to_numeric(merged["quantity_sold"], errors="coerce") * pd.to_numeric(merged["_price"], errors="coerce")
                total_rev = float(merged["_rev"].fillna(0).sum())
        if "quantity_sold" in sales_df.columns:
            total_units = int(pd.to_numeric(sales_df["quantity_sold"], errors="coerce").fillna(0).sum())

        # Best-selling item
        name_col = "_matched_menu_name" if "_matched_menu_name" in sales_df.columns else (
            "item_name" if "item_name" in sales_df.columns else None
        )
        if name_col and "quantity_sold" in sales_df.columns:
            item_qty = sales_df.groupby(name_col)["quantity_sold"].sum()
            if not item_qty.empty:
                best_item = str(item_qty.idxmax())

    recs = agent_state.recommendations if agent_state else repo.list_recommendations(run_id)
    menu_items = len(menu_df) if menu_df is not None else 0
    review_count = len(reviews_df) if reviews_df is not None else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue", f"₹{total_rev:,.0f}" if total_rev else "—")
    k2.metric("Units Sold", f"{total_units:,}" if total_units else "—")
    k3.metric("Menu Items", menu_items or "—")
    k4.metric("Reviews", review_count or "—")
    k5.metric("Recommendations", len(recs))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Data status row ────────────────────────────────────────────────────
    data_status = {
        "📋 Menu": st.session_state.get("menu_df") is not None,
        "📈 Sales": st.session_state.get("sales_df") is not None,
        "⭐ Reviews": st.session_state.get("reviews_df") is not None,
        "💰 Costs": st.session_state.get("costs_df") is not None,
    }
    status_html = "".join(
        f"""<div style="display:inline-flex;align-items:center;gap:6px;
            background:{"#e8f7f4" if loaded else "#f5f6f8"};
            border-radius:20px;padding:5px 14px;margin:0 6px 6px 0;font-size:0.82rem;font-weight:600;
            color:{"#1a7a65" if loaded else "#8896a8"};">
            {"✅" if loaded else "○"} {label}
        </div>"""
        for label, loaded in data_status.items()
    )
    st.markdown(
        f"""<div style="background:#ffffff;border-radius:12px;padding:14px 18px;
            border:1px solid #e8edf4;margin-bottom:20px;">
            <div style="font-size:0.76rem;font-weight:600;color:#8896a8;text-transform:uppercase;
                letter-spacing:0.07em;margin-bottom:10px;">Data Status</div>
            {status_html}
        </div>""",
        unsafe_allow_html=True,
    )

    # ── High-priority findings ─────────────────────────────────────────────
    if agent_state and agent_state.recommendations:
        high_prio = [r for r in agent_state.recommendations if r.priority.value == "high"]
        if high_prio:
            st.markdown("<div class='section-title'>🔴 High Priority Findings</div>", unsafe_allow_html=True)
            for rec in high_prio[:3]:
                action_colors = {
                    "IMPROVE": "#fff3cd", "REMOVE": "#fde8e8",
                    "PROMOTE": "#e8f7f4", "REPRICE": "#e8f0ff",
                    "INSUFFICIENT_EVIDENCE": "#f5f6f8",
                }
                bg = action_colors.get(rec.action.value, "#f5f6f8")
                st.markdown(
                    f"""<div style="background:{bg};border-radius:12px;padding:14px 18px;
                        border-left:4px solid #e74c3c;margin-bottom:10px;font-size:0.9rem;">
                        <strong>{rec.item_name}</strong>
                        <span style="background:#00000010;border-radius:4px;padding:1px 8px;
                            font-size:0.78rem;margin:0 8px;">{rec.action.value}</span>
                        <span style="color:#8896a8;font-size:0.82rem;">{rec.confidence_score:.0%} confidence</span>
                        <div style="color:#455060;font-size:0.85rem;margin-top:6px;">{rec.reasoning[:140]}…</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── Agent log ──────────────────────────────────────────────────────────
    if agent_state and agent_state.log:
        with st.expander("📜 Analysis Log"):
            log_text = "\n".join(agent_state.log)
            st.code(log_text, language=None)

    # ── Switch restaurant ──────────────────────────────────────────────────
    st.divider()
    with st.expander("🔄 Switch Restaurant / Load Another Run"):
        _render_existing_restaurant_selector()
        if st.button("➕  Set Up New Restaurant", key="new_from_overview"):
            for key in ["active_run_id", "active_restaurant_id", "restaurant_info",
                        "menu_df", "sales_df", "reviews_df", "costs_df",
                        "agent_state", "quality_reports", "data_quality_score",
                        "sales_summary", "waste_image_result"]:
                st.session_state.pop(key, None)
            st.rerun()
