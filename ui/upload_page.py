"""
Data Upload module — Multi-dataset ingestion, schema & foreign-key validation,
data quality preview, and Run Analysis execution engine.
"""
from __future__ import annotations

import io
import logging
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from database import repository as repo
from services.ingestion_service import (
    ingest_menu,
    ingest_sales,
    ingest_reviews,
    ingest_costs,
    validate_cross_dataset_integrity,
)
from services.preprocessing_service import (
    clean_menu,
    clean_sales,
    clean_reviews,
    clean_costs,
)
from services.review_retrieval_service import autocomplete_restaurant_name
from agent.schemas import DataQualityReport

logger = logging.getLogger(__name__)

# ── CSV Templates ─────────────────────────────────────────────────────────────
_MENU_TPL = (
    "restaurant_id,item_id,item_name,category,description,price\n"
    "REST001,ITEM001,Margherita Pizza,Pizza,Classic tomato and mozzarella pizza,12.99\n"
    "REST001,ITEM002,Caesar Salad,Salad,Romaine lettuce with Caesar dressing,9.99\n"
)
_SALES_TPL = (
    "restaurant_id,item_id,date,quantity_sold,revenue,discount,transaction_id\n"
    "REST001,ITEM001,2024-01-15,3,38.97,0,TXN001\n"
    "REST001,ITEM002,2024-01-15,1,9.99,0,TXN002\n"
)
_REVIEWS_TPL = (
    "restaurant_id,review_id,item_name,rating,review_text,review_date,source,source_url\n"
    "REST001,REV001,Margherita Pizza,4,Great crispy crust!,2024-01-20,Platform,https://example.com\n"
)
_COSTS_TPL = (
    "restaurant_id,item_id,ingredient_cost,packaging_cost\n"
    "REST001,ITEM001,4.50,0.50\n"
    "REST001,ITEM002,2.20,0.30\n"
)


def _quality_badge(score: float) -> str:
    if score >= 0.85:
        return "🟢 High Quality"
    if score >= 0.60:
        return "🟡 Moderate Quality"
    return "🔴 Quality Issues"


def render_upload_page():
    st.markdown(
        """<div style="margin-bottom:20px;">
            <h1 style="margin:0 0 6px 0;">📁 Data Upload & Validation</h1>
            <p style="color:#6b7a8d;font-size:0.92rem;margin:0;">
                Provide restaurant information and upload data files (CSV, XLSX, XLS) to power AI-driven menu intelligence.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Section 1: Restaurant Identification ──────────────────────────────────
    active_rest = st.session_state.get("restaurant_info", {})
    default_name = active_rest.get("name", "")
    default_city = active_rest.get("city", "")
    default_loc = active_rest.get("location", "")
    default_cat = active_rest.get("category", "")
    default_url = active_rest.get("website", "")

    st.markdown("<div class='section-title'>🏪 Restaurant Details</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    name_input = c1.text_input(
        "Restaurant Name *",
        value=default_name,
        key="upload_rest_name",
        placeholder="e.g. Haldiram's, Barbeque Nation",
        help="Type at least 2 characters to trigger autocomplete suggestions.",
    )
    city_input = c2.text_input(
        "City *",
        value=default_city,
        key="upload_rest_city",
        placeholder="e.g. Mumbai, New Delhi",
    )

    # Autocomplete Suggestions
    if name_input and len(name_input.strip()) >= 2:
        suggestions = autocomplete_restaurant_name(name_input.strip(), city=city_input.strip(), limit=5)
        if suggestions:
            st.markdown(
                "<span style='font-size:0.8rem;color:#6b7a8d;font-weight:600;'>SUGGESTIONS: </span>",
                unsafe_allow_html=True,
            )
            scols = st.columns(min(len(suggestions), 5))
            for i, sug in enumerate(suggestions[:5]):
                if scols[i].button(sug, key=f"sug_btn_{i}", help="Click to use this suggestion"):
                    st.session_state["upload_rest_name"] = sug
                    st.rerun()

    c3, c4 = st.columns(2)
    loc_input = c3.text_input(
        "Location / Address",
        value=default_loc,
        key="upload_rest_loc",
        placeholder="e.g. Connaught Place, South Extension",
    )
    cat_input = c4.text_input(
        "Cuisine / Category",
        value=default_cat,
        key="upload_rest_cat",
        placeholder="e.g. North Indian, Fast Food, Italian",
    )

    c5, c6, c7 = st.columns([2, 1, 1])
    web_input = c5.text_input(
        "Website URL (optional)",
        value=default_url,
        key="upload_rest_url",
        placeholder="https://example.com",
    )
    start_date = c6.date_input("Analysis Start", value=date(2024, 1, 1), key="upload_period_start")
    end_date = c7.date_input("Analysis End", value=date.today(), key="upload_period_end")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── Section 2: CSV / Excel Uploaders ──────────────────────────────────────
    st.markdown("<div class='section-title'>📂 Upload Datasets</div>", unsafe_allow_html=True)

    # Downloadable templates
    with st.expander("📥 Download Sample Templates (CSV)", expanded=False):
        tc = st.columns(4)
        tc[0].download_button("menu.csv", _MENU_TPL, "menu_template.csv", mime="text/csv")
        tc[1].download_button("sales.csv", _SALES_TPL, "sales_template.csv", mime="text/csv")
        tc[2].download_button("costs.csv", _COSTS_TPL, "costs_template.csv", mime="text/csv")
        tc[3].download_button("reviews.csv", _REVIEWS_TPL, "reviews_template.csv", mime="text/csv")
        st.caption("Templates show expected column headers and sample data types.")

    u_col1, u_col2 = st.columns(2)
    with u_col1:
        st.markdown("**1. Menu Dataset** <span style='color:#e74c3c;font-size:0.8rem;'>Required</span>", unsafe_allow_html=True)
        menu_up = st.file_uploader(
            "Upload Menu",
            type=["csv", "xlsx", "xls"],
            key="up_menu_file",
            label_visibility="collapsed",
        )
        if menu_up:
            _ingest_and_store_file("menu", menu_up)

        if st.session_state.get("menu_df") is not None:
            m_len = len(st.session_state["menu_df"])
            st.success(f"✅ Menu loaded: {m_len} items active in session.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("**3. Cost Dataset** <span style='color:#6b7a8d;font-size:0.8rem;'>Optional</span>", unsafe_allow_html=True)
        costs_up = st.file_uploader(
            "Upload Costs",
            type=["csv", "xlsx", "xls"],
            key="up_costs_file",
            label_visibility="collapsed",
        )
        if costs_up:
            _ingest_and_store_file("costs", costs_up)

        if st.session_state.get("costs_df") is not None:
            c_len = len(st.session_state["costs_df"])
            st.success(f"✅ Costs loaded: {c_len} items active in session.")

    with u_col2:
        st.markdown("**2. Sales Dataset** <span style='color:#e74c3c;font-size:0.8rem;'>Required</span>", unsafe_allow_html=True)
        sales_up = st.file_uploader(
            "Upload Sales",
            type=["csv", "xlsx", "xls"],
            key="up_sales_file",
            label_visibility="collapsed",
        )
        if sales_up:
            _ingest_and_store_file("sales", sales_up)

        if st.session_state.get("sales_df") is not None:
            s_len = len(st.session_state["sales_df"])
            st.success(f"✅ Sales loaded: {s_len} records active in session.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("**4. Customer Reviews** <span style='color:#6b7a8d;font-size:0.8rem;'>Optional</span>", unsafe_allow_html=True)
        reviews_up = st.file_uploader(
            "Upload Reviews",
            type=["csv", "xlsx", "xls"],
            key="up_reviews_file",
            label_visibility="collapsed",
        )
        if reviews_up:
            _ingest_and_store_file("reviews", reviews_up)

        if st.session_state.get("reviews_df") is not None:
            r_len = len(st.session_state["reviews_df"])
            st.success(f"✅ Reviews loaded: {r_len} reviews active in session.")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # ── Section 3: Cross-Dataset Validation Report ────────────────────────────
    menu_df = st.session_state.get("menu_df")
    sales_df = st.session_state.get("sales_df")
    costs_df = st.session_state.get("costs_df")
    reviews_df = st.session_state.get("reviews_df")

    is_valid = False
    if menu_df is not None and sales_df is not None:
        is_valid, val_errors, val_warnings = validate_cross_dataset_integrity(
            menu_df, sales_df, costs_df, reviews_df
        )

        st.markdown("<div class='section-title'>🔍 Dataset Integrity & Validation</div>", unsafe_allow_html=True)
        if val_errors:
            for err in val_errors:
                st.error(f"❌ {err}")
        else:
            st.success("✅ All required schema checks and foreign key validations passed successfully!")

        if val_warnings:
            with st.expander(f"⚠️ {len(val_warnings)} Non-Critical Notices / Fallbacks", expanded=False):
                for w in val_warnings:
                    st.info(w)

        # Show Data Previews
        _render_dataset_previews(menu_df, sales_df, costs_df, reviews_df)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Section 4: Primary Run Analysis CTA ───────────────────────────────────
    st.markdown("<div class='section-title'>🚀 Run Full AI Analysis</div>", unsafe_allow_html=True)

    btn_col, info_col = st.columns([1, 2])
    with btn_col:
        run_btn = st.button(
            "🚀  Run Analysis",
            type="primary",
            use_container_width=True,
            help="Executes deterministic analytics, sentiment processing, and AI recommendation pipeline.",
        )

    if run_btn:
        _execute_full_analysis(
            name=name_input,
            city=city_input,
            location=loc_input,
            website=web_input,
            category=cat_input,
            period_start=str(start_date),
            period_end=str(end_date),
            menu_df=menu_df,
            sales_df=sales_df,
            costs_df=costs_df,
            reviews_df=reviews_df,
        )


def _ingest_and_store_file(file_type: str, uploaded_file):
    """Parses, cleans and stores the uploaded file into session_state with deduplication."""
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    try:
        if file_type == "menu":
            df_raw, mapping, warnings = ingest_menu(file_bytes, filename)
            df_clean, report = clean_menu(df_raw)
            st.session_state["menu_df"] = df_clean
            st.session_state["menu_report"] = report
            st.session_state["menu_filename"] = filename

        elif file_type == "sales":
            df_raw, mapping, warnings = ingest_sales(file_bytes, filename)
            menu_df = st.session_state.get("menu_df")
            df_clean, report, _ = clean_sales(df_raw, menu_df)
            st.session_state["sales_df"] = df_clean
            st.session_state["sales_report"] = report
            st.session_state["sales_filename"] = filename

        elif file_type == "costs":
            df_raw, mapping, warnings = ingest_costs(file_bytes, filename)
            df_clean, report = clean_costs(df_raw)
            st.session_state["costs_df"] = df_clean
            st.session_state["costs_report"] = report
            st.session_state["costs_filename"] = filename

        elif file_type == "reviews":
            df_raw, mapping, warnings = ingest_reviews(file_bytes, filename)
            df_clean, report = clean_reviews(df_raw)
            st.session_state["reviews_df"] = df_clean
            st.session_state["reviews_report"] = report
            st.session_state["reviews_filename"] = filename

    except Exception as exc:
        logger.exception("Failed to parse file %s: %s", filename, exc)
        st.error(f"Error parsing {filename}: {exc}")


def _render_dataset_previews(menu_df, sales_df, costs_df, reviews_df):
    """Renders tabular previews with quality metrics."""
    with st.expander("📊 Preview Loaded Datasets", expanded=False):
        t_names = ["📋 Menu", "📈 Sales"]
        if costs_df is not None:
            t_names.append("💰 Costs")
        if reviews_df is not None:
            t_names.append("⭐ Reviews")

        tabs = st.tabs(t_names)
        tabs[0].dataframe(menu_df.head(20), use_container_width=True)
        tabs[1].dataframe(sales_df.head(20), use_container_width=True)
        curr_idx = 2
        if costs_df is not None:
            tabs[curr_idx].dataframe(costs_df.head(20), use_container_width=True)
            curr_idx += 1
        if reviews_df is not None:
            tabs[curr_idx].dataframe(reviews_df.head(20), use_container_width=True)


def _execute_full_analysis(
    name: str,
    city: str,
    location: str,
    website: str,
    category: str,
    period_start: str,
    period_end: str,
    menu_df: Optional[pd.DataFrame],
    sales_df: Optional[pd.DataFrame],
    costs_df: Optional[pd.DataFrame],
    reviews_df: Optional[pd.DataFrame],
):
    """Validates inputs, avoids restaurant duplicates, creates run, and executes orchestrator."""
    errors: list[str] = []
    clean_name = (name or "").strip()
    clean_city = (city or "").strip()

    if not clean_name:
        errors.append("Restaurant name is required.")
    if not clean_city:
        errors.append("City is required.")
    if menu_df is None or menu_df.empty:
        errors.append("Menu dataset is required before running analysis.")
    if sales_df is None or sales_df.empty:
        errors.append("Sales dataset is required before running analysis.")

    if errors:
        for err in errors:
            st.error(err)
        return

    # Check cross-dataset foreign keys
    is_valid, cross_errors, cross_warnings = validate_cross_dataset_integrity(
        menu_df, sales_df, costs_df, reviews_df
    )
    if not is_valid:
        for err in cross_errors:
            st.error(err)
        return

    progress_bar = st.progress(0, text="Initializing analysis run…")

    # 1. Reuse existing restaurant or create new without duplicating
    rest_id, _ = repo.get_or_create_restaurant(
        name=clean_name,
        city=clean_city,
        location=location.strip(),
        website=website.strip(),
        category=category.strip(),
    )

    run_id = repo.create_analysis_run(
        restaurant_id=rest_id,
        period_start=period_start,
        period_end=period_end,
        notes="",
    )

    # Update session state with active restaurant & run
    st.session_state["active_restaurant_id"] = rest_id
    st.session_state["active_run_id"] = run_id
    st.session_state["restaurant_info"] = {
        "id": rest_id,
        "name": clean_name,
        "city": clean_city,
        "location": location.strip(),
        "website": website.strip(),
        "category": category.strip(),
    }

    # Record data files in database
    if menu_df is not None:
        repo.record_data_file(
            run_id, "menu", st.session_state.get("menu_filename", "menu.csv"),
            len(menu_df), len(menu_df), 0
        )
    if sales_df is not None:
        repo.record_data_file(
            run_id, "sales", st.session_state.get("sales_filename", "sales.csv"),
            len(sales_df), len(sales_df), 0
        )
    if costs_df is not None:
        repo.record_data_file(
            run_id, "costs", st.session_state.get("costs_filename", "costs.csv"),
            len(costs_df), len(costs_df), 0
        )
    if reviews_df is not None:
        repo.record_data_file(
            run_id, "reviews", st.session_state.get("reviews_filename", "reviews.csv"),
            len(reviews_df), len(reviews_df), 0
        )

    progress_bar.progress(25, text="Processing data files and running deterministic analytics…")

    # Calculate overall data quality score
    reports = [
        st.session_state.get("menu_report"),
        st.session_state.get("sales_report"),
        st.session_state.get("costs_report"),
        st.session_state.get("reviews_report"),
    ]
    valid_reports = [r for r in reports if r is not None]
    if valid_reports:
        avg_q = sum(r.quality_score for r in valid_reports) / len(valid_reports)
    else:
        avg_q = 1.0
    st.session_state["data_quality_score"] = avg_q
    st.session_state["quality_reports"] = valid_reports

    progress_bar.progress(50, text="Executing AI orchestrator pipeline…")

    # Run orchestrator
    from agent.orchestrator import run_analysis as _run_orchestrator
    steps_log: list[str] = []

    def _progress_cb(msg: str):
        steps_log.append(msg)
        progress_bar.progress(
            min(50 + int(len(steps_log) * 4), 95),
            text=msg[:80],
        )

    waste_records = repo.list_waste_records(run_id)
    waste_df = pd.DataFrame(waste_records) if waste_records else None

    search_name = f"{clean_name}, {clean_city}" if clean_city else clean_name
    agent_state = _run_orchestrator(
        run_id=run_id,
        restaurant_name=search_name,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=costs_df,
        waste_df=waste_df,
        progress_callback=_progress_cb,
    )
    st.session_state["agent_state"] = agent_state
    if getattr(agent_state, "_reviews_df", None) is not None:
        st.session_state["reviews_df"] = agent_state._reviews_df

    # Save recommendations to database
    for rec in agent_state.recommendations:
        repo.save_recommendation(run_id, rec.model_dump(mode="json"))

    repo.update_run_status(run_id, "completed", avg_q)
    progress_bar.progress(100, text="Analysis complete!")

    st.success(
        f"✅ Analysis successfully completed for **{clean_name}**! "
        f"{len(agent_state.recommendations)} AI recommendations generated."
    )

    # Programmatic navigation to Sales Analytics
    st.session_state["_nav_to"] = "📈  Sales Analytics"
    st.rerun()
