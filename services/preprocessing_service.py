"""
Data cleaning, validation and quality reporting.
All mutations operate on copies; originals are preserved.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz, process

from agent.schemas import DataQualityReport
from config.settings import FUZZY_MATCH_THRESHOLD, FUZZY_AUTO_ACCEPT

logger = logging.getLogger(__name__)


# ──────────────────────────── Helpers ────────────────────────────────────────

def _normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def _to_numeric(series: pd.Series, col: str, warnings: list[str]) -> pd.Series:
    converted = pd.to_numeric(series, errors="coerce")
    bad = converted.isna() & series.notna() & (series.astype(str).str.strip() != "")
    if bad.sum() > 0:
        warnings.append(f"Column '{col}': {bad.sum()} non-numeric values coerced to NaN.")
    return converted


def _to_datetime(series: pd.Series, col: str, warnings: list[str]) -> pd.Series:
    converted = pd.to_datetime(series, errors="coerce", dayfirst=False)
    bad = converted.isna() & series.notna() & (series.astype(str).str.strip() != "")
    if bad.sum() > 0:
        warnings.append(f"Column '{col}': {bad.sum()} unparseable date values set to NaT.")
    return converted


# ──────────────────────────── Menu Cleaning ──────────────────────────────────

def clean_menu(df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    warnings: list[str] = []
    errors: list[str] = []
    df = df.copy()
    total = len(df)

    # Normalize text
    if "item_name" in df.columns:
        df["item_name"] = df["item_name"].astype(str).apply(_normalize_text)
    if "description" in df.columns:
        df["description"] = df["description"].astype(str).str.strip()
    if "category" in df.columns:
        df["category"] = df["category"].astype(str).apply(_normalize_text)

    # Numeric
    if "price" in df.columns:
        df["price"] = _to_numeric(df["price"], "price", warnings)
        neg_price = (df["price"] < 0).sum()
        if neg_price:
            warnings.append(f"{neg_price} items have negative price — flagged.")
            df.loc[df["price"] < 0, "price"] = np.nan

    # Deduplicate
    dup_mask = df.duplicated(keep="first")
    dups = int(dup_mask.sum())
    if dups:
        warnings.append(f"{dups} exact duplicate menu rows removed.")
    df = df[~dup_mask].reset_index(drop=True)

    # Missing essential
    missing: dict[str, int] = {}
    for col in df.columns:
        n = int(df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum())
        if n:
            missing[col] = n

    if "item_name" not in df.columns or df["item_name"].str.strip().eq("").all():
        errors.append("No usable item names found in menu file.")

    if "description" in df.columns:
        missing_desc = int(df["description"].isna().sum())
        if missing_desc:
            warnings.append(f"{missing_desc} menu items have no description.")

    accepted = len(df)
    rejected = total - accepted
    score = max(0.0, 1.0 - (rejected / max(total, 1)) - (0.1 * len(errors)))

    report = DataQualityReport(
        file_type="menu",
        total_records=total,
        accepted_records=accepted,
        rejected_records=rejected,
        duplicate_records=dups,
        missing_values=missing,
        warnings=warnings,
        errors=errors,
        quality_score=round(min(max(score, 0.0), 1.0), 3),
    )
    return df, report


# ──────────────────────────── Sales Cleaning ─────────────────────────────────

def clean_sales(df: pd.DataFrame, menu_df: Optional[pd.DataFrame] = None
                ) -> tuple[pd.DataFrame, DataQualityReport, list[dict]]:
    """
    Returns (cleaned_df, report, ambiguous_matches).
    ambiguous_matches: list of {sales_name, candidates} for human review.
    """
    warnings: list[str] = []
    errors: list[str] = []
    df = df.copy()
    total = len(df)

    # Numerics
    for col in ("quantity_sold", "revenue", "discount"):
        if col in df.columns:
            df[col] = _to_numeric(df[col], col, warnings)

    # Date
    if "date" in df.columns:
        df["date"] = _to_datetime(df["date"], "date", warnings)

    # Normalize item names if present
    if "item_name" in df.columns:
        df["item_name"] = df["item_name"].astype(str).apply(_normalize_text)

    # Negative quantities flagged, not auto-removed (could be returns/voids)
    if "quantity_sold" in df.columns:
        neg_qty = (df["quantity_sold"] < 0).sum()
        if neg_qty:
            warnings.append(
                f"{neg_qty} negative quantity_sold rows found (possible returns/voids). "
                "Kept for completeness — verify before aggregating."
            )

    # Deduplicate by transaction_id if available
    dups = 0
    if "transaction_id" in df.columns:
        dup_mask = df.duplicated(subset=["transaction_id"], keep="first")
        dups = int(dup_mask.sum())
        if dups:
            warnings.append(f"{dups} duplicate transaction_ids detected and removed.")
            df = df[~dup_mask].reset_index(drop=True)
    else:
        all_cols = [c for c in ("item_id", "item_name", "date", "quantity_sold", "revenue")
                    if c in df.columns]
        dup_mask = df.duplicated(subset=all_cols, keep="first")
        dups = int(dup_mask.sum())
        if dups:
            warnings.append(f"{dups} exact duplicate sales rows removed.")
            df = df[~dup_mask].reset_index(drop=True)

    # Item matching & metadata resolution from menu
    unmatched: list[str] = []
    ambiguous: list[dict] = []
    if menu_df is not None and not menu_df.empty:
        df["_matched_menu_name"] = None
        df["_match_score"] = 0
        df["_match_type"] = None

        # 1. Match by exact item_id
        if "item_id" in df.columns and "item_id" in menu_df.columns and "item_name" in menu_df.columns:
            id_map = dict(zip(menu_df["item_id"].astype(str), menu_df["item_name"]))
            id_match = df["item_id"].astype(str).map(id_map)
            matched_by_id = id_match.notna()
            df.loc[matched_by_id, "_matched_menu_name"] = id_match[matched_by_id]
            df.loc[matched_by_id, "_match_type"] = "exact_id"
            df.loc[matched_by_id, "_match_score"] = 100
            if "item_name" not in df.columns:
                df["item_name"] = df["_matched_menu_name"]
            else:
                df["item_name"] = df["item_name"].fillna(df["_matched_menu_name"])

        # 2. Attach category from menu if available
        if "category" in menu_df.columns:
            if "item_id" in df.columns and "item_id" in menu_df.columns:
                cat_map_id = dict(zip(menu_df["item_id"].astype(str), menu_df["category"]))
                if "category" not in df.columns:
                    df["category"] = df["item_id"].astype(str).map(cat_map_id)
                else:
                    df["category"] = df["category"].fillna(df["item_id"].astype(str).map(cat_map_id))
            elif "item_name" in menu_df.columns:
                cat_map_name = dict(zip(menu_df["item_name"].astype(str), menu_df["category"]))
                name_source = df["_matched_menu_name"] if "_matched_menu_name" in df.columns else df.get("item_name")
                if name_source is not None:
                    if "category" not in df.columns:
                        df["category"] = name_source.astype(str).map(cat_map_name)
                    else:
                        df["category"] = df["category"].fillna(name_source.astype(str).map(cat_map_name))

        # 3. Fuzzy fallback for remaining unmatched names
        if "item_name" in df.columns and "item_name" in menu_df.columns:
            menu_names = menu_df["item_name"].dropna().unique().tolist()
            unmatched_rows = df[df["_matched_menu_name"].isna()]
            for idx, row in unmatched_rows.iterrows():
                name = row.get("item_name", "")
                if not name or str(name) == "nan":
                    continue
                result = process.extractBests(
                    str(name), menu_names, scorer=fuzz.token_set_ratio, limit=3, score_cutoff=FUZZY_MATCH_THRESHOLD
                )
                if not result:
                    unmatched.append(str(name))
                elif result[0][1] >= FUZZY_AUTO_ACCEPT:
                    df.at[idx, "_matched_menu_name"] = result[0][0]
                    df.at[idx, "_match_score"] = result[0][1]
                    df.at[idx, "_match_type"] = "fuzzy_auto"
                else:
                    ambiguous.append({"sales_name": str(name), "candidates": result})

        # 4. Impute revenue if missing or entirely NaN
        if "quantity_sold" in df.columns and ("revenue" not in df.columns or df["revenue"].isna().all()):
            if "price" in menu_df.columns:
                unit_prices = None
                if "item_id" in df.columns and "item_id" in menu_df.columns:
                    price_map = dict(zip(menu_df["item_id"].astype(str), pd.to_numeric(menu_df["price"], errors="coerce")))
                    unit_prices = df["item_id"].astype(str).map(price_map)
                if (unit_prices is None or unit_prices.isna().all()) and "item_name" in menu_df.columns:
                    name_key = df["_matched_menu_name"] if "_matched_menu_name" in df.columns else df.get("item_name")
                    if name_key is not None:
                        price_map_name = dict(zip(menu_df["item_name"].astype(str), pd.to_numeric(menu_df["price"], errors="coerce")))
                        unit_prices = name_key.astype(str).map(price_map_name)
                if unit_prices is not None and not unit_prices.empty and unit_prices.notna().any():
                    df["revenue"] = df["quantity_sold"] * unit_prices
                    warnings.append("Computed revenue as quantity_sold × menu selling price.")

    missing: dict[str, int] = {}
    for col in df.columns:
        if col.startswith("_"):
            continue
        n = int(df[col].isna().sum())
        if n:
            missing[col] = n

    accepted = len(df)
    rejected = total - accepted
    score = max(0.0, 1.0 - (rejected / max(total, 1)) * 0.5 - (0.05 * len(errors)))

    report = DataQualityReport(
        file_type="sales",
        total_records=total,
        accepted_records=accepted,
        rejected_records=rejected,
        duplicate_records=dups,
        missing_values=missing,
        invalid_records=0,
        unmatched_items=list(set(unmatched)),
        warnings=warnings,
        errors=errors,
        quality_score=round(min(max(score, 0.0), 1.0), 3),
    )
    return df, report, ambiguous


# ──────────────────────────── Reviews Cleaning ───────────────────────────────

def clean_reviews(df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    warnings: list[str] = []
    errors: list[str] = []
    df = df.copy()
    total = len(df)

    if "review_text" in df.columns:
        df["review_text"] = df["review_text"].astype(str).str.strip()
        df = df[df["review_text"].str.len() > 5].reset_index(drop=True)
        dropped = total - len(df)
        if dropped:
            warnings.append(f"{dropped} reviews with very short/empty text excluded.")

    if "rating" in df.columns:
        df["rating"] = _to_numeric(df["rating"], "rating", warnings)

    if "review_date" in df.columns:
        df["review_date"] = _to_datetime(df["review_date"], "review_date", warnings)

    if "item_name" in df.columns:
        df["item_name"] = df["item_name"].astype(str).apply(_normalize_text)
        df["item_name"] = df["item_name"].replace("nan", None)

    # Classify review provenance: uploaded reviews vs external snippets
    if "is_snippet" not in df.columns:
        if "attribution" in df.columns:
            df["is_snippet"] = df["attribution"].astype(str).str.contains("snippet", case=False, na=False)
        elif "source" in df.columns:
            snippet_sources = {"SerpApi Google Search", "Google Custom Search API"}
            df["is_snippet"] = df["source"].astype(str).isin(snippet_sources)
        else:
            df["is_snippet"] = False
    else:
        df["is_snippet"] = df["is_snippet"].astype(bool)

    if "attribution" not in df.columns:
        df["attribution"] = df["is_snippet"].apply(
            lambda s: "SerpApi Google Search snippet" if s else "Uploaded customer review"
        )

    if "review_type" not in df.columns:
        df["review_type"] = df["is_snippet"].apply(
            lambda s: "search_snippet" if s else "verified_customer_review"
        )

    # Deduplicate
    dup_cols = [c for c in ("review_text", "source") if c in df.columns]
    dups = 0
    if dup_cols:
        dup_mask = df.duplicated(subset=dup_cols, keep="first")
        dups = int(dup_mask.sum())
        if dups:
            warnings.append(f"{dups} duplicate reviews removed.")
            df = df[~dup_mask].reset_index(drop=True)

    missing: dict[str, int] = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n:
            missing[col] = n

    accepted = len(df)
    rejected = total - accepted
    score = 1.0 - (max(0, total - accepted) / max(total, 1)) * 0.5

    report = DataQualityReport(
        file_type="reviews",
        total_records=total,
        accepted_records=accepted,
        rejected_records=rejected,
        duplicate_records=dups,
        missing_values=missing,
        warnings=warnings,
        errors=errors,
        quality_score=round(min(max(score, 0.0), 1.0), 3),
    )
    return df, report


# ──────────────────────────── Costs Cleaning ─────────────────────────────────

def clean_costs(df: pd.DataFrame) -> tuple[pd.DataFrame, DataQualityReport]:
    warnings: list[str] = []
    errors: list[str] = []
    df = df.copy()
    total = len(df)

    for col in ("ingredient_cost", "packaging_cost"):
        if col in df.columns:
            df[col] = _to_numeric(df[col], col, warnings)
            neg = (df[col] < 0).sum()
            if neg:
                warnings.append(f"{neg} negative values in '{col}' — set to NaN.")
                df.loc[df[col] < 0, col] = np.nan

    dups = 0
    if "item_id" in df.columns:
        dup_mask = df.duplicated(subset=["item_id"], keep="first")
        dups = int(dup_mask.sum())
        if dups:
            warnings.append(f"{dups} duplicate item_id rows in costs — keeping first.")
            df = df[~dup_mask].reset_index(drop=True)

    missing: dict[str, int] = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n:
            missing[col] = n

    accepted = len(df)
    rejected = total - accepted

    report = DataQualityReport(
        file_type="costs",
        total_records=total,
        accepted_records=accepted,
        rejected_records=rejected,
        duplicate_records=dups,
        missing_values=missing,
        warnings=warnings,
        errors=errors,
        quality_score=round(min(max(1.0 - rejected / max(total, 1), 0.0), 1.0), 3),
    )
    return df, report
