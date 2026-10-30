"""
Agent orchestrator — the central tool-calling loop.
Uses Gemini function calling to drive multi-step analysis.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import pandas as pd

from agent.schemas import AgentState, Recommendation
from agent.state import create_initial_state, format_state_for_prompt
from agent.tools import ToolExecutor, TOOL_DEFINITIONS
from config.settings import (
    GEMINI_API_KEY,
    AGENT_MAX_TOOL_CALLS,
    GEMINI_MODEL,
    MIN_REVIEWS_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _get_gemini_client():
    """Return a configured Gemini client or None."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        logger.error("Failed to initialize Gemini client: %s", e)
        return None


def run_analysis(
    run_id: int,
    restaurant_name: str,
    menu_df: Optional[pd.DataFrame] = None,
    sales_df: Optional[pd.DataFrame] = None,
    reviews_df: Optional[pd.DataFrame] = None,
    costs_df: Optional[pd.DataFrame] = None,
    waste_df: Optional[pd.DataFrame] = None,
    progress_callback=None,  # callable(step_msg: str)
) -> AgentState:
    """
    Main agent entry point.
    Returns the completed AgentState including all recommendations.
    """
    available = []
    if menu_df is not None and not menu_df.empty:
        available.append("menu")
    if sales_df is not None and not sales_df.empty:
        available.append("sales")
    if reviews_df is not None and not reviews_df.empty:
        available.append("reviews")
    if costs_df is not None and not costs_df.empty:
        available.append("costs")
    if waste_df is not None and not waste_df.empty:
        available.append("waste")

    state = create_initial_state(
        run_id=run_id,
        restaurant_name=restaurant_name,
        available_data=available,
        max_tool_calls=AGENT_MAX_TOOL_CALLS,
    )

    gemini = _get_gemini_client()
    if not gemini:
        state.add_log("Gemini API key not configured — running deterministic analysis only.")

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=costs_df,
        gemini_client=gemini,
        waste_df=waste_df,
    )

    def progress(msg: str):
        state.add_log(msg)
        if progress_callback:
            progress_callback(msg)

    # ── Phase 1: Deterministic analysis (no API key needed) ───────────────
    if "sales" in available:
        progress("Analyzing sales data...")
        result = executor.execute("analyze_sales", {})
        if "error" in result:
            progress(f"Sales analysis warning: {result['error']}")

    if "costs" in available and "menu" in available:
        progress("Calculating profitability margins...")
        result = executor.execute("calculate_profitability", {})
        if "error" in result:
            progress(f"Profitability warning: {result['error']}")

    # ── Food waste analysis (only when verified records exist) ────────────
    if waste_df is not None and not waste_df.empty:
        progress("Analyzing verified food-waste records...")
        result = executor.execute("analyze_food_waste", {})
        if "error" in result:
            progress(f"Food waste analysis warning: {result['error']}")
        else:
            progress(
                f"Food waste analysis completed; recorded waste cost: "
                f"{result.get('total_waste_cost', 0)}"
            )

    # ── Phase 2: Review retrieval if needed ────────────────────────────────
    # Trigger if: no reviews at all, OR uploaded reviews are below the threshold
    uploaded_review_count = len(reviews_df) if reviews_df is not None else 0
    needs_retrieval = (
        "reviews" not in available
        or uploaded_review_count < MIN_REVIEWS_THRESHOLD
    )
    if needs_retrieval:
        if "reviews" not in available:
            progress("No reviews uploaded — attempting web retrieval...")
        else:
            progress(
                f"Only {uploaded_review_count} review(s) uploaded "
                f"(threshold: {MIN_REVIEWS_THRESHOLD}) — supplementing with web retrieval..."
            )
        try:
            result = executor.execute("search_restaurant_reviews", {})
            if result.get("review_count", 0) > 0:
                progress(
                    f"Retrieved {result['review_count']} reviews "
                    f"from {result.get('source')}"
                )
                if "reviews" not in available:
                    available.append("reviews")
                    state.available_data = available
            else:
                progress(
                    f"Review retrieval unavailable: "
                    f"{result.get('limitations', [''])[0]}"
                )
        except Exception as retrieval_exc:  # noqa: BLE001
            # Retrieval failure must not stop the main agent
            logger.warning(
                "Review retrieval raised an unexpected error: %s", retrieval_exc
            )
            progress(f"Review retrieval error (non-fatal): {retrieval_exc}")

    # ── Phase 3: Sentiment analysis ────────────────────────────────────────
    if "reviews" in available or (reviews_df is not None and not reviews_df.empty):
        progress("Analyzing customer sentiment...")
        result = executor.execute("analyze_sentiment", {})
        if "error" in result:
            progress(f"Sentiment warning: {result['error']}")

    # ── Phase 4: Recommendation generation ─────────────────────────────────
    if not state.can_call_tool():
        state.add_log("Max tool calls reached — stopping agent loop.")
        state.finished = True
        return state

    if gemini:
        progress("Generating AI-powered menu recommendations with Gemini...")
    else:
        progress("Generating evidence-based menu recommendations (deterministic engine)...")

    result = executor.execute("recommend_menu_actions", {})
    if "error" in result:
        progress(f"Recommendation error: {result['error']}")
        state.error = result["error"]
    else:
        progress(f"Generated {result.get('count', 0)} recommendations.")
        if not gemini:
            progress("Add GEMINI_API_KEY in .env for advanced LLM-generated narrative insights.")

    state.finished = True
    setattr(state, "_reviews_df", executor.reviews_df)
    return state
