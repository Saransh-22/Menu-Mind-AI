"""
Data ingestion — reads uploaded CSVs/Excel files, maps columns,
validates schemas and returns clean DataFrames.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ──────────────────────────── Column Alias Maps ──────────────────────────────

MENU_ALIASES: dict[str, list[str]] = {
    "restaurant_id": ["restaurant_id", "rest_id", "restaurant"],
    "item_id":       ["item_id", "id", "sku", "product_id"],
    "item_name":     ["item_name", "name", "dish", "product", "menu_item", "item"],
    "category":      ["category", "cat", "section", "type", "group"],
    "description":   ["description", "desc", "details", "about"],
    "price":         ["price", "selling_price", "unit_price", "cost", "amount"],
}

SALES_ALIASES: dict[str, list[str]] = {
    "restaurant_id":  ["restaurant_id", "rest_id", "restaurant"],
    "item_id":        ["item_id", "id", "sku", "product_id"],
    "date":           ["date", "order_date", "sale_date", "transaction_date", "day"],
    "quantity_sold":  ["quantity_sold", "quantity", "qty", "units", "count", "sold"],
    "revenue":        ["revenue", "total", "amount", "sales", "gross"],
    "discount":       ["discount", "disc", "promotion", "promo"],
    "transaction_id": ["transaction_id", "txn_id", "order_id", "receipt_id"],
}

REVIEW_ALIASES: dict[str, list[str]] = {
    "restaurant_id": ["restaurant_id", "rest_id", "restaurant"],
    "review_id":     ["review_id", "id", "review_number"],
    "item_name":     ["item_name", "dish", "product", "menu_item", "item"],
    "rating":        ["rating", "score", "stars", "grade"],
    "review_text":   ["review_text", "text", "review", "comment", "feedback", "body"],
    "review_date":   ["review_date", "date", "posted_at", "created_at"],
    "source":        ["source", "platform", "origin"],
    "source_url":    ["source_url", "url", "link"],
}

COSTS_ALIASES: dict[str, list[str]] = {
    "restaurant_id":   ["restaurant_id", "rest_id", "restaurant"],
    "item_id":         ["item_id", "id", "sku"],
    "ingredient_cost": ["ingredient_cost", "food_cost", "cogs", "cost_of_goods",
                        "ingredient", "material_cost"],
    "packaging_cost":  ["packaging_cost", "packaging", "pack_cost"],
}


def _normalize_col(col: str) -> str:
    """Lowercase + strip + replace spaces/hyphens with underscores."""
    return re.sub(r"[\s\-]+", "_", col.strip().lower())


def map_columns(df: pd.DataFrame, alias_map: dict[str, list[str]]) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Rename DataFrame columns to canonical names using the alias map.
    Returns (renamed_df, mapping_used).
    Unrecognised columns are kept as-is.
    """
    norm = {_normalize_col(c): c for c in df.columns}
    rename: dict[str, str] = {}
    mapping_used: dict[str, str] = {}

    for canonical, aliases in alias_map.items():
        for alias in aliases:
            alias_norm = _normalize_col(alias)
            if alias_norm in norm:
                original = norm[alias_norm]
                if original not in rename:
                    rename[original] = canonical
                    mapping_used[canonical] = original
                break

    return df.rename(columns=rename), mapping_used


def load_dataframe(source: bytes | str | Path, filename: str = "") -> pd.DataFrame:
    """Load CSV or Excel into a raw DataFrame."""
    ext = Path(filename).suffix.lower() if filename else ""
    if isinstance(source, (str, Path)):
        ext = Path(source).suffix.lower()
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(source, dtype=str)
        return pd.read_csv(source, dtype=str)
    # bytes
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(io.BytesIO(source), dtype=str)
    # default csv
    try:
        return pd.read_csv(io.BytesIO(source), dtype=str)
    except Exception:
        return pd.read_csv(io.StringIO(source.decode("utf-8", errors="replace")), dtype=str)


def ingest_menu(source: bytes | str | Path, filename: str = "") -> tuple[pd.DataFrame, dict, list[str]]:
    """
    Load and column-map a menu file.
    Returns (df, column_mapping, warnings).
    Required columns: item_name, price.
    """
    df = load_dataframe(source, filename)
    df, mapping = map_columns(df, MENU_ALIASES)
    warnings = []
    if "item_name" not in df.columns:
        warnings.append("CRITICAL: 'item_name' column not found or could not be mapped.")
    if "price" not in df.columns:
        warnings.append("WARNING: 'price' column not found — profitability analysis unavailable.")
    return df, mapping, warnings


def ingest_sales(source: bytes | str | Path, filename: str = "") -> tuple[pd.DataFrame, dict, list[str]]:
    """
    Load and column-map a sales file.
    Returns (df, column_mapping, warnings).
    Required columns: item_id or item_name, date, quantity_sold.
    If revenue is missing, it will be computed from menu price.
    """
    df = load_dataframe(source, filename)
    df, mapping = map_columns(df, SALES_ALIASES)
    warnings = []
    has_id = "item_id" in df.columns
    has_name = "item_name" in df.columns
    if not has_id and not has_name:
        warnings.append("CRITICAL: Neither 'item_id' nor 'item_name' found in sales file.")
    for col in ("date", "quantity_sold"):
        if col not in df.columns:
            warnings.append(f"CRITICAL: Required column '{col}' missing from sales file.")
    if "revenue" not in df.columns:
        warnings.append("NOTE: 'revenue' column missing — will be computed as quantity_sold × menu selling price.")
    return df, mapping, warnings


def ingest_reviews(source: bytes | str | Path, filename: str = "") -> tuple[pd.DataFrame, dict, list[str]]:
    df = load_dataframe(source, filename)
    df, mapping = map_columns(df, REVIEW_ALIASES)
    warnings = []
    if "review_text" not in df.columns:
        warnings.append("CRITICAL: 'review_text' column not found.")
    return df, mapping, warnings


def ingest_costs(source: bytes | str | Path, filename: str = "") -> tuple[pd.DataFrame, dict, list[str]]:
    df = load_dataframe(source, filename)
    df, mapping = map_columns(df, COSTS_ALIASES)
    warnings = []
    if "ingredient_cost" not in df.columns:
        warnings.append("WARNING: 'ingredient_cost' column not found — margin analysis unavailable.")
    return df, mapping, warnings


def validate_cross_dataset_integrity(
    menu_df: Optional[pd.DataFrame],
    sales_df: Optional[pd.DataFrame],
    costs_df: Optional[pd.DataFrame] = None,
    reviews_df: Optional[pd.DataFrame] = None,
) -> tuple[bool, list[str], list[str]]:
    """
    Validates cross-dataset schemas, column types, and foreign key relationships.
    Returns: (is_valid, error_list, warning_list).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Menu validation
    if menu_df is None or menu_df.empty:
        errors.append("Menu dataset is required but missing or empty.")
    else:
        if "item_name" not in menu_df.columns:
            errors.append("Menu dataset must contain an 'item_name' column.")
        if "price" not in menu_df.columns:
            warnings.append("Menu dataset has no 'price' column; revenue & margins will be limited.")
        if "item_id" in menu_df.columns:
            dup_ids = menu_df["item_id"].dropna()
            dup_count = int(dup_ids.duplicated().sum())
            if dup_count > 0:
                warnings.append(f"Menu has {dup_count} duplicate item_id entries.")

    # 2. Sales validation
    if sales_df is None or sales_df.empty:
        errors.append("Sales dataset is required but missing or empty.")
    else:
        if "date" not in sales_df.columns:
            errors.append("Sales dataset must contain a 'date' column.")
        if "quantity_sold" not in sales_df.columns:
            errors.append("Sales dataset must contain a 'quantity_sold' column.")
        has_sales_id = "item_id" in sales_df.columns
        has_sales_name = "item_name" in sales_df.columns
        if not has_sales_id and not has_sales_name:
            errors.append("Sales dataset must contain either 'item_id' or 'item_name'.")

        # Cross-validation with menu
        if menu_df is not None and not menu_df.empty:
            if has_sales_id and "item_id" in menu_df.columns:
                sales_ids = set(sales_df["item_id"].dropna().astype(str))
                menu_ids = set(menu_df["item_id"].dropna().astype(str))
                unmatched_ids = sales_ids - menu_ids
                if unmatched_ids:
                    sample = list(unmatched_ids)[:3]
                    warnings.append(
                        f"Sales contains {len(unmatched_ids)} item IDs not found in Menu (e.g. {sample})."
                    )
            elif has_sales_name and "item_name" in menu_df.columns:
                sales_names = set(sales_df["item_name"].dropna().astype(str).str.strip().str.lower())
                menu_names = set(menu_df["item_name"].dropna().astype(str).str.strip().str.lower())
                unmatched_names = sales_names - menu_names
                if unmatched_names:
                    sample = list(unmatched_names)[:3]
                    warnings.append(
                        f"Sales contains {len(unmatched_names)} item names not matched to Menu (e.g. {sample})."
                    )

    # 3. Costs validation (optional)
    if costs_df is not None and not costs_df.empty:
        if "ingredient_cost" not in costs_df.columns:
            warnings.append("Costs dataset is missing 'ingredient_cost' column.")
        if menu_df is not None and not menu_df.empty and "item_id" in costs_df.columns and "item_id" in menu_df.columns:
            cost_ids = set(costs_df["item_id"].dropna().astype(str))
            menu_ids = set(menu_df["item_id"].dropna().astype(str))
            unmatched_cost_ids = cost_ids - menu_ids
            if unmatched_cost_ids:
                warnings.append(f"Costs contains {len(unmatched_cost_ids)} item IDs not found in Menu.")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
