"""
Specialist Agent 4: Operations & Waste Agent.
Expertise in kitchen food waste mitigation, prep trim utilization,
consumption velocity modeling, and inventory spoilage risk reduction.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

from services.gemini_service import get_gemini_service
import agent.multi_agent.tools as tool_svc

logger = logging.getLogger(__name__)


class OperationsWasteAgent:
    """Specialist agent for kitchen food waste mitigation and inventory velocity."""

    def __init__(self, gemini_client=None):
        self.gemini_svc = get_gemini_service()

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        run_id: Optional[int] = None,
        waste_records: Optional[list[dict]] = None,
        sales_df: Optional[pd.DataFrame] = None,
        menu_df: Optional[pd.DataFrame] = None,
        costs_df: Optional[pd.DataFrame] = None,
    ) -> str:
        """Provide waste reduction guidance based on physical logs and sales velocity."""
        q_low = query.lower()

        waste_info = tool_svc.get_food_waste_records(run_id or 0) if run_id else {"has_records": False}
        spoilage_info = tool_svc.get_spoilage_risk(run_id or 0) if run_id else {"has_data": False}

        has_physical_records = waste_info.get("has_records", False)
        tot_waste_cost = waste_info.get("total_waste_cost", 0.0)

        # Spoilage details
        slow_movers = spoilage_info.get("slow_moving_items", [])
        weekly_spoilage = spoilage_info.get("total_weekly_exposure", 0.0)
        action_items = spoilage_info.get("action_items", [])

        waste_record_context = (
            f"- Physical Waste Records: {waste_info.get('record_count')} incidents logged, totaling ₹{tot_waste_cost:,.2f} in measured food cost.\n"
            if has_physical_records else
            "- Physical Waste Records: The current dataset does not contain enough physical waste records to identify the biggest measured sources. (Do not claim zero risk).\n"
        )

        spoilage_context = ""
        if slow_movers:
            risk_list = ", ".join(f"{it['item_name']} (₹{it['weekly_exposure']:.0f}/wk exposure)" for it in slow_movers[:4])
            spoilage_context = f"- Slow-Moving Dishes Posing Spoilage Risk: {risk_list}\n- Total Weekly Spoilage Exposure: ₹{weekly_spoilage:,.2f}\n"
        else:
            spoilage_context = "- Spoilage Risk Modeling: Based on sales velocity, inventory turnover is within standard range.\n"

        system_instruction = (
            "You are the Operations & Food Waste Specialist Agent for MenuMind AI. "
            "Help restaurant managers and head chefs eliminate food waste and protect food cost margins. "
            "Important guidelines: "
            "1. If physical waste records are missing, explicitly inform the user that the current dataset lacks logged waste records. Never claim there is zero spoilage risk just because logs are absent. "
            "2. Ground suggestions in slow-moving dish velocity, station prep audits, dynamic par ordering, and prep trim cross-utilization (stocks, marinades, staff meals). "
            "3. Answer the user's specific question directly with concrete kitchen actions."
        )

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Active Run: #{run_id or 'N/A'}\n"
            f"Grounded Waste & Inventory Evidence:\n"
            f"{waste_record_context}"
            f"{spoilage_context}"
            f"Recommended Mitigations: {'; '.join(action_items[:3]) if action_items else 'FIFO rotation, par levels'}\n\n"
            f"Manager Question: \"{query}\"\n\n"
            "Provide a direct, practical operations response with 3 station-level kitchen steps."
        )

        if self.gemini_svc.is_available():
            try:
                res = self.gemini_svc.generate_content(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
                if res:
                    return res
            except Exception as exc:
                logger.warning("Waste Agent Gemini call failed: %s", exc)

        # Deterministic fallback
        if not has_physical_records:
            return (
                f"### Food Waste Intelligence: {restaurant_name}\n\n"
                f"**Data Notice:** The current analysis run **does not contain physical food waste records** to identify the biggest measured kitchen waste sources. "
                "However, lack of recorded waste logs does *not* indicate zero spoilage risk.\n\n"
                f"**Inventory Velocity & Spoilage Exposure:**\n"
                + (f"- Slow-moving items with perishable risk: {', '.join(it['item_name'].title() for it in slow_movers[:3])} (₹{weekly_spoilage:,.2f} weekly exposure).\n\n" if slow_movers else "- No critical slow-moving inventory risks flagged.\n\n")
                + f"**3 Immediate Waste Reduction Strategies:**\n"
                f"1. **Prep Trim Cross-Utilization:** Repurpose aromatic vegetable ends and poultry bones into concentrated master stock reductions for signature curries.\n"
                f"2. **Dynamic Par-Level Ordering:** Recalibrate raw ingredient procurement on high-perishable proteins based on weekday vs weekend demand patterns.\n"
                f"3. **Physical Waste Logging:** Track prep discards and over-portioning in the **Food Waste** tab to isolate exact station loss points."
            )

        return (
            f"### Food Waste Intelligence: {restaurant_name}\n\n"
            f"- **Measured Waste Cost:** **₹{tot_waste_cost:,.2f}** across {waste_info.get('record_count')} logged incidents.\n"
            f"- **Weekly Spoilage Risk Exposure:** **₹{weekly_spoilage:,.2f}**.\n\n"
            f"**Station Mitigation Steps:**\n"
            f"1. **Batch Sizing:** Reduce prep batch volume on slow-moving gravies to prevent end-of-night discard.\n"
            f"2. **Cross-Utilization Specials:** Feature daily specials utilizing ingredients nearing shelf-life.\n"
            f"3. **FIFO Audit:** Enforce strict First-In, First-Out rotation in walk-in coolers."
        )
