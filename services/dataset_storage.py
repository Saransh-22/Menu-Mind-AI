"""
Durable run-level dataset persistence using Parquet and JSON files.
Storage location: data/runs/{run_id}/
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from agent.schemas import DataQualityReport

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


def _get_run_dir(run_id: int) -> Path:
    run_dir = DATA_DIR / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_run_dataset(run_id: int, file_type: str, df: pd.DataFrame) -> Path:
    """Save cleaned DataFrame as Parquet for the specified run_id."""
    clean_type = file_type.lower().strip()
    if clean_type not in {"menu", "sales", "reviews", "costs"}:
        raise ValueError(f"Invalid file_type: {file_type}")
    run_dir = _get_run_dir(run_id)
    parquet_path = run_dir / f"{clean_type}.parquet"
    # Ensure all object columns are string-safe for parquet
    df_to_save = df.copy()
    for col in df_to_save.columns:
        if df_to_save[col].dtype == "object":
            df_to_save[col] = df_to_save[col].astype(str)
    df_to_save.to_parquet(parquet_path, index=False)
    logger.info("Persisted %s dataset for run %s at %s", clean_type, run_id, parquet_path)
    return parquet_path


def load_run_dataset(run_id: int, file_type: str) -> Optional[pd.DataFrame]:
    """Load cleaned DataFrame for the specified run_id from Parquet."""
    clean_type = file_type.lower().strip()
    run_dir = DATA_DIR / str(run_id)
    parquet_path = run_dir / f"{clean_type}.parquet"
    if not parquet_path.exists():
        return None
    try:
        df = pd.read_parquet(parquet_path)
        # Restore None for string 'None' / 'nan' in object columns if needed
        return df
    except Exception as exc:
        logger.warning("Failed to load parquet at %s: %s", parquet_path, exc)
        return None


def list_run_datasets(run_id: int) -> dict[str, bool]:
    """Return presence status for all 4 dataset types for a run."""
    run_dir = DATA_DIR / str(run_id)
    return {
        "menu": (run_dir / "menu.parquet").exists(),
        "sales": (run_dir / "sales.parquet").exists(),
        "reviews": (run_dir / "reviews.parquet").exists(),
        "costs": (run_dir / "costs.parquet").exists(),
    }


def save_run_quality_report(run_id: int, file_type: str, report: DataQualityReport) -> None:
    """Persist quality report JSON alongside datasets."""
    run_dir = _get_run_dir(run_id)
    report_path = run_dir / f"{file_type}_quality.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2)


def load_run_quality_reports(run_id: int) -> list[DataQualityReport]:
    """Load all persisted quality reports for a run."""
    run_dir = DATA_DIR / str(run_id)
    reports = []
    if not run_dir.exists():
        return reports
    for p in run_dir.glob("*_quality.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                reports.append(DataQualityReport(**data))
        except Exception as exc:
            logger.warning("Failed reading quality report at %s: %s", p, exc)
    return reports
