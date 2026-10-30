"""
Specialist Agent 2: Business Intelligence Agent.
Expertise in sales performance analytics, volume vs revenue leaders,
dish margin contribution, and category velocity.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import pandas as pd

from services.gemini_service import get_gemini_service
import agent.multi_agent.tools as tool_svc

logger = logging.getLogger(__name__)


class BusinessIntelligenceAgent:
    """Specialist analyst for financial, revenue, and sales performance."""

    def __init__(self, gemini_client=None):
        self.gemini_svc = get_gemini_service()

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        run_id: Optional[int] = None,
        sales_df: Optional[pd.DataFrame] = None,
        menu_df: Optional[pd.DataFrame] = None,
        costs_df: Optional[pd.DataFrame] = None,
    ) -> str:
        """Analyze verified business data to answer specific natural language questions."""
        q_low = query.lower()

        # 1. Check if asking specifically about best-selling / top dishes
        is_best_selling_query = any(k in q_low for k in ["best-selling", "best selling", "top dish", "top seller", "highest volume", "highest revenue", "most popular"])
        is_profit_query = any(k in q_low for k in ["profit", "margin", "profitable", "contribution", "cost margin"])

        if run_id:
            top_sales = tool_svc.get_top_selling_items(run_id, limit=5)
            profit_data = tool_svc.get_item_profitability(run_id)
        elif sales_df is not None and not sales_df.empty:
            from services.analytics_service import impute_revenue, analyze_sales, calculate_profitability
            clean_sales = impute_revenue(sales_df, menu_df)
            qty_col = tool_svc._find_qty_col(clean_sales)
            vol_grouped = clean_sales.groupby("item_name")[qty_col].sum().sort_values(ascending=False)
            rev_col = "total_revenue" if "total_revenue" in clean_sales.columns else "revenue"
            rev_grouped = clean_sales.groupby("item_name")[rev_col].sum().sort_values(ascending=False)
            top_sales = {
                "has_data": True,
                "volume_leader": {"item_name": str(vol_grouped.index[0]), "units_sold": int(vol_grouped.iloc[0])} if not vol_grouped.empty else None,
                "revenue_leader": {"item_name": str(rev_grouped.index[0]), "revenue": float(rev_grouped.iloc[0])} if not rev_grouped.empty else None,
                "top_by_volume": [{"item_name": str(k), "units_sold": int(v)} for k, v in vol_grouped.head(5).items()],
                "top_by_revenue": [{"item_name": str(k), "revenue": float(v)} for k, v in rev_grouped.head(5).items()],
            }
            summary = analyze_sales(clean_sales, menu_df)
            effective_menu = menu_df if menu_df is not None else pd.DataFrame()
            profit_metrics = calculate_profitability(effective_menu, costs_df, summary)
            profit_data = {
                "calculable": bool(profit_metrics),
                "top_margin_items": [
                    {"item_name": getattr(p, "item_name", "Item"), "margin_pct": getattr(p, "margin_pct", None), "margin_amount": getattr(p, "margin_amount", None), "selling_price": getattr(p, "selling_price", 0.0), "cost_per_unit": getattr(p, "cost_per_unit", None)}
                    for p in profit_metrics if getattr(p, "margin_pct", None) is not None
                ]
            }
        else:
            top_sales = {"has_data": False}
            profit_data = {"calculable": False}

        if not top_sales.get("has_data") and (sales_df is None or sales_df.empty):
            return (
                f"I cannot analyze sales performance for **{restaurant_name}** because no sales transaction "
                "dataset has been uploaded for this run yet. Please upload sales records in the **Data Upload** section."
            )

        # Build numerical context
        vol_leader = top_sales.get("volume_leader")
        rev_leader = top_sales.get("revenue_leader")

        vol_text = (
            f"Volume Leader (Units Sold): {vol_leader['item_name']} ({vol_leader['units_sold']} units)\n"
            if vol_leader else "Volume Leader: N/A\n"
        )
        rev_text = (
            f"Revenue Leader (Total INR): {rev_leader['item_name']} (₹{rev_leader['revenue']:,.2f})\n"
            if rev_leader else "Revenue Leader: N/A\n"
        )

        top_vol_list = ", ".join(f"{i['item_name']} ({i['units_sold']} units)" for i in top_sales.get("top_by_volume", [])[:5])
        top_rev_list = ", ".join(f"{i['item_name']} (₹{i['revenue']:,.0f})" for i in top_sales.get("top_by_revenue", [])[:5])

        profit_context = ""
        if profit_data.get("calculable") and profit_data.get("top_margin_items"):
            top_margin = profit_data["top_margin_items"][:3]
            profit_parts = []
            for i in top_margin:
                if i.get("margin_pct") is not None:
                    m_pct = f"{i['margin_pct']*100:.1f}%"
                    m_amt = f"₹{i['margin_amount']:.2f}" if i.get("margin_amount") is not None else "N/A"
                    profit_parts.append(f"{i.get('item_name', 'Unknown')} ({m_pct} margin / {m_amt} contribution)")
            if profit_parts:
                profit_context = "Top Margin Items: " + ", ".join(profit_parts)

        system_instruction = (
            "You are the Principal Business Intelligence Agent for MenuMind AI. "
            "Answer the user's specific question directly, concisely, and accurately using ONLY the provided verified metrics. "
            "Crucial Rule: Clearly distinguish between dishes that lead in unit sales volume (quantity) versus total revenue (INR). "
            "Never confuse quantity with revenue. Never invent numbers. Format numbers cleanly with INR (₹) and exact unit counts."
        )

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Active Run: #{run_id or 'N/A'}\n"
            f"Grounded Sales Performance:\n"
            f"{vol_text}"
            f"{rev_text}"
            f"Top 5 by Unit Volume: {top_vol_list}\n"
            f"Top 5 by Gross Revenue: {top_rev_list}\n"
            f"{profit_context}\n\n"
            f"User Question: \"{query}\"\n\n"
            "Provide a direct, conversational, and precise answer addressing exactly what was asked."
        )

        if self.gemini_svc.is_available():
            try:
                res = self.gemini_svc.generate_content(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
                if res:
                    return res
            except Exception as exc:
                logger.warning("BI Agent Gemini call failed: %s", exc)

        # Deterministic fallback directly answering the query
        if is_best_selling_query and vol_leader and rev_leader:
            if vol_leader["item_name"].lower() == rev_leader["item_name"].lower():
                return (
                    f"### Best-Selling Performance: {restaurant_name}\n\n"
                    f"**{vol_leader['item_name'].title()}** is your undisputed top performer in both sales metrics:\n"
                    f"- **Unit Volume:** **{vol_leader['units_sold']} units sold**\n"
                    f"- **Total Revenue:** **₹{rev_leader['revenue']:,.2f}**\n\n"
                    f"It accounts for both the highest customer demand and the largest gross dollar contribution to your top line."
                )
            else:
                return (
                    f"### Best-Selling Performance: {restaurant_name}\n\n"
                    f"In restaurant analytics, 'best-selling' is evaluated in two distinct ways: **by volume (units sold)** and **by gross revenue (INR generated)**.\n\n"
                    f"- **Highest Volume Dish:** **{vol_leader['item_name'].title()}** with **{vol_leader['units_sold']} units sold** (generating ₹{next((r['revenue'] for r in top_sales.get('top_by_revenue', []) if r['item_name'] == vol_leader['item_name']), 0):,.2f}).\n"
                    f"- **Highest Revenue Dish:** **{rev_leader['item_name'].title()}** with **₹{rev_leader['revenue']:,.2f}** in sales (from {next((v['units_sold'] for v in top_sales.get('top_by_volume', []) if v['item_name'] == rev_leader['item_name']), 0)} units sold).\n\n"
                    f"**Top Volume Ranking:**\n"
                    + "\n".join(f"{idx+1}. **{it['item_name'].title()}**: {it['units_sold']} units sold" for idx, it in enumerate(top_sales.get("top_by_volume", [])[:5]))
                    + "\n\n**Top Revenue Ranking:**\n"
                    + "\n".join(f"{idx+1}. **{it['item_name'].title()}**: ₹{it['revenue']:,.2f}" for idx, it in enumerate(top_sales.get("top_by_revenue", [])[:5]))
                )

        if is_profit_query and profit_data.get("calculable") and profit_data.get("top_margin_items"):
            top = profit_data["top_margin_items"][0]
            top_m_amt = f"₹{top['margin_amount']:.2f}" if top.get("margin_amount") is not None else "N/A"
            sp = f"₹{top['selling_price']:.2f}" if top.get("selling_price") is not None else "N/A"
            cpu = f"₹{top['cost_per_unit']:.2f}" if top.get("cost_per_unit") is not None else "N/A"
            return (
                f"### Profitability & Margin Analysis: {restaurant_name}\n\n"
                f"The dish generating the highest profit margin in your active dataset is **{top['item_name'].title()}**:\n"
                f"- **Contribution Margin:** **{top.get('margin_pct', 0)*100:.1f}%**\n"
                f"- **Margin Amount:** **{top_m_amt}** per serving (Selling Price: {sp}, Cost: {cpu})\n\n"
                f"**Top High-Margin Dishes:**\n"
                + "\n".join(
                    f"- **{it['item_name'].title()}**: {it.get('margin_pct', 0)*100:.1f}% margin "
                    + (f"(₹{it['margin_amount']:.2f} profit/unit)" if it.get("margin_amount") is not None else "")
                    for it in profit_data["top_margin_items"][:5] if it.get("margin_pct") is not None
                )
            )

        # General sales performance
        return (
            f"### Sales Performance Summary: {restaurant_name}\n\n"
            f"- **Unit Volume Leader:** {vol_leader['item_name'].title() if vol_leader else 'N/A'} ({vol_leader['units_sold'] if vol_leader else 0} units)\n"
            f"- **Gross Revenue Leader:** {rev_leader['item_name'].title() if rev_leader else 'N/A'} (₹{rev_leader['revenue']:,.2f} if rev_leader else '0')\n"
        )
