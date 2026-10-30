"""
Analytics page — Premium executive dashboard with revenue bug fix.
Imputes revenue from menu prices when the sales CSV lacks a revenue column.
"""
from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.analytics_service import analyze_sales, analyze_menu, calculate_profitability
from agent.schemas import SalesAnalysisSummary

logger = logging.getLogger(__name__)

# ── Consistent premium chart palette ──────────────────────────────────────────
PALETTE = ["#0f3460", "#38bda3", "#e94560", "#f9a825", "#6c63ff",
           "#43b89c", "#1e7bbf", "#f36f38", "#8e44ad", "#27ae60"]


def _section(title: str):
    st.markdown(
        f"<div class='section-title'>{title}</div>",
        unsafe_allow_html=True,
    )


def _kpi_card(label: str, value: str, sub: str = "", col=None):
    html = f"""<div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>"""
    (col or st).markdown(html, unsafe_allow_html=True)


def _impute_revenue(sales_df: pd.DataFrame, menu_df: pd.DataFrame | None) -> pd.DataFrame:
    """
    If sales_df has no revenue column but has quantity_sold, compute revenue
    by joining against menu prices via item_name or item_id.
    Returns a copy of sales_df with a populated 'revenue' column.
    """
    df = sales_df.copy()
    if "revenue" in df.columns:
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
        if df["revenue"].notna().any():
            return df   # already has real revenue

    if menu_df is None or "price" not in menu_df.columns:
        return df

    menu = menu_df.copy()
    menu["price"] = pd.to_numeric(menu["price"], errors="coerce")

    # Build price lookup by item_name and item_id
    price_by_name: dict[str, float] = {}
    price_by_id: dict[str, float] = {}
    if "item_name" in menu.columns:
        price_by_name = {
            str(n).strip().lower(): p
            for n, p in zip(menu["item_name"], menu["price"])
            if pd.notna(p)
        }
    if "item_id" in menu.columns:
        price_by_id = {
            str(i).strip(): p
            for i, p in zip(menu["item_id"], menu["price"])
            if pd.notna(p)
        }

    # Resolve price per row
    def _get_price(row) -> float:
        name_col = "_matched_menu_name" if "_matched_menu_name" in row.index else (
            "item_name" if "item_name" in row.index else None
        )
        if name_col:
            key = str(row.get(name_col, "")).strip().lower()
            if key in price_by_name:
                return price_by_name[key]
        if "item_id" in row.index:
            key = str(row.get("item_id", "")).strip()
            if key in price_by_id:
                return price_by_id[key]
        return float("nan")

    qty = pd.to_numeric(df.get("quantity_sold", pd.Series(dtype=float)), errors="coerce")
    prices = df.apply(_get_price, axis=1)
    df["revenue"] = qty * prices
    return df


def _impute_category(sales_df: pd.DataFrame, menu_df: pd.DataFrame | None) -> pd.DataFrame:
    """Attach category to sales rows if missing, so charts don't show all-Uncategorised."""
    df = sales_df.copy()
    if menu_df is None or "category" not in menu_df.columns:
        return df

    cat_by_name: dict[str, str] = {}
    cat_by_id: dict[str, str] = {}
    if "item_name" in menu_df.columns:
        cat_by_name = {
            str(n).strip().lower(): str(c)
            for n, c in zip(menu_df["item_name"], menu_df["category"])
            if pd.notna(c)
        }
    if "item_id" in menu_df.columns:
        cat_by_id = {
            str(i).strip(): str(c)
            for i, c in zip(menu_df["item_id"], menu_df["category"])
            if pd.notna(c)
        }

    def _get_cat(row) -> str:
        name_col = "_matched_menu_name" if "_matched_menu_name" in row.index else (
            "item_name" if "item_name" in row.index else None
        )
        if name_col:
            key = str(row.get(name_col, "")).strip().lower()
            if key in cat_by_name:
                return cat_by_name[key]
        if "item_id" in row.index:
            key = str(row.get("item_id", "")).strip()
            if key in cat_by_id:
                return cat_by_id[key]
        return "Other"

    if "category" not in df.columns or df["category"].isna().all():
        df["category"] = df.apply(_get_cat, axis=1)

    return df


def render_analytics_page():
    st.markdown(
        "<h1 style='margin-bottom:4px;'>📈 Sales Analytics</h1>"
        "<p style='color:#6b7a8d;font-size:0.92rem;margin-bottom:24px;'>Executive overview of sales performance and profitability.</p>",
        unsafe_allow_html=True,
    )

    menu_df = st.session_state.get("menu_df")
    sales_df_raw = st.session_state.get("sales_df")
    costs_df = st.session_state.get("costs_df")

    if sales_df_raw is None:
        st.markdown(
            """<div style="background:#ffffff;border-radius:14px;padding:48px 32px;text-align:center;
                border:1px solid #e8edf4;box-shadow:0 1px 5px rgba(0,0,0,0.05);">
                <div style="font-size:2.5em;margin-bottom:12px;">📊</div>
                <div style="font-size:1.1rem;font-weight:600;color:#0d1b2a;margin-bottom:8px;">No Sales Data Yet</div>
                <div style="color:#8896a8;font-size:0.9rem;">Go to Overview → New Restaurant to upload your sales data.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # Fix revenue and category
    sales_df = _impute_revenue(sales_df_raw, menu_df)
    sales_df = _impute_category(sales_df, menu_df)

    # Recompute summary
    col_refresh, _ = st.columns([1, 5])
    refresh = col_refresh.button("🔄  Refresh", key="refresh_analytics")
    if "sales_summary" not in st.session_state or refresh:
        with st.spinner("Computing analytics…"):
            summary = analyze_sales(sales_df, menu_df)
            st.session_state["sales_summary"] = summary

    summary: SalesAnalysisSummary = st.session_state["sales_summary"]

    # Suppress the "revenue missing" warning if we imputed it
    displayed_warnings = [
        w for w in summary.warnings
        if "revenue" not in w.lower() or "revenue" in sales_df_raw.columns
    ]
    for w in displayed_warnings:
        st.warning(w)

    # ── KPI Row ───────────────────────────────────────────────────────────
    avg_price = (summary.total_revenue / summary.total_units) if summary.total_units > 0 else 0

    # Best-selling item
    best_item_name = "—"
    if summary.top_items:
        best_item_name = summary.top_items[0].item_name

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Revenue", f"₹{summary.total_revenue:,.0f}")
    k2.metric("Units Sold", f"{summary.total_units:,}")
    k3.metric("Avg Selling Price", f"₹{avg_price:.2f}" if avg_price else "—")
    k4.metric("Best-Selling Item", best_item_name[:20] + "…" if len(best_item_name) > 20 else best_item_name)
    k5.metric("Menu Items", summary.item_count)

    period_str = f"{summary.period_start or '?'} → {summary.period_end or '?'}"
    st.caption(f"Period: {period_str}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Revenue Over Time ─────────────────────────────────────────────────
    if "date" in sales_df.columns and "revenue" in sales_df.columns:
        _section("📅 Revenue Trend Over Time")
        df_time = sales_df.copy()
        df_time["date"] = pd.to_datetime(df_time["date"], errors="coerce")
        df_time["revenue"] = pd.to_numeric(df_time["revenue"], errors="coerce")
        df_time = df_time.dropna(subset=["date", "revenue"])

        if not df_time.empty:
            # Date filter
            min_date = df_time["date"].min().date()
            max_date = df_time["date"].max().date()
            fc1, fc2, _ = st.columns([1, 1, 3])
            start_f = fc1.date_input("From", value=min_date, min_value=min_date, max_value=max_date, key="rev_from")
            end_f = fc2.date_input("To", value=max_date, min_value=min_date, max_value=max_date, key="rev_to")

            mask = (df_time["date"].dt.date >= start_f) & (df_time["date"].dt.date <= end_f)
            df_filtered = df_time[mask]

            df_daily = df_filtered.groupby(df_filtered["date"].dt.date)["revenue"].sum().reset_index()
            df_daily.columns = ["Date", "Revenue"]
            df_daily["Revenue_7d"] = df_daily["Revenue"].rolling(7, min_periods=1).mean()

            fig_time = go.Figure()
            fig_time.add_trace(go.Scatter(
                x=df_daily["Date"], y=df_daily["Revenue"],
                mode="lines", name="Daily Revenue",
                line=dict(color="#38bda3", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(56,189,163,0.1)",
            ))
            fig_time.add_trace(go.Scatter(
                x=df_daily["Date"], y=df_daily["Revenue_7d"],
                mode="lines", name="7-day Average",
                line=dict(color="#0f3460", width=2, dash="dot"),
            ))
            fig_time.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=300, margin=dict(t=20, b=20, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(gridcolor="#f0f2f6", tickprefix="₹", tickformat=",.0f"),
                xaxis=dict(gridcolor="#f0f2f6"),
                hovermode="x unified",
            )
            st.plotly_chart(fig_time, use_container_width=True)

    # ── Top Items Charts ──────────────────────────────────────────────────
    all_items = summary.top_items + summary.weak_items
    seen: set = set()
    unique_items = []
    for item in all_items:
        if item.item_name not in seen:
            unique_items.append(item)
            seen.add(item.item_name)

    if unique_items:
        df_plot = pd.DataFrame([
            {
                "Item": i.item_name,
                "Revenue": i.total_revenue,
                "Units": i.total_quantity,
                "Category": i.category or "Other",
            }
            for i in unique_items
        ]).sort_values("Revenue", ascending=False).head(10)

        cl, cr = st.columns(2)

        with cl:
            _section("🏆 Top 10 Items by Revenue")
            fig_rev = go.Figure(go.Bar(
                x=df_plot["Revenue"],
                y=df_plot["Item"],
                orientation="h",
                marker=dict(
                    color=df_plot["Revenue"],
                    colorscale=[[0, "#c8e6f4"], [1, "#0f3460"]],
                    showscale=False,
                ),
                text=[f"₹{v:,.0f}" for v in df_plot["Revenue"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Revenue: ₹%{x:,.0f}<extra></extra>",
            ))
            fig_rev.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=380, margin=dict(t=10, b=20, l=10, r=60),
                yaxis=dict(autorange="reversed", gridcolor="#f0f2f6"),
                xaxis=dict(gridcolor="#f0f2f6", tickprefix="₹", tickformat=",.0f"),
            )
            st.plotly_chart(fig_rev, use_container_width=True)

        with cr:
            _section("📦 Top 10 Items by Quantity Sold")
            df_units = df_plot.sort_values("Units", ascending=False)
            fig_units = go.Figure(go.Bar(
                x=df_units["Units"],
                y=df_units["Item"],
                orientation="h",
                marker=dict(
                    color=df_units["Units"],
                    colorscale=[[0, "#c8f0ea"], [1, "#38bda3"]],
                    showscale=False,
                ),
                text=[f"{v:,}" for v in df_units["Units"]],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Units: %{x:,}<extra></extra>",
            ))
            fig_units.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=380, margin=dict(t=10, b=20, l=10, r=60),
                yaxis=dict(autorange="reversed", gridcolor="#f0f2f6"),
                xaxis=dict(gridcolor="#f0f2f6"),
            )
            st.plotly_chart(fig_units, use_container_width=True)

    # ── Category Charts ───────────────────────────────────────────────────
    if summary.category_summary:
        # Filter out "Uncategorised" if real categories exist
        cat_data = {
            k: v for k, v in summary.category_summary.items()
            if k not in ("Uncategorised", "Other") or len(summary.category_summary) == 1
        } or summary.category_summary

        cat_df = pd.DataFrame([{"Category": k, **v} for k, v in cat_data.items()])

        cl2, cr2 = st.columns(2)

        with cl2:
            _section("🍕 Revenue by Category (Donut)")
            fig_donut = go.Figure(go.Pie(
                labels=cat_df["Category"],
                values=cat_df["revenue"],
                hole=0.52,
                marker=dict(colors=PALETTE[:len(cat_df)]),
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            fig_donut.update_layout(
                paper_bgcolor="#ffffff", height=340,
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False,
                annotations=[dict(text="Revenue", x=0.5, y=0.5,
                                  font=dict(size=13, color="#0d1b2a", family="Inter"),
                                  showarrow=False)],
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with cr2:
            _section("📊 Category Performance")
            cat_sorted = cat_df.sort_values("revenue", ascending=False)
            fig_cat = go.Figure()
            fig_cat.add_trace(go.Bar(
                name="Revenue (₹)",
                x=cat_sorted["Category"],
                y=cat_sorted["revenue"],
                marker_color="#0f3460",
                yaxis="y",
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>",
            ))
            fig_cat.add_trace(go.Bar(
                name="Units Sold",
                x=cat_sorted["Category"],
                y=cat_sorted["quantity"],
                marker_color="#38bda3",
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Units: %{y:,}<extra></extra>",
            ))
            fig_cat.update_layout(
                barmode="group",
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=340, margin=dict(t=10, b=20, l=40, r=40),
                yaxis=dict(title="Revenue (₹)", gridcolor="#f0f2f6", tickprefix="₹", tickformat=",.0f"),
                yaxis2=dict(title="Units Sold", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_cat, use_container_width=True)

    # ── Profitability / Contribution Margin ───────────────────────────────
    if costs_df is not None and menu_df is not None:
        _section("💹 Contribution Margin by Item")
        prof_metrics = calculate_profitability(menu_df, costs_df, summary)
        calculable = [p for p in prof_metrics if p.calculable]
        if calculable:
            df_prof = pd.DataFrame([
                {
                    "Item": p.item_name,
                    "Selling Price (₹)": p.selling_price,
                    "Total Cost (₹)": p.total_cost,
                    "Margin (₹)": p.contribution_margin,
                    "Margin (%)": p.margin_pct,
                }
                for p in calculable
            ]).sort_values("Margin (%)", ascending=False)

            fig_margin = go.Figure(go.Bar(
                x=df_prof["Item"],
                y=df_prof["Margin (%)"],
                marker=dict(
                    color=df_prof["Margin (%)"],
                    colorscale=[[0, "#e74c3c"], [0.4, "#f9a825"], [1, "#27ae60"]],
                    cmin=df_prof["Margin (%)"].min(),
                    cmax=df_prof["Margin (%)"].max(),
                    showscale=True,
                    colorbar=dict(title="%", thickness=10),
                ),
                text=[f"{v:.1f}%" for v in df_prof["Margin (%)"]],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Margin: %{y:.1f}%<extra></extra>",
            ))
            fig_margin.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=340, margin=dict(t=10, b=60, l=40, r=40),
                yaxis=dict(gridcolor="#f0f2f6", ticksuffix="%"),
                xaxis=dict(tickangle=-35),
            )
            st.plotly_chart(fig_margin, use_container_width=True)

            with st.expander("📋 Full Margin Table"):
                st.dataframe(df_prof, use_container_width=True, hide_index=True)
        else:
            st.info("Cost data uploaded but margin cannot be calculated — ensure 'ingredient_cost' column is present.")

    # ── Menu Price Overview ───────────────────────────────────────────────
    if menu_df is not None:
        _section("🍽️ Menu Price Distribution")
        menu_stats = analyze_menu(menu_df)
        if menu_stats.get("price_stats"):
            ps = menu_stats["price_stats"]
            mp1, mp2, mp3, mp4 = st.columns(4)
            mp1.metric("Min Price", f"₹{ps['min']}")
            mp2.metric("Max Price", f"₹{ps['max']}")
            mp3.metric("Avg Price", f"₹{ps['mean']}")
            mp4.metric("Median Price", f"₹{ps['median']}")

        price_col = pd.to_numeric(menu_df["price"], errors="coerce").dropna() if "price" in menu_df.columns else pd.Series()
        if not price_col.empty:
            fig_hist = go.Figure(go.Histogram(
                x=price_col,
                nbinsx=20,
                marker_color="#0f3460",
                opacity=0.8,
            ))
            fig_hist.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                height=240, margin=dict(t=10, b=40, l=40, r=20),
                xaxis=dict(title="Price (₹)", gridcolor="#f0f2f6", tickprefix="₹"),
                yaxis=dict(title="# Items", gridcolor="#f0f2f6"),
                bargap=0.05,
            )
            st.plotly_chart(fig_hist, use_container_width=True)
