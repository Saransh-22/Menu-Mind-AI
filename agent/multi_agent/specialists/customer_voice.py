"""
Specialist Agent 3: Customer Voice Agent.
Expertise in guest sentiment analysis, dish-specific feedback, recurring complaints,
and guest satisfaction driver identification.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

from services.gemini_service import get_gemini_service
import agent.multi_agent.tools as tool_svc

logger = logging.getLogger(__name__)


class CustomerVoiceAgent:
    """Specialist agent for customer feedback and review analytics."""

    def __init__(self, gemini_client=None):
        self.gemini_svc = get_gemini_service()

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        run_id: Optional[int] = None,
        reviews_df: Optional[pd.DataFrame] = None,
        menu_df: Optional[pd.DataFrame] = None,
        dish_name: Optional[str] = None,
    ) -> str:
        """Analyze verified reviews to answer natural language guest perception questions."""
        q_low = query.lower()

        # Extract dish name if present in query or parameter
        target_dish = dish_name
        if not target_dish:
            for dish in ["butter chicken", "biryani", "paneer", "naan", "dal makhani", "tikka", "pizza", "pasta"]:
                if dish in q_low:
                    target_dish = dish
                    break

        reviews_info = tool_svc.get_customer_reviews(run_id or 0, item_name=target_dish) if run_id else {"has_reviews": False}

        if not reviews_info.get("has_reviews"):
            if target_dish:
                return (
                    f"### Customer Reviews for '{target_dish.title()}'\n\n"
                    f"There are currently **no customer reviews mentioning '{target_dish.title()}'** in your uploaded review dataset for **{restaurant_name}**.\n\n"
                    "We do not synthesize or fabricate fictional guest feedback. "
                    "You can upload updated review datasets in the **Data Upload** section or fetch live online reviews in the **Review Insights** tab."
                )
            return (
                f"No customer reviews are currently available for **{restaurant_name}**. "
                "Upload a review CSV or click **Fetch External Reviews** in the Review Insights tab."
            )

        # Context construction
        if target_dish and reviews_info.get("reviews"):
            excerpts = [f"- \"{r['text']}\" ({r.get('rating') or 'N/A'}★)" for r in reviews_info["reviews"][:5]]
            review_context = (
                f"Dish: {target_dish.title()}\n"
                f"Total Mentions: {reviews_info.get('mention_count')}\n"
                f"Average Score for Item: {reviews_info.get('average_rating_for_item')}/5.0\n"
                f"Excerpts:\n" + "\n".join(excerpts)
            )
        else:
            sample_excerpts = [f"- \"{r['text']}\" ({r.get('rating') or 'N/A'}★)" for r in reviews_info.get("sample_reviews", [])[:4]]
            review_context = (
                f"Total Reviews: {reviews_info.get('review_count')}\n"
                f"Average Rating: {reviews_info.get('overall_average_rating')}/5.0\n"
                f"Recent Reviews:\n" + "\n".join(sample_excerpts)
            )

        system_instruction = (
            "You are the Customer Voice Agent for MenuMind AI. "
            "Synthesize customer feedback directly answering the user's question. "
            "Never fabricate customer reviews or sentiments. Quote or cite verified review excerpts. "
            "Categorize feedback into appreciated features, recurring complaints, and concrete kitchen/service improvements."
        )

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Grounded Customer Review Evidence:\n"
            f"{review_context}\n\n"
            f"User Question: \"{query}\"\n\n"
            "Provide a direct, empathetic, and evidence-grounded synthesis with 2 operational actions."
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
                logger.warning("Customer Voice Agent Gemini call failed: %s", exc)

        # Deterministic fallback
        if target_dish:
            return (
                f"### Customer Perception: {target_dish.title()} at {restaurant_name}\n\n"
                f"- **Review Mentions:** {reviews_info.get('mention_count')} mentions analyzed (Average Score: **{reviews_info.get('average_rating_for_item') or 'N/A'}/5.0**).\n\n"
                f"**Verified Review Excerpts:**\n"
                + "\n".join(f"- *\"{r['text']}\"* ({r.get('rating') or 'N/A'}★)" for r in reviews_info.get("reviews", [])[:4])
                + f"\n\n**Key Takeaways:**\n"
                f"- Address any consistency notes raised by guests in prep station handoffs.\n"
                f"- Maintain the favored elements that guests praised in their dining feedback."
            )

        return (
            f"### Guest Review Synthesis: {restaurant_name}\n\n"
            f"- **Volume Analyzed:** {reviews_info.get('review_count')} customer reviews.\n"
            f"- **Average Rating:** **{reviews_info.get('overall_average_rating') or 'N/A'}/5.0**.\n\n"
            f"**Recent Guest Excerpts:**\n"
            + "\n".join(f"- *\"{r['text']}\"* ({r.get('rating') or 'N/A'}★)" for r in reviews_info.get("sample_reviews", [])[:3])
        )
