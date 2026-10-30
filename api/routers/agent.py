"""
AI Agent orchestration, tool execution, and progress streaming.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.dependencies import get_verified_run, get_run_datasets
from agent.orchestrator import run_analysis
from database import repository as repo
from services.dataset_storage import save_run_dataset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["AI Recommendations"])

# In-memory progress tracking for background agent execution
_analysis_state: dict[int, dict[str, Any]] = {}


def _execute_agent_task(run_id: int):
    """Background worker executing the agent analysis pipeline."""
    try:
        run = repo.get_analysis_run(run_id)
        if not run:
            return
        restaurant = repo.get_restaurant(run["restaurant_id"])
        rest_name = restaurant["name"] if restaurant else "Restaurant"
        if restaurant and restaurant.get("city"):
            rest_name += f", {restaurant['city']}"

        datasets = get_run_datasets(run_id)
        menu_df = datasets.get("menu")
        sales_df = datasets.get("sales")
        reviews_df = datasets.get("reviews")
        costs_df = datasets.get("costs")

        # Load verified waste records
        waste_records = repo.list_waste_records(run_id)
        waste_df = pd.DataFrame(waste_records) if waste_records else None

        _analysis_state[run_id] = {
            "status": "running",
            "steps": ["Initializing AI Agent Orchestrator..."],
            "error": None,
            "recommendations_count": 0,
        }

        def on_progress(msg: str):
            if run_id in _analysis_state:
                _analysis_state[run_id]["steps"].append(msg)
                logger.info("[Run #%s Progress] %s", run_id, msg)

        agent_state = run_analysis(
            run_id=run_id,
            restaurant_name=rest_name,
            menu_df=menu_df,
            sales_df=sales_df,
            reviews_df=reviews_df,
            costs_df=costs_df,
            waste_df=waste_df,
            progress_callback=on_progress,
        )

        # If external reviews were fetched during analysis, persist them
        if hasattr(agent_state, "_reviews_df") and agent_state._reviews_df is not None:
            save_run_dataset(run_id, "reviews", agent_state._reviews_df)

        # Persist generated recommendations into SQLite
        existing_recs = repo.list_recommendations(run_id)
        existing_keys = {
            (str(r["item_name"]).strip().lower(), str(r["action"]).upper())
            for r in existing_recs
        }

        saved_count = len(existing_recs)
        for rec in agent_state.recommendations:
            key = (rec.item_name.strip().lower(), rec.action.value.upper())
            if key not in existing_keys:
                repo.save_recommendation(run_id, rec.model_dump(mode="json"))
                existing_keys.add(key)
                saved_count += 1

        repo.update_run_status(run_id, "completed")

        _analysis_state[run_id] = {
            "status": "completed",
            "steps": _analysis_state[run_id]["steps"] + ["Analysis completed successfully!"],
            "error": agent_state.error,
            "recommendations_count": saved_count,
        }

    except Exception as exc:
        logger.exception("Agent execution failed for run #%s: %s", run_id, exc)
        _analysis_state[run_id] = {
            "status": "failed",
            "steps": _analysis_state.get(run_id, {}).get("steps", []) + [f"Fatal Error: {exc}"],
            "error": str(exc),
            "recommendations_count": 0,
        }
        repo.update_run_status(run_id, "failed")


@router.post("/{run_id}/run-analysis")
def trigger_ai_analysis(
    run_id: int,
    background_tasks: BackgroundTasks,
    run: dict = Depends(get_verified_run),
):
    """Trigger the Gemini-powered AI multi-step agent loop."""
    current_state = _analysis_state.get(run_id)
    if current_state and current_state.get("status") == "running":
        return {
            "status": "already_running",
            "message": "Analysis is currently executing for this run.",
            "steps": current_state.get("steps", []),
        }

    repo.update_run_status(run_id, "running")
    _analysis_state[run_id] = {
        "status": "running",
        "steps": ["Analysis requested..."],
        "error": None,
        "recommendations_count": 0,
    }
    background_tasks.add_task(_execute_agent_task, run_id)
    return {
        "status": "started",
        "message": "AI analysis started in background.",
        "run_id": run_id,
    }


@router.get("/{run_id}/analysis-progress")
def get_analysis_progress(run_id: int, run: dict = Depends(get_verified_run)):
    """Poll for live status, step messages, and final completion."""
    state = _analysis_state.get(run_id)
    if not state:
        recs = repo.list_recommendations(run_id)
        is_completed = run.get("status") == "completed" or bool(recs)
        return {
            "status": "completed" if is_completed else run.get("status", "pending"),
            "steps": ["Loaded existing run data."] if is_completed else [],
            "error": None,
            "recommendations_count": len(recs),
        }
    return state


@router.get("/{run_id}/analysis-stream")
async def stream_analysis_progress(run_id: int, run: dict = Depends(get_verified_run)):
    """Server-Sent Events (SSE) endpoint for streaming agent progress."""
    async def event_generator():
        last_step_idx = 0
        while True:
            state = _analysis_state.get(run_id, {})
            steps = state.get("steps", [])
            status_val = state.get("status", run.get("status", "pending"))

            # Stream newly appended step messages
            if len(steps) > last_step_idx:
                for step in steps[last_step_idx:]:
                    yield f"data: {step}\n\n"
                last_step_idx = len(steps)

            if status_val in {"completed", "failed"}:
                yield f"event: done\ndata: {status_val}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
