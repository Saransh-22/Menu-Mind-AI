"""
Specialist Agent 5: Operations & Waste Agent.
Expertise in kitchen food waste prevention, prep trim control,
consumption velocity modeling, and inventory spoilage risk mitigation.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

from services.waste_analysis_service import calculate_waste_cost, analyze_spoilage_risk
from config.settings import GEMINI_MODEL

logger = logging.getLogger(__name__)


class OperationsWasteAgent:
    """Specialist agent for kitchen food waste mitigation."""

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        waste_records: list[dict],
        sales_df: Optional[pd.DataFrame],
        menu_df: Optional[pd.DataFrame],
        costs_df: Optional[pd.DataFrame],
    ) -> str:
        """Provide waste reduction guidance based on physical logs and sales velocity."""
        measured = calculate_waste_cost(waste_records) if waste_records else {
            "total_waste_cost": 0.0,
            "calculable_records": 0,
            "by_ingredient": {},
        }
        spoilage = analyze_spoilage_risk(sales_df, menu_df, costs_df)

        tot_measured = measured.get("total_waste_cost", 0.0)
        weekly_spoilage = spoilage.get("total_weekly_exposure", 0.0)
        high_risk_dishes = spoilage.get("slow_moving_items", [])
        action_items = spoilage.get("action_items", [])

        risk_list = ", ".join(f"{it['item_name']} (₹{it['weekly_exposure']:.0f}/wk)" for it in high_risk_dishes[:3]) if high_risk_dishes else "None identified"

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Measured Kitchen Waste: ₹{tot_measured:,.2f} across {measured.get('calculable_records', 0)} incidents\n"
            f"Weekly Spoilage Risk Exposure: ₹{weekly_spoilage:,.2f}\n"
            f"Slow-Moving High-Risk Dishes: {risk_list}\n"
            f"Recommended Mitigations: {'; '.join(action_items[:3]) if action_items else 'Standard FIFO rotation'}\n\n"
            f"Manager Question: \"{query}\"\n\n"
            "Provide 3 practical kitchen station adjustments to reduce discarded inventory and protect margins."
        )

        system_instruction = (
            "You are the Operations & Food Waste Agent for MenuMind AI. "
            "Help kitchen managers prevent waste and cut food costs. "
            "Ground your suggestions in batch prep, cross-utilization, and sales velocity."
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
                logger.warning("Waste Agent LLM call failed: %s", exc)

        # Deterministic fallback
        return (
            f"### Food Waste & Kitchen Operations: {restaurant_name}\n\n"
            f"- **Measured Waste Cost:** ₹{tot_measured:,.2f}\n"
            f"- **Weekly Spoilage Exposure:** ₹{weekly_spoilage:,.2f}\n"
            f"- **Vulnerable Slow-Moving Items:** {risk_list}\n\n"
            f"**Operational Mitigation Actions:**\n"
            f"1. **Ingredient Cross-Utilization:** Repurpose slow-moving ingredients into high-velocity daily specials or soups.\n"
            f"2. **Dynamic Par Levels:** Tighten order quantities on high-cost perishables based on weekday vs weekend sales velocity.\n"
            f"3. **Prep Trim Audits:** Conduct station-level prep training to minimize trimming losses on fresh produce and proteins."
        )
