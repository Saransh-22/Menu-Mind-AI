"""
Analysis run management routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from api.schemas import AnalysisRunOut
from api.dependencies import get_verified_run
from database import repository as repo
from services.dataset_storage import list_run_datasets

router = APIRouter(prefix="/api/runs", tags=["Analysis Runs"])


@router.get("/{run_id}", response_model=AnalysisRunOut)
def get_run_details(run: dict = Depends(get_verified_run)):
    """Fetch full analysis run status and dataset presence."""
    datasets = list_run_datasets(run["id"])
    return AnalysisRunOut(**run, datasets=datasets)


@router.get("/{run_id}/status")
def get_run_status(run: dict = Depends(get_verified_run)):
    """Quick polling endpoint for run execution status."""
    return {
        "run_id": run["id"],
        "status": run.get("status", "pending"),
        "data_quality_score": run.get("data_quality_score"),
        "completed_at": run.get("completed_at"),
        "datasets": list_run_datasets(run["id"]),
    }
