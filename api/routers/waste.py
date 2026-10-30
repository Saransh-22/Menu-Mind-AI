"""
Food waste intelligence, Gemini Vision identification, and deterministic spoilage analytics.
"""
from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import get_verified_run, get_run_datasets
from api.schemas import (
    WasteRecordCreate,
    WasteIntelligenceOut,
)
from database import repository as repo
from services.waste_analysis_service import (
    analyze_food_image,
    calculate_waste_cost,
    analyze_spoilage_risk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["Food Waste Intelligence"])


@router.post("/{run_id}/waste/analyze-image")
async def analyze_waste_image(
    run_id: int,
    image: UploadFile = File(...),
    run: dict = Depends(get_verified_run),
):
    """
    Analyze kitchen food-waste image using Gemini Vision to identify visible candidates.
    Never infers exact weight or food safety; candidate items must be confirmed by kitchen staff.
    """
    mime = image.content_type or "image/jpeg"
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG and WEBP images are supported.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image size exceeds the 10 MB limit.",
        )

    try:
        vision_result = analyze_food_image(image_bytes, mime)
        repo.save_waste_image(
            run_id=run_id,
            original_name=image.filename or "waste_image.jpg",
            mime_type=mime,
            detected_items=vision_result.get("items", []),
            limitations=vision_result.get("image_limitations", []),
        )
        return vision_result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(re))
    except Exception as exc:
        logger.exception("Failed image analysis: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Vision analysis failed: {exc}")


@router.get("/{run_id}/waste/summary", response_model=WasteIntelligenceOut)
def get_waste_summary(run_id: int, run: dict = Depends(get_verified_run)):
    """
    Fetch both measured kitchen waste logs and predictive sales velocity-driven spoilage risk.
    Clearly distinguishes physical weigh-ins from estimated risk exposure.
    """
    records = repo.list_waste_records(run_id)
    measured = calculate_waste_cost(records) if records else {
        "total_waste_cost": 0.0,
        "calculable_records": 0,
        "uncalculable_records": 0,
        "by_ingredient": {},
        "limitations": [],
    }

    datasets = get_run_datasets(run_id)
    sales_df = datasets.get("sales")
    menu_df = datasets.get("menu")
    costs_df = datasets.get("costs")

    spoilage = analyze_spoilage_risk(sales_df, menu_df, costs_df)

    return WasteIntelligenceOut(
        measured=measured,
        spoilage=spoilage,
        records=records,
    )


@router.post("/{run_id}/waste/records", status_code=status.HTTP_201_CREATED)
def record_waste_entry(
    run_id: int,
    payload: WasteRecordCreate,
    run: dict = Depends(get_verified_run),
):
    """Save a human-verified kitchen waste log entry with measured quantity and unit cost."""
    record_id = repo.save_waste_record(run_id=run_id, data=payload.model_dump())
    records = repo.list_waste_records(run_id)
    created = next((r for r in records if r["id"] == record_id), None)
    return created or {"id": record_id, **payload.model_dump()}


@router.get("/{run_id}/waste/records")
def list_waste_records(run_id: int, run: dict = Depends(get_verified_run)):
    """List all physical waste entries for an analysis run."""
    return repo.list_waste_records(run_id)
