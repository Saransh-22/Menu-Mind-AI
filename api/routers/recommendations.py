"""
Recommendation listing and human-in-the-loop approval workflow routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_verified_run
from api.schemas import (
    RecommendationWithApproval,
    ApprovalCreate,
    ApprovalOut,
)
from database import repository as repo

router = APIRouter(tags=["Recommendations & Approvals"])


@router.get("/api/runs/{run_id}/recommendations", response_model=list[RecommendationWithApproval])
def list_run_recommendations(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch all recommendations generated for this run along with approval decisions."""
    db_recs = repo.list_recommendations(run_id)
    results = []
    for r in db_recs:
        rec_id = r["id"]
        approval = repo.get_approval(rec_id)
        results.append(
            RecommendationWithApproval(
                **r,
                approval=ApprovalOut(**approval) if approval else None,
            )
        )
    return results


@router.post("/api/recommendations/{recommendation_id}/approval", response_model=ApprovalOut)
def record_recommendation_approval(
    recommendation_id: int,
    payload: ApprovalCreate,
):
    """Save an approval decision (approved, rejected, or saved_for_later) for an item."""
    approval_id = repo.save_approval(
        recommendation_id=recommendation_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    saved = repo.get_approval(recommendation_id)
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved approval decision",
        )
    return ApprovalOut(**saved)


@router.get("/api/recommendations/{recommendation_id}/approval", response_model=ApprovalOut)
def get_recommendation_approval(recommendation_id: int):
    """Retrieve the current approval status for a recommendation."""
    approval = repo.get_approval(recommendation_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No approval record found for recommendation #{recommendation_id}",
        )
    return ApprovalOut(**approval)
