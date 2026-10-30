"""
Executive HTML report and CSV spreadsheet download endpoints.
"""
from __future__ import annotations

import io
import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse

from api.dependencies import get_verified_run, get_run_datasets
from database import repository as repo
from services.report_service import generate_html_report, recommendations_to_csv
from services.dataset_storage import load_run_quality_reports
from services.analytics_service import analyze_sales, impute_revenue, impute_category
from agent.schemas import (
    AgentState,
    Recommendation,
    MenuAction,
    Priority,
)

router = APIRouter(prefix="/api/runs", tags=["Reports & Exports"])


def _reconstruct_state_for_report(run_id: int, restaurant_name: str) -> AgentState:
    """Reconstruct an AgentState object from database records and stored datasets."""
    db_recs = repo.list_recommendations(run_id)
    recs: list[Recommendation] = []
    for r in db_recs:
        try:
            recs.append(
                Recommendation(
                    item_id=r.get("item_id"),
                    item_name=r.get("item_name", "Unknown"),
                    action=MenuAction(r.get("action")),
                    priority=Priority(r.get("priority", "medium")),
                    confidence_score=float(r.get("confidence_score") or 0.8),
                    reasoning=r.get("reasoning", ""),
                    alternative_actions=r.get("alternative_actions") or [],
                    expected_benefits=r.get("expected_benefits", ""),
                    potential_risks=r.get("potential_risks", ""),
                    missing_information=r.get("missing_information", ""),
                    next_steps=r.get("next_steps") or [],
                    sales_metrics=r.get("sales_metrics"),
                    review_themes=r.get("review_themes"),
                    profitability=r.get("profitability"),
                    requires_approval=bool(r.get("requires_approval", 1)),
                    success_metrics=r.get("success_metrics", ""),
                )
            )
        except Exception:
            pass

    datasets = get_run_datasets(run_id)
    sales_df = datasets.get("sales")
    menu_df = datasets.get("menu")
    sales_summary = None
    if sales_df is not None and not sales_df.empty:
        s_df = impute_revenue(sales_df, menu_df)
        s_df = impute_category(s_df, menu_df)
        sales_summary = analyze_sales(s_df, menu_df)

    quality_reports = load_run_quality_reports(run_id)

    state = AgentState(
        run_id=run_id,
        restaurant_name=restaurant_name,
        available_data=[k for k, v in datasets.items() if v is not None],
        quality_reports=quality_reports,
        sales_summary=sales_summary,
        recommendations=recs,
        finished=True,
    )
    return state


@router.get("/{run_id}/reports/html", response_class=HTMLResponse)
def download_html_report(run_id: int, run: dict = Depends(get_verified_run)):
    """Generate and stream a self-contained HTML executive report."""
    restaurant = repo.get_restaurant(run["restaurant_id"])
    rest_name = restaurant["name"] if restaurant else f"Run_{run_id}"

    state = _reconstruct_state_for_report(run_id, rest_name)
    quality_reports = load_run_quality_reports(run_id)

    html_content = generate_html_report(
        restaurant_name=rest_name,
        state=state,
        quality_reports=quality_reports,
    )

    clean_filename = re.sub(r"[^\w\-]", "_", rest_name).strip("_")
    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f'attachment; filename="menumind_{clean_filename}_report.html"'
        },
    )


@router.get("/{run_id}/reports/csv")
def download_recommendations_csv(run_id: int, run: dict = Depends(get_verified_run)):
    """Export all AI menu recommendations to a CSV spreadsheet."""
    restaurant = repo.get_restaurant(run["restaurant_id"])
    rest_name = restaurant["name"] if restaurant else f"Run_{run_id}"

    state = _reconstruct_state_for_report(run_id, rest_name)
    if not state.recommendations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recommendations found for this run. Run AI analysis first.",
        )

    csv_bytes = recommendations_to_csv(state.recommendations)
    clean_filename = re.sub(r"[^\w\-]", "_", rest_name).strip("_")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="menumind_{clean_filename}_recommendations.csv"'
        },
    )
