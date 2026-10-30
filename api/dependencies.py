"""
FastAPI dependency injection and context resolution.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import HTTPException, status

from database import repository as repo
from services.dataset_storage import load_run_dataset

logger = logging.getLogger(__name__)


def get_verified_restaurant(restaurant_id: int) -> dict:
    """Verify that a restaurant exists or raise 404."""
    restaurant = repo.get_restaurant(restaurant_id)
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restaurant with ID {restaurant_id} not found",
        )
    return restaurant


def get_verified_run(run_id: int) -> dict:
    """Verify that an analysis run exists or raise 404."""
    run = repo.get_analysis_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run with ID {run_id} not found",
        )
    return run


def get_run_datasets(run_id: int) -> dict[str, Optional[object]]:
    """Load all available DataFrames for run_id from durable parquet storage."""
    return {
        "menu": load_run_dataset(run_id, "menu"),
        "sales": load_run_dataset(run_id, "sales"),
        "reviews": load_run_dataset(run_id, "reviews"),
        "costs": load_run_dataset(run_id, "costs"),
    }
