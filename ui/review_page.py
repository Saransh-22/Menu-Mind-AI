"""
Review Insights module — Comprehensive customer sentiment, 5-star rating distribution,
common customer complaints, appreciated features, item-wise insights, and review trends.
Clearly distinguishes verified customer reviews from SerpApi search snippets and web mentions.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.review_retrieval_service import retrieve_reviews
from services.sentiment_service import (
    analyze_sentiment_local,
    extract_item_review_insights,
    extract_review_trends,
)

logger = logging.getLogger(__name__)

_SNIPPET_SOURCES = frozenset({"SerpApi Google Search", "Google Custom Search API"})

SENTIMENT_PALETTE = {
    "Positive": "#10b981",  # Emerald
    "Neutral":  "#f59e0b",  # Amber
    "Negative": "#ef4444",  # Rose / Red
}


def _section(title: str, subtitle: Optional[str] = None):
    st.markdown(
        f"""<div style="margin:24px 0 12px 0;">
            <div class="section-title" style="margin-bottom:2px;">{title}</div>
            {f'<div style="color:#6b7a8d;font-size:0.83rem;margin-top:2px;">{subtitle}</div>' if subtitle else ''}
        </div>""",
        unsafe_allow_html=True,
    )


def _ensure_provenance_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure is_snippet, attribution, and review_type are structured."""
    out = df.copy()
    if "is_snippet" not in out.columns:
        if "attribution" in out.columns:
            out["is_snippet"] = out["attribution"].astype(str).str.contains("snippet", case=False, na=False)
        elif "source" in out.columns:
            out["is_snippet"] = out["source"].astype(str).isin(_SNIPPET_SOURCES)
        else:
            out["is_snippet"] = False
    else:
        out["is_snippet"] = out["is_snippet"].astype(bool)

    if "attribution" not in out.columns:
        out["attribution"] = out["is_snippet"].apply(
            lambda s: "SerpApi Google Search snippet" if s else "Uploaded customer review"
        )
    if "review_type" not in out.columns:
        out["review_type"] = out["is_snippet"].apply(
            lambda s: "search_snippet" if s else "verified_customer_review"
        )
    return out


def render_review_page():
    st.markdown(
        """<div style="margin-bottom:20px;">
            <h1 style="margin:0 0 6px 0;">⭐ Review Insights & Customer Voice</h1>
            <p style="color:#6b7a8d;font-size:0.92rem;margin:0;">
                Actionable sentiment analysis, 5-star rating breakdowns, customer complaints, and web retrieval powered by SerpApi.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    raw_reviews_df = st.session_state.get("reviews_df")
    restaurant = st.session_state.get("restaurant_info", {})
    menu_df = st.session_state.get("menu_df")

    # ── Empty state ────────────────────────────────────────────────────────
    if raw_reviews_df is None or raw_reviews_df.empty:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:44px 32px;text-align:center;
                border:1px solid #e8edf4;margin-bottom:20px;">
                <div style="font-size:2.8em;margin-bottom:12px;">⭐</div>
                <div style="font-size:1.15rem;font-weight:700;color:#0d1b2a;margin-bottom:8px;">No Reviews Loaded</div>
                <div style="color:#6b7a8d;font-size:0.9rem;max-width:540px;margin:0 auto 20px auto;line-height:1.5;">
                    Upload a <code>reviews.csv</code> in the <b>Data Upload</b> module, or retrieve public reviews
                    and organic web snippets automatically from Google using SerpApi.
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown(
                """<div style="background:#f8fafc;border-radius:12px;padding:20px;border:1px solid #e2e8f0;text-align:center;">
                    <div style="font-weight:600;color:#0d1b2a;margin-bottom:6px;">Automated Google Search Retrieval</div>
                    <div style="font-size:0.83rem;color:#64748b;margin-bottom:16px;">
                        Queries Google Search API via SerpApi for customer feedback and review snippets.
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
            r_name = restaurant.get("name", "") if restaurant else ""
            r_city = restaurant.get("city", "") if restaurant else ""
            if not r_name:
                st.info("ℹ️ Select or create a restaurant in Overview or Data Upload first to enable web review retrieval.")
            else:
                if st.button("🔍  Retrieve Public Reviews via SerpApi", type="primary", use_container_width=True):
                    with st.spinner(f"Searching Google for '{r_name}' in {r_city} via SerpApi…"):
                        result = retrieve_reviews(r_name, r_city, force_refresh=True)
                    if result.success and result.reviews:
                        rows = [{
                            "review_text": r.review_text,
                            "source": r.source,
                            "source_url": r.source_url,
                            "item_name": r.item_name or "",
                            "rating": r.rating,
                            "review_date": r.review_date,
                            "attribution": r.attribution or "SerpApi Google Search snippet",
                            "is_snippet": getattr(r, "is_snippet", True),
                            "review_type": getattr(r, "review_type", "search_snippet"),
                        } for r in result.reviews]
                        new_df = pd.DataFrame(rows)
                        st.session_state["reviews_df"] = new_df
                        st.success(f"✅ Successfully retrieved {len(result.reviews)} review snippets from {result.source}!")
                        st.rerun()
                    else:
                        st.error(f"❌ Review retrieval: {result.error or 'No snippets found'}")
                        for lim in result.limitations:
                            st.caption(f"• {lim}")
        return

    # Normalize provenance columns
    reviews_df = _ensure_provenance_columns(raw_reviews_df)

    # ── Source Attribution & Data Provenance Banner ────────────────────────
    snippet_mask = reviews_df["is_snippet"].astype(bool)
    snippet_count = int(snippet_mask.sum())
    verified_count = len(reviews_df) - snippet_count

    banner_style = (
        "background:linear-gradient(90deg, #f0fdf4 0%, #ffffff 100%);border-left:4px solid #10b981;"
        if snippet_count == 0 else
        "background:linear-gradient(90deg, #eff6ff 0%, #ffffff 100%);border-left:4px solid #3b82f6;"
    )

    st.markdown(
        f"""<div style="{banner_style}border-radius:10px;padding:14px 18px;margin-bottom:18px;border-top:1px solid #e2e8f0;border-right:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
                <div>
                    <span style="font-weight:700;color:#0d1b2a;font-size:0.95rem;">📊 Data Source Attribution:</span>
                    <span style="color:#059669;font-weight:600;margin-left:8px;">🟢 {verified_count} Verified Customer Review(s)</span>
                    <span style="color:#64748b;margin:0 6px;">·</span>
                    <span style="color:#2563eb;font-weight:600;">🔍 {snippet_count} External Web Search Snippet(s) (SerpApi)</span>
                </div>
                <div style="font-size:0.8rem;color:#64748b;">
                    Attributed transparently to ensure data integrity
                </div>
            </div>
            {f'<div style="font-size:0.82rem;color:#475569;margin-top:6px;border-top:1px dashed #cbd5e1;padding-top:6px;">⚠️ <b>Note on Search Snippets:</b> Snippets are extracted from Google Search indexed pages via SerpApi. They are not direct, first-party reviews and may reflect excerpts or aggregated third-party descriptions.</div>' if snippet_count > 0 else ''}
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Source Filter Bar ──────────────────────────────────────────────────
    f_col1, f_col2 = st.columns([3, 1])
    with f_col1:
        source_filter = st.radio(
            "Filter Reviews by Provenance:",
            options=["All Sources", "Verified Customer Reviews Only", "Web Search Snippets Only"],
            horizontal=True,
            key="review_provenance_filter",
            label_visibility="collapsed",
        )
    with f_col2:
        r_name = restaurant.get("name", "") if restaurant else ""
        r_city = restaurant.get("city", "") if restaurant else ""
        if st.button("🔄  Refresh / Add Web Snippets", help="Fetch or update Google snippets via SerpApi"):
            with st.spinner("Querying SerpApi Google Search…"):
                result = retrieve_reviews(r_name, r_city, force_refresh=True)
            if result.success and result.reviews:
                rows = [{
                    "review_text": r.review_text,
                    "source": r.source,
                    "source_url": r.source_url,
                    "item_name": r.item_name or "",
                    "rating": r.rating,
                    "review_date": r.review_date,
                    "attribution": r.attribution or "SerpApi Google Search snippet",
                    "is_snippet": getattr(r, "is_snippet", True),
                    "review_type": getattr(r, "review_type", "search_snippet"),
                } for r in result.reviews]
                new_snippets_df = pd.DataFrame(rows)
                # Deduplicate by review_text against existing
                combined = pd.concat([reviews_df, new_snippets_df], ignore_index=True)
                combined = combined.drop_duplicates(subset=["review_text"], keep="first").reset_index(drop=True)
                st.session_state["reviews_df"] = combined
                st.success(f"✅ Retrieved {len(result.reviews)} snippets from {result.source}!")
                st.rerun()
            else:
                st.warning(f"Could not retrieve new snippets: {result.error}")

    # Apply filter
    if source_filter == "Verified Customer Reviews Only":
        active_df = reviews_df[~reviews_df["is_snippet"].astype(bool)]
        if active_df.empty:
            st.info("No verified customer reviews uploaded. Upload a `reviews.csv` in Data Upload.")
            return
    elif source_filter == "Web Search Snippets Only":
        active_df = reviews_df[reviews_df["is_snippet"].astype(bool)]
        if active_df.empty:
            st.info("No web search snippets retrieved. Click 'Refresh / Add Web Snippets' to query SerpApi.")
            return
    else:
        active_df = reviews_df

    # ── Top-level KPIs ────────────────────────────────────────────────────
    summary = analyze_sentiment_local(active_df, item_name=None)
    avg_rating = summary.avg_rating

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Reviews Analyzed", len(active_df), help="Total count of review records in the active selection.")
    with k2:
        st.metric(
            "⭐ Average Rating",
            f"{avg_rating:.2f} / 5" if avg_rating is not None else "No Ratings",
            help="Average star rating calculated across records with numerical ratings.",
        )
    with k3:
        st.metric("😊 Positive Sentiment", f"{summary.positive_pct:.1f}%")
    with k4:
        st.metric("😐 Neutral Sentiment", f"{summary.neutral_pct:.1f}%")
    with k5:
        st.metric("😞 Negative Sentiment", f"{summary.negative_pct:.1f}%")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Row 1: Sentiment Donut & 5-Star Rating Distribution ────────────────
    c_donut, c_rating = st.columns(2)

    with c_donut:
        _section("🎯 Sentiment Distribution", "Overall sentiment breakdown of customer feedback.")
        fig_donut = go.Figure(go.Pie(
            labels=["Positive", "Neutral", "Negative"],
            values=[summary.positive_pct, summary.neutral_pct, summary.negative_pct],
            hole=0.62,
            marker=dict(colors=[SENTIMENT_PALETTE["Positive"], SENTIMENT_PALETTE["Neutral"], SENTIMENT_PALETTE["Negative"]]),
            textinfo="percent+label",
            textfont=dict(size=12, family="Inter"),
            hovertemplate="<b>%{label}</b>: %{percent}<extra></extra>",
        ))
        center_icon = "😊" if summary.positive_pct >= 50 else ("😞" if summary.negative_pct >= 40 else "😐")
        fig_donut.update_layout(
            paper_bgcolor="#ffffff",
            height=280,
            margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            annotations=[dict(
                text=f"<span style='font-size:24px;'>{center_icon}</span><br><b style='font-size:16px;'>{max(summary.positive_pct, summary.negative_pct):.0f}%</b>",
                x=0.5, y=0.5, font=dict(family="Inter", color="#0d1b2a"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with c_rating:
        _section("⭐ 5-Star Rating Distribution", "Breakdown of numeric star ratings across records.")
        dist = summary.rating_distribution
        has_dist_data = sum(dist.values()) > 0
        if has_dist_data:
            stars = ["1⭐", "2⭐", "3⭐", "4⭐", "5⭐"]
            counts = [dist.get(s, 0) for s in stars]
            colors_r = ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981"]
            fig_bar = go.Figure(go.Bar(
                x=stars,
                y=counts,
                marker_color=colors_r,
                text=counts,
                textposition="outside",
                hovertemplate="<b>%{x}</b>: %{y} reviews<extra></extra>",
            ))
            fig_bar.update_layout(
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                height=280,
                margin=dict(t=15, b=25, l=35, r=20),
                yaxis=dict(gridcolor="#f1f5f9", title="Count"),
                xaxis=dict(gridcolor="transparent"),
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.markdown(
                """<div style="background:#ffffff;border-radius:12px;padding:50px 20px;text-align:center;
                    border:1px dashed #cbd5e1;height:280px;display:flex;flex-direction:column;justify-content:center;">
                    <div style="color:#94a3b8;font-size:1.8em;margin-bottom:8px;">⭐</div>
                    <div style="color:#64748b;font-weight:600;font-size:0.95rem;">No Star Ratings Available</div>
                    <div style="color:#94a3b8;font-size:0.82rem;margin-top:4px;">The selected records do not contain numeric ratings.</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 2: Customer Voices — Appreciated Features vs Common Complaints ─
    _section("💬 Voice of the Customer: Key Themes & Feedback", "Extracted themes with representative verbatim quotes.")
    c_praise, c_complaint = st.columns(2)

    with c_praise:
        st.markdown(
            """<div style="background:#f0fdf4;border-radius:12px;padding:16px 20px;border:1px solid #bbf7d0;margin-bottom:12px;">
                <div style="font-weight:700;color:#166534;font-size:1rem;display:flex;align-items:center;gap:6px;">
                    <span>💚</span> Top Appreciated Features & Compliments
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if summary.appreciated_features:
            for item in summary.appreciated_features[:5]:
                quote_html = (
                    f'<div style="font-style:italic;color:#475569;font-size:0.83rem;margin-top:5px;background:#ffffffa0;padding:6px 10px;border-radius:6px;border-left:3px solid #10b981;">"{item["representative_quote"]}"</div>'
                    if item.get("representative_quote") else ""
                )
                st.markdown(
                    f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-weight:600;color:#0f172a;font-size:0.92rem;">✨ {item['theme']}</span>
                            <span style="background:#dcfce7;color:#15803d;font-size:0.75rem;padding:2px 8px;border-radius:12px;font-weight:600;">{item['frequency']}× mentioned</span>
                        </div>
                        {quote_html}
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No specific positive themes identified in the current sample.")

    with c_complaint:
        st.markdown(
            """<div style="background:#fef2f2;border-radius:12px;padding:16px 20px;border:1px solid #fecaca;margin-bottom:12px;">
                <div style="font-weight:700;color:#991b1b;font-size:1rem;display:flex;align-items:center;gap:6px;">
                    <span>🛑</span> Common Customer Complaints & Pain Points
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if summary.complaints:
            for item in summary.complaints[:5]:
                quote_html = (
                    f'<div style="font-style:italic;color:#475569;font-size:0.83rem;margin-top:5px;background:#ffffffa0;padding:6px 10px;border-radius:6px;border-left:3px solid #ef4444;">"{item["representative_quote"]}"</div>'
                    if item.get("representative_quote") else ""
                )
                st.markdown(
                    f"""<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-weight:600;color:#0f172a;font-size:0.92rem;">⚠️ {item['theme']}</span>
                            <span style="background:#fee2e2;color:#b91c1c;font-size:0.75rem;padding:2px 8px;border-radius:12px;font-weight:600;">{item['frequency']}× mentioned</span>
                        </div>
                        {quote_html}
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recurring complaints detected in the current review sample.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 3: Review Trends Over Time ────────────────────────────────────
    trends_df = extract_review_trends(active_df)
    if not trends_df.empty and len(trends_df) > 1:
        _section("📅 Review Volume & Sentiment Trends Over Time", "Historical review trends based on available review dates.")
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=trends_df["period"],
            y=trends_df["total_reviews"],
            name="Review Count",
            marker_color="#1e293b",
            hovertemplate="<b>%{x}</b>: %{y} reviews<extra></extra>",
        ))
        if trends_df["avg_rating"].notna().any():
            fig_trend.add_trace(go.Scatter(
                x=trends_df["period"],
                y=trends_df["avg_rating"],
                name="Avg Rating (⭐)",
                yaxis="y2",
                line=dict(color="#f59e0b", width=3),
                mode="lines+markers",
                hovertemplate="<b>%{x}</b> Avg Rating: %{y:.2f}⭐<extra></extra>",
            ))
            fig_trend.update_layout(
                yaxis2=dict(
                    title="Average Rating (⭐)",
                    overlaying="y",
                    side="right",
                    range=[0, 5.5],
                    gridcolor="transparent",
                ),
            )
        fig_trend.update_layout(
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            height=260,
            margin=dict(t=15, b=25, l=40, r=40),
            yaxis=dict(gridcolor="#f1f5f9", title="Review Volume"),
            xaxis=dict(gridcolor="transparent"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 4: Item-Wise Review Insights ──────────────────────────────────
    item_insights = extract_item_review_insights(active_df, menu_df)
    if item_insights:
        _section("🍽️ Item-Wise Review Insights", "Specific customer feedback and ratings mapped to menu items.")

        item_rows = []
        for it in item_insights:
            item_rows.append({
                "Menu Item": it["item_name"],
                "Mentions": it["mention_count"],
                "Avg Rating": f"{it['avg_rating']:.1f}⭐" if it["avg_rating"] is not None else "—",
                "Positive %": f"{it['positive_pct']:.0f}%",
                "Negative %": f"{it['negative_pct']:.0f}%",
                "Top Compliment": it["top_compliment"] or "—",
                "Top Complaint": it["top_complaint"] or "—",
            })
        st.dataframe(pd.DataFrame(item_rows), use_container_width=True, hide_index=True)

        # Item Deep Dive Selector
        with st.expander("🔍 Deep Dive: View Customer Quotes by Menu Item", expanded=False):
            item_names = [it["item_name"] for it in item_insights]
            chosen_item = st.selectbox("Select Menu Item to Inspect:", item_names, key="sel_item_deepdive")
            chosen_info = next((it for it in item_insights if it["item_name"] == chosen_item), None)
            if chosen_info and chosen_info.get("sample_reviews"):
                st.markdown(f"**Customer Quotes for {chosen_item}:**")
                for s in chosen_info["sample_reviews"]:
                    r_star = f"⭐ {s['rating']}" if pd.notna(s.get("rating")) else ""
                    st.markdown(f"> *\"{s.get('review_text', '')}\"* — <small style='color:#64748b;'>{r_star} ({s.get('source', '')})</small>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Row 5: All Reviews Explorer Table ─────────────────────────────────
    _section("📋 All Reviews & Search Snippets Explorer", "Full record listing with provenance badges and source attribution.")

    s_col1, s_col2 = st.columns([3, 1])
    with s_col1:
        search_term = st.text_input("🔍 Search within reviews:", placeholder="Filter by keyword (e.g. pizza, crust, slow, salt)…", key="review_kw_search")
    with s_col2:
        export_df = active_df.copy()
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            "📥 Export Reviews (CSV)",
            data=csv_data,
            file_name="menumind_reviews_export.csv",
            mime="text/csv",
            use_container_width=True,
        )

    view_df = active_df.copy()
    if search_term:
        term_clean = search_term.strip().lower()
        view_df = view_df[
            view_df["review_text"].astype(str).str.lower().str.contains(term_clean, na=False)
            | view_df.get("item_name", pd.Series()).astype(str).str.lower().str.contains(term_clean, na=False)
        ]

    # Format display columns
    display_rows = []
    for _, row in view_df.head(200).iterrows():
        is_snip = bool(row.get("is_snippet", False))
        prov_badge = "🔍 Web Snippet" if is_snip else "🟢 Verified Review"
        r_rating = f"{float(row['rating']):.1f}⭐" if pd.notna(row.get("rating")) else "—"
        display_rows.append({
            "Provenance": prov_badge,
            "Menu Item": str(row.get("item_name") or "General"),
            "Rating": r_rating,
            "Review Text / Snippet": str(row.get("review_text") or ""),
            "Date": str(row.get("review_date") or "—"),
            "Source": str(row.get("source") or "—"),
            "Attribution": str(row.get("attribution") or ""),
        })

    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    st.caption(f"Showing {len(display_rows)} of {len(view_df)} matching records. Maximum 200 displayed.")
