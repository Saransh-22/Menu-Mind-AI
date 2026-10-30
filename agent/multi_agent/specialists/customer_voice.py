"""
Specialist Agent 4: Customer Voice Agent.
Expertise in review sentiment synthesis, item-level perception analysis,
recurring customer complaints, and external review attribution.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

from services.sentiment_service import analyze_sentiment_local, extract_item_review_insights
from config.settings import GEMINI_MODEL

logger = logging.getLogger(__name__)


class CustomerVoiceAgent:
    """Specialist agent for customer feedback and reputation analytics."""

    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client

    def answer_query(
        self,
        query: str,
        restaurant_name: str,
        reviews_df: Optional[pd.DataFrame],
        menu_df: Optional[pd.DataFrame],
    ) -> str:
        """Analyze verified reviews and feedback to answer customer satisfaction questions."""
        if reviews_df is None or reviews_df.empty:
            return (
                f"No customer reviews are currently available for **{restaurant_name}**. "
                "Upload a review CSV or click **Fetch External Reviews** in the Review Insights tab."
            )

        sentiment = analyze_sentiment_local(reviews_df)
        item_insights = extract_item_review_insights(reviews_df, menu_df)

        tot_rev = sentiment.review_count
        avg_rat = f"{sentiment.avg_rating:.1f}/5.0" if sentiment.avg_rating else "N/A"
        pos_pct = f"{sentiment.positive_pct * 100:.0f}%"
        neg_pct = f"{sentiment.negative_pct * 100:.0f}%"

        loved_themes = ", ".join(f"{t['theme']} ({t['frequency']} mentions)" for t in sentiment.appreciated_features[:3])
        complaints = ", ".join(f"{c['theme']} ({c['frequency']} mentions)" for c in sentiment.complaints[:3])

        # Find dishes mentioned
        top_compliment_dishes = [it for it in item_insights if it.get("top_compliment")][:3]
        top_complaint_dishes = [it for it in item_insights if it.get("top_complaint")][:3]

        dish_summary = ""
        if top_compliment_dishes:
            dish_summary += "\nPraised dishes: " + "; ".join(f"{d['item_name']} (\"{d['top_compliment']}\")" for d in top_compliment_dishes)
        if top_complaint_dishes:
            dish_summary += "\nFlagged dishes: " + "; ".join(f"{d['item_name']} (\"{d['top_complaint']}\")" for d in top_complaint_dishes)

        system_instruction = (
            "You are the Customer Voice Agent for MenuMind AI. "
            "Synthesize customer sentiment for the restaurant. "
            "Never invent quotes or ratings. State exact percentages, loved themes, and operational pain points."
        )

        prompt = (
            f"Restaurant: {restaurant_name}\n"
            f"Total Reviews: {tot_rev} (Rating: {avg_rat})\n"
            f"Sentiment: {pos_pct} Positive | {neg_pct} Negative\n"
            f"What Customers Love: {loved_themes or 'General quality'}\n"
            f"Recurring Complaints: {complaints or 'None highlighted'}\n"
            f"{dish_summary}\n\n"
            f"User Question: \"{query}\"\n\n"
            "Provide a direct, empathetic synthesis of customer perception and 2 concrete kitchen/service improvements."
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
                logger.warning("Customer Voice Agent LLM call failed: %s", exc)

        # Deterministic fallback
        return (
            f"### Customer Voice & Sentiment: {restaurant_name}\n\n"
            f"- **Volume Analyzed:** {tot_rev} reviews with an average score of **{avg_rat}**.\n"
            f"- **Sentiment Distribution:** {pos_pct} Positive vs {neg_pct} Negative.\n"
            f"- **Top Praises:** {loved_themes or 'Quality food and flavor'}\n"
            f"- **Primary Friction Points:** {complaints or 'Occasional wait times'}\n\n"
            f"**Operational Recommendation:** Address recurring complaints on flagged menu items to improve overall guest ratings and repeat visits."
        )
