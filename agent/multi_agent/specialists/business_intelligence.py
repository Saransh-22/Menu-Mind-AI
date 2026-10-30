"""
Specialist Agent 3: Business Intelligence Agent.
Expertise in sales performance analytics, revenue anomalies,
item profitability margins, and historical period-over-period comparisons.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

from services.analytics_service import analyze_sales, calculate_profitability, impute_revenue, impute_category
from config.settings import GEMINI_MODEL

logger = logging.getLogger(__name__)


class BusinessIntelligenceAgent:
    """Specialist analyst for financial and sales performance."""

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        sales_df: Optional[pd.DataFrame],
        menu_df: Optional[pd.DataFrame],
        costs_df: Optional[pd.DataFrame],
    ) -> str:
        """Analyze verified business data to answer natural language questions."""
        if sales_df is None or sales_df.empty:
            return (
                f"I cannot analyze sales performance for **{restaurant_name}** because no sales transaction "
                "dataset has been uploaded for this run yet. Please upload sales records in the **Data Upload** section."
            )

        clean_sales = impute_revenue(sales_df, menu_df)
        clean_sales = impute_category(clean_sales, menu_df)
        summary = analyze_sales(clean_sales, menu_df)

        profitability = []
        if menu_df is not None and not menu_df.empty:
            profitability = calculate_profitability(menu_df, costs_df, summary)

        # Build numerical context
        tot_rev = summary.total_revenue
        tot_units = summary.total_units
        avg_ticket = tot_rev / tot_units if tot_units > 0 else 0.0

        top_3 = ", ".join(f"{it.item_name} (₹{it.total_revenue:,.0f})" for it in summary.top_items[:3])
        weak_3 = ", ".join(f"{it.item_name} (₹{it.total_revenue:,.0f})" for it in summary.weak_items[:3]) if summary.weak_items else "None"

        cat_breakdown = ", ".join(f"{cat}: ₹{data['revenue']:,.0f}" for cat, data in list(summary.category_summary.items())[:4])

        def _get_m(p):
            return getattr(p, "margin_pct", None) if not isinstance(p, dict) else p.get("margin_pct")

        def _get_name(p):
            return getattr(p, "item_name", "Item") if not isinstance(p, dict) else p.get("item_name", "Item")

        high_margin = [p for p in profitability if _get_m(p) is not None and _get_m(p) >= 0.65]
        low_margin = [p for p in profitability if _get_m(p) is not None and _get_m(p) < 0.45]

        margin_context = ""
        if high_margin:
            margin_context += f"\nHigh-margin leaders: {', '.join(_get_name(p) for p in high_margin[:3])} (>65% margin)."
        if low_margin:
            margin_context += f"\nLow-margin items: {', '.join(_get_name(p) for p in low_margin[:3])} (<45% margin)."

        system_instruction = (
            "You are the Principal Business Intelligence Agent for MenuMind AI. "
            "Answer the restaurant owner's question using ONLY the provided verified metrics. "
            "Never invent numbers or dates. Format with clear headings, bullet points, and exact INR (₹) figures."
        )

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Period: {summary.period_start or 'N/A'} to {summary.period_end or 'N/A'}\n"
            f"Total Revenue: ₹{tot_rev:,.2f}\n"
            f"Units Sold: {tot_units:,}\n"
            f"Average Spend per Unit: ₹{avg_ticket:.2f}\n"
            f"Top Revenue Drivers: {top_3}\n"
            f"Lowest Volume Items: {weak_3}\n"
            f"Category Distribution: {cat_breakdown}\n"
            f"{margin_context}\n\n"
            f"Question: \"{query}\"\n\n"
            "Provide a direct, data-grounded business analysis with 2 concrete recommendations."
        )

        if self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config={"system_instruction": system_instruction},
                )
                if response and response.text:
                    return response.text
            except Exception as exc:
                logger.warning("BI Agent LLM call failed: %s", exc)

        # High-quality deterministic fallback
        return (
            f"### Business & Revenue Intelligence: {restaurant_name}\n\n"
            f"- **Total Revenue:** ₹{tot_rev:,.2f} across **{tot_units:,} units sold**.\n"
            f"- **Average Item Price:** ₹{avg_ticket:.2f}\n"
            f"- **Top Revenue Generators:** {top_3}\n"
            f"- **Underperforming Volume:** {weak_3}\n"
            f"- **Category Contribution:** {cat_breakdown}\n\n"
            f"**Strategic Assessment:**\n"
            f"Your revenue is heavily anchored by your top 3 sellers. To improve overall yield, consider bundling slow movers with high-velocity anchors, and adjust portion/ingredient costs on bottom-quartile dishes."
        )
