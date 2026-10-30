"""
Restaurant management routes.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from api.schemas import (
    RestaurantCreate,
    RestaurantOut,
    RestaurantSuggestion,
    AnalysisRunCreate,
    AnalysisRunOut,
)
from api.dependencies import get_verified_restaurant
from database import repository as repo
from services.review_retrieval_service import autocomplete_restaurant_name
from services.dataset_storage import list_run_datasets

router = APIRouter(prefix="/api/restaurants", tags=["Restaurants"])


@router.get("", response_model=list[RestaurantOut])
def list_restaurants():
    """List all registered restaurants ordered by creation date."""
    rows = repo.list_restaurants()
    return [RestaurantOut(**r) for r in rows]


@router.post("", response_model=RestaurantOut, status_code=status.HTTP_201_CREATED)
def create_restaurant(payload: RestaurantCreate):
    """Create a new restaurant or return existing with deduplication."""
    rest_id, is_new = repo.get_or_create_restaurant(
        name=payload.name,
        city=payload.city,
        location=payload.location,
        website=payload.website,
        category=payload.category,
    )
    rest = repo.get_restaurant(rest_id)
    return RestaurantOut(**rest, is_new=is_new)


@router.get("/autocomplete", response_model=list[RestaurantSuggestion])
def autocomplete_restaurants(
    query: str = Query(..., min_length=1, description="Search query"),
    city: str = Query(default="", description="Optional city filter"),
    limit: int = Query(default=5, ge=1, le=20),
):
    """Real-time autocomplete search for restaurant names."""
    names = autocomplete_restaurant_name(query=query, city=city, limit=limit)
    return [RestaurantSuggestion(name=n, city=city, source="database") for n in names]


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant: dict = Depends(get_verified_restaurant)):
    """Fetch restaurant profile by ID."""
    return RestaurantOut(**restaurant)


@router.post("/{restaurant_id}/runs", response_model=AnalysisRunOut, status_code=status.HTTP_201_CREATED)
def create_run_for_restaurant(
    payload: AnalysisRunCreate,
    restaurant: dict = Depends(get_verified_restaurant),
):
    """Create a new analysis run for a restaurant."""
    run_id = repo.create_analysis_run(
        restaurant_id=restaurant["id"],
        period_start=payload.period_start,
        period_end=payload.period_end,
        notes=payload.notes,
    )
    run = repo.get_analysis_run(run_id)
    return AnalysisRunOut(**run, datasets=list_run_datasets(run_id))


@router.get("/{restaurant_id}/runs", response_model=list[AnalysisRunOut])
def list_runs_for_restaurant(restaurant: dict = Depends(get_verified_restaurant)):
    """List all analysis runs for a restaurant."""
    runs = repo.list_runs_for_restaurant(restaurant["id"])
    return [
        AnalysisRunOut(**r, datasets=list_run_datasets(r["id"]))
        for r in runs
    ]
