"""
Dataset ingestion, file upload, preview and validation routes.
"""
from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import get_verified_run, get_run_datasets
from api.schemas import DataQualityReport, ValidationResult, DatasetPreview
from config.settings import MAX_UPLOAD_SIZE_MB, ALLOWED_EXTENSIONS
from database import repository as repo
from services.ingestion_service import (
    ingest_menu,
    ingest_sales,
    ingest_reviews,
    ingest_costs,
    validate_cross_dataset_integrity,
)
from services.preprocessing_service import (
    clean_menu,
    clean_sales,
    clean_reviews,
    clean_costs,
)
from services.dataset_storage import (
    save_run_dataset,
    load_run_dataset,
    save_run_quality_report,
    load_run_quality_reports,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["Data Ingestion & Quality"])


@router.post("/{run_id}/upload/{file_type}", response_model=DataQualityReport)
async def upload_dataset_file(
    run_id: int,
    file_type: str,
    file: UploadFile = File(...),
    run: dict = Depends(get_verified_run),
):
    """
    Upload, ingest, clean, and persist a CSV or Excel dataset file.
    Validates file extensions, cleans data, records metadata and saves to parquet.
    """
    clean_type = file_type.lower().strip()
    if clean_type not in {"menu", "sales", "reviews", "costs"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file_type: '{file_type}'. Must be one of: menu, sales, reviews, costs",
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read bytes with size limit guard
    contents = await file.read()
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload limit of {MAX_UPLOAD_SIZE_MB}MB",
        )

    filename = file.filename or f"{clean_type}.csv"

    try:
        if clean_type == "menu":
            df_raw, mapping, warnings = ingest_menu(contents, filename)
            df_clean, report = clean_menu(df_raw)
        elif clean_type == "sales":
            df_raw, mapping, warnings = ingest_sales(contents, filename)
            menu_df = load_run_dataset(run_id, "menu")
            df_clean, report, _ = clean_sales(df_raw, menu_df)
        elif clean_type == "reviews":
            df_raw, mapping, warnings = ingest_reviews(contents, filename)
            df_clean, report = clean_reviews(df_raw)
        elif clean_type == "costs":
            df_raw, mapping, warnings = ingest_costs(contents, filename)
            df_clean, report = clean_costs(df_raw)

        # Save to durable parquet storage
        save_run_dataset(run_id, clean_type, df_clean)
        save_run_quality_report(run_id, clean_type, report)

        # Record in SQLite database data_files table
        repo.record_data_file(
            run_id=run_id,
            file_type=clean_type,
            original_name=filename,
            row_count=report.total_records,
            accepted_rows=report.accepted_records,
            rejected_rows=report.rejected_records,
        )

        # Update run's average data quality score in DB
        all_reports = load_run_quality_reports(run_id)
        if all_reports:
            avg_score = sum(r.quality_score for r in all_reports) / len(all_reports)
            repo.update_run_status(run_id, run.get("status", "pending"), avg_score)

        return report

    except Exception as exc:
        logger.exception("Failed processing uploaded %s file: %s", clean_type, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error parsing {clean_type} file: {str(exc)}",
        )


@router.get("/{run_id}/validate", response_model=ValidationResult)
def validate_datasets(run_id: int, run: dict = Depends(get_verified_run)):
    """Run cross-dataset schema and foreign-key integrity checks."""
    datasets = get_run_datasets(run_id)
    menu_df = datasets.get("menu")
    sales_df = datasets.get("sales")
    costs_df = datasets.get("costs")
    reviews_df = datasets.get("reviews")

    is_valid, errors, warnings = validate_cross_dataset_integrity(
        menu_df=menu_df,
        sales_df=sales_df,
        costs_df=costs_df,
        reviews_df=reviews_df,
    )
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


@router.get("/{run_id}/datasets/{file_type}/preview", response_model=DatasetPreview)
def preview_dataset(
    run_id: int,
    file_type: str,
    limit: int = 25,
    run: dict = Depends(get_verified_run),
):
    """Return top rows of cleaned dataset for data table preview."""
    clean_type = file_type.lower().strip()
    df = load_run_dataset(run_id, clean_type)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No dataset found for '{clean_type}' in run #{run_id}",
        )
    # Filter internal underscore columns for clean preview
    preview_df = df[[c for c in df.columns if not c.startswith("_")]].head(limit)
    # Replace NaN with None for valid JSON serialization
    rows = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")
    return DatasetPreview(
        file_type=clean_type,
        columns=list(preview_df.columns),
        total_rows=len(df),
        rows=rows,
    )


@router.get("/{run_id}/quality-reports", response_model=list[DataQualityReport])
def get_quality_reports(run_id: int, run: dict = Depends(get_verified_run)):
    """Return all data quality reports for this analysis run."""
    return load_run_quality_reports(run_id)
