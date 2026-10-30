"""
Agent state management and session helpers.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from agent.schemas import AgentState

logger = logging.getLogger(__name__)


def create_initial_state(
    run_id: int,
    restaurant_name: str,
    available_data: list[str],
    max_tool_calls: int = 20,
) -> AgentState:
    return AgentState(
        run_id=run_id,
        restaurant_name=restaurant_name,
        available_data=available_data,
        max_tool_calls=max_tool_calls,
    )


def state_to_dict(state: AgentState) -> dict:
    return state.model_dump(mode="json")


def format_state_for_prompt(state: AgentState) -> str:
    """Compact summary of current state for the LLM system prompt."""
    lines = [
        f"Restaurant: {state.restaurant_name}",
        f"Available data: {', '.join(state.available_data) or 'none'}",
        f"Tools called: {state.tool_calls_made}/{state.max_tool_calls}",
    ]
    if state.sales_summary:
        s = state.sales_summary
        lines.append(
            f"Sales: {s.total_units} units, ${s.total_revenue:,.2f} revenue, "
            f"{s.item_count} items, period {s.period_start}–{s.period_end}"
        )
    if state.sentiment_summaries:
        lines.append(f"Sentiment: {len(state.sentiment_summaries)} analyses done")
    if state.profitability_metrics:
        calc = sum(1 for p in state.profitability_metrics if p.calculable)
        lines.append(
            f"Profitability: {calc}/{len(state.profitability_metrics)} items calculable"
        )
    if state.recommendations:
        lines.append(f"Recommendations: {len(state.recommendations)} generated")
    return "\n".join(lines)
