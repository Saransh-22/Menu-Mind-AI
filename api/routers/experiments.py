"""
Menu experiments and outcome tracking routes.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_verified_run
from api.schemas import (
    ExperimentCreate,
    ExperimentStatusUpdate,
    ExperimentResultCreate,
)
from database import repository as repo

router = APIRouter(tags=["Experiments & Outcomes"])


@router.get("/api/runs/{run_id}/experiments")
def list_run_experiments(run_id: int, run: dict = Depends(get_verified_run)):
    """List all menu experiments and their outcome evaluations for this run."""
    experiments = repo.list_experiments(run_id)
    results = []
    for exp in experiments:
        exp_id = exp["id"]
        exp_results = repo.get_experiment_results(exp_id)
        exp_dict = dict(exp)
        exp_dict["results"] = exp_results
        results.append(exp_dict)
    return results


@router.post("/api/runs/{run_id}/experiments", status_code=status.HTTP_201_CREATED)
def create_experiment(
    run_id: int,
    payload: ExperimentCreate,
    run: dict = Depends(get_verified_run),
):
    """Create a new experiment linked to an analysis run and optional recommendation."""
    exp_id = repo.create_experiment(run_id=run_id, data=payload.model_dump())
    experiments = repo.list_experiments(run_id)
    created = next((e for e in experiments if e["id"] == exp_id), None)
    if not created:
        raise HTTPException(status_code=500, detail="Experiment created but could not be retrieved")
    created_dict = dict(created)
    created_dict["results"] = []
    return created_dict


@router.patch("/api/experiments/{experiment_id}/status")
def update_experiment_status(
    experiment_id: int,
    payload: ExperimentStatusUpdate,
):
    """Transition experiment through proposed, approved, active, completed, or cancelled."""
    repo.update_experiment_status(experiment_id=experiment_id, status=payload.status)
    return {"status": payload.status, "experiment_id": experiment_id}


@router.post("/api/experiments/{experiment_id}/results", status_code=status.HTTP_201_CREATED)
def record_experiment_results(
    experiment_id: int,
    payload: list[ExperimentResultCreate],
):
    """Save baseline vs test metrics for an experiment."""
    results_dicts = [r.model_dump() for r in payload]
    repo.save_experiment_result(experiment_id=experiment_id, results=results_dicts)
    return {
        "status": "recorded",
        "experiment_id": experiment_id,
        "results": repo.get_experiment_results(experiment_id),
    }


@router.get("/api/experiments/{experiment_id}/results")
def get_experiment_results(experiment_id: int):
    """Get evaluated metrics and percentage changes for an experiment."""
    return repo.get_experiment_results(experiment_id)
