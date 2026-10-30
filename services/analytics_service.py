"""
Deterministic analytics engine.
All numerical computations happen here — no LLM calls.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from agent.schemas import (
    ItemSalesMetrics,
    SalesAnalysisSummary,
    ProfitabilityMetrics,
)

logger = logging.getLogger(__name__)


# ──────────────────────────── Sales Analytics ────────────────────────────────

def analyze_sales(
    sales_df: pd.DataFrame,
    menu_df: Optional[pd.DataFrame] = None,
) -> SalesAnalysisSummary:
    """
    Compute complete sales analytics from a cleaned sales DataFrame.
    """
    warnings: list[str] = []
    df = sales_df.copy()

    # Guard
    for col in ("quantity_sold", "revenue"):
        if col not in df.columns:
            warnings.append(f"Column '{col}' missing — analysis limited.")

    qty_col = "quantity_sold" if "quantity_sold" in df.columns else None
    rev_col = "revenue" if "revenue" in df.columns else None

    # Period
    period_start = period_end = None
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not dates.empty:
            period_start = str(dates.min().date())
            period_end = str(dates.max().date())

    qty_col = "quantity_sold" if "quantity_sold" in df.columns else None
    rev_col = "revenue" if "revenue" in df.columns else None

    # Resolve dish names and prices from menu_df if available
    id_to_name: dict[str, str] = {}
    id_to_cat: dict[str, str] = {}
    name_to_cat: dict[str, str] = {}
    id_to_price: dict[str, float] = {}
    name_to_price: dict[str, float] = {}

    if menu_df is not None and not menu_df.empty:
        if "item_id" in menu_df.columns and "item_name" in menu_df.columns:
            id_to_name = dict(zip(menu_df["item_id"].astype(str), menu_df["item_name"].astype(str)))
        if "item_id" in menu_df.columns and "category" in menu_df.columns:
            id_to_cat = dict(zip(menu_df["item_id"].astype(str), menu_df["category"].astype(str)))
        if "item_name" in menu_df.columns and "category" in menu_df.columns:
            name_to_cat = dict(zip(menu_df["item_name"].astype(str), menu_df["category"].astype(str)))
        if "price" in menu_df.columns:
            prices = pd.to_numeric(menu_df["price"], errors="coerce")
            if "item_id" in menu_df.columns:
                id_to_price = dict(zip(menu_df["item_id"].astype(str), prices))
            if "item_name" in menu_df.columns:
                name_to_price = dict(zip(menu_df["item_name"].astype(str), prices))

    # Name column to group on — prefer resolved menu item_name over raw item_id
    if "_matched_menu_name" in df.columns and df["_matched_menu_name"].notna().any():
        name_col = "_matched_menu_name"
    elif "item_name" in df.columns and df["item_name"].notna().any():
        name_col = "item_name"
    elif "item_id" in df.columns:
        if id_to_name:
            df["_matched_menu_name"] = df["item_id"].astype(str).map(id_to_name).fillna(df["item_id"].astype(str))
            name_col = "_matched_menu_name"
        else:
            name_col = "item_id"
    else:
        name_col = None

    if name_col is None:
        return SalesAnalysisSummary(
            total_revenue=0.0,
            total_units=0,
            item_count=0,
            warnings=["Cannot identify items in sales data."],
        )

    # Impute missing or empty revenue column using quantity_sold × selling_price
    if (rev_col is None or df[rev_col].isna().all()) and qty_col is not None:
        unit_prices = None
        if "item_id" in df.columns and id_to_price:
            unit_prices = df["item_id"].astype(str).map(id_to_price)
        elif name_col in df.columns and name_to_price:
            unit_prices = df[name_col].astype(str).map(name_to_price)
        if unit_prices is not None and unit_prices.notna().any():
            df["revenue"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) * unit_prices.fillna(0)
            rev_col = "revenue"

    # Guard
    if qty_col is None:
        warnings.append("Column 'quantity_sold' missing — analysis limited.")
    if rev_col is None:
        warnings.append("Column 'revenue' missing and could not be calculated from menu prices.")

    # Totals (positive only to avoid voiding all sales)
    pos = df.copy()
    if rev_col and rev_col in pos.columns:
        pos_rev = pd.to_numeric(pos[rev_col], errors="coerce").fillna(0)
        total_revenue = float(pos_rev.where(pos_rev > 0, 0).sum())
    else:
        total_revenue = 0.0

    if qty_col and qty_col in pos.columns:
        pos_qty = pd.to_numeric(pos[qty_col], errors="coerce").fillna(0)
        total_units = int(pos_qty.where(pos_qty > 0, 0).sum())
    else:
        total_units = 0

    # Per-item aggregation
    agg: dict[str, str] = {}
    if qty_col and qty_col in df.columns:
        agg[qty_col] = "sum"
    if rev_col and rev_col in df.columns:
        agg[rev_col] = "sum"
    if "price" in df.columns:
        agg["price"] = "mean"

    grouped = df.groupby(name_col, dropna=False).agg(agg).reset_index()

    # Reconstruct id_map and category_map
    name_to_id: dict[str, str] = {}
    if menu_df is not None and not menu_df.empty:
        if "item_id" in menu_df.columns and "item_name" in menu_df.columns:
            name_to_id = dict(zip(menu_df["item_name"].astype(str), menu_df["item_id"].astype(str)))

    items: list[ItemSalesMetrics] = []
    for _, row in grouped.iterrows():
        name = str(row[name_col]) if pd.notna(row[name_col]) else "Unknown"
        qty = int(row[qty_col]) if qty_col and qty_col in row.index and not pd.isna(row.get(qty_col)) else 0
        rev = float(row[rev_col]) if rev_col and rev_col in row.index and not pd.isna(row.get(rev_col)) else 0.0
        avg_p = float(row["price"]) if "price" in row.index and not pd.isna(row.get("price")) else None
        if avg_p is None:
            avg_p = name_to_price.get(name)

        # Resolve category
        cat = name_to_cat.get(name) or id_to_cat.get(name_to_id.get(name, ""))
        if not cat and "category" in df.columns:
            matching_cats = df.loc[df[name_col] == name, "category"].dropna()
            if not matching_cats.empty:
                cat = str(matching_cats.iloc[0])

        items.append(
            ItemSalesMetrics(
                item_id=name_to_id.get(name),
                item_name=name,
                category=cat,
                total_quantity=qty,
                total_revenue=rev,
                avg_price=avg_p,
                data_points=int(df[df[name_col] == row[name_col]].shape[0]),
            )
        )

    # Revenue contribution & rank
    if total_revenue > 0 and items:
        for item in items:
            item.revenue_contribution_pct = round(item.total_revenue / total_revenue * 100, 2)
        for rank, item in enumerate(
            sorted(items, key=lambda x: x.total_revenue, reverse=True), start=1
        ):
            item.sales_rank = rank

    # Trend: compare first-half vs second-half of date range
    if "date" in df.columns and period_start and period_end:
        _add_trends(df, items, name_col, qty_col, rev_col)

    # Category summary
    category_summary: dict[str, dict] = {}
    for item in items:
        cat = item.category or "Uncategorised"
        if cat not in category_summary:
            category_summary[cat] = {"revenue": 0.0, "quantity": 0, "item_count": 0}
        category_summary[cat]["revenue"] += item.total_revenue
        category_summary[cat]["quantity"] += item.total_quantity
        category_summary[cat]["item_count"] += 1

    sorted_items = sorted(items, key=lambda x: x.total_revenue, reverse=True)
    top_items = sorted_items[:10]
    weak_items = sorted_items[-10:][::-1]

    return SalesAnalysisSummary(
        total_revenue=round(total_revenue, 2),
        total_units=total_units,
        item_count=len(items),
        period_start=period_start,
        period_end=period_end,
        top_items=top_items,
        weak_items=weak_items,
        category_summary=category_summary,
        warnings=warnings,
    )


def _add_trends(df, items, name_col, qty_col, rev_col):
    """Tag each item with a growth trend by comparing first vs second half of dates."""
    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"], errors="coerce")
    midpoint = df["_date"].median()
    if pd.isna(midpoint):
        return
    first_half = df[df["_date"] <= midpoint]
    second_half = df[df["_date"] > midpoint]

    for item in items:
        mask1 = first_half[name_col] == item.item_name
        mask2 = second_half[name_col] == item.item_name
        if qty_col:
            q1 = first_half.loc[mask1, qty_col].sum()
            q2 = second_half.loc[mask2, qty_col].sum()
        else:
            q1 = first_half.loc[mask1, rev_col].sum() if rev_col else 0
            q2 = second_half.loc[mask2, rev_col].sum() if rev_col else 0

        if q1 == 0 and q2 == 0:
            item.period_trend = "no_data"
        elif q1 == 0:
            item.period_trend = "new"
        elif q2 > q1 * 1.1:
            item.period_trend = "growing"
        elif q2 < q1 * 0.9:
            item.period_trend = "declining"
        else:
            item.period_trend = "stable"


# ──────────────────────────── Profitability ──────────────────────────────────

def calculate_profitability(
    menu_df: pd.DataFrame,
    costs_df: Optional[pd.DataFrame],
    sales_summary: Optional[SalesAnalysisSummary] = None,
) -> list[ProfitabilityMetrics]:
    """
    Calculate contribution margin per item.
    Returns one ProfitabilityMetrics per menu item.
    """
    results: list[ProfitabilityMetrics] = []

    if menu_df is None or menu_df.empty:
        return results

    # Build cost lookup
    cost_by_id: dict[str, dict] = {}
    cost_by_name: dict[str, dict] = {}
    if costs_df is not None and not costs_df.empty:
        for _, row in costs_df.iterrows():
            entry = {
                "ingredient_cost": row.get("ingredient_cost"),
                "packaging_cost": row.get("packaging_cost"),
            }
            if "item_id" in row.index and not pd.isna(row.get("item_id")):
                cost_by_id[str(row["item_id"])] = entry
            if "item_name" in row.index and not pd.isna(row.get("item_name")):
                cost_by_name[str(row["item_name"])] = entry

    for _, row in menu_df.iterrows():
        item_id = str(row.get("item_id", "")) if not pd.isna(row.get("item_id", "")) else None
        item_name = str(row.get("item_name", "Unknown"))
        price = row.get("price")
        if pd.isna(price):
            price = None

        # Find costs
        cost_entry = (
            cost_by_id.get(item_id or "")
            or cost_by_name.get(item_name)
        )

        if cost_entry is None:
            results.append(
                ProfitabilityMetrics(
                    item_id=item_id,
                    item_name=item_name,
                    selling_price=price,
                    calculable=False,
                    limitation_note="No cost data available for this item.",
                )
            )
            continue

        ing_cost = cost_entry.get("ingredient_cost")
        pack_cost = cost_entry.get("packaging_cost") or 0.0

        if pd.isna(ing_cost) or ing_cost is None:
            results.append(
                ProfitabilityMetrics(
                    item_id=item_id,
                    item_name=item_name,
                    selling_price=price,
                    packaging_cost=pack_cost if not pd.isna(pack_cost) else None,
                    calculable=False,
                    limitation_note="Ingredient cost is missing.",
                )
            )
            continue

        total_cost = float(ing_cost) + float(pack_cost)
        margin = (float(price) - total_cost) if price is not None else None
        margin_pct = (margin / float(price) * 100) if (margin is not None and price) else None

        results.append(
            ProfitabilityMetrics(
                item_id=item_id,
                item_name=item_name,
                selling_price=price,
                ingredient_cost=float(ing_cost),
                packaging_cost=float(pack_cost),
                total_cost=total_cost,
                contribution_margin=round(margin, 4) if margin is not None else None,
                margin_pct=round(margin_pct, 2) if margin_pct is not None else None,
                calculable=True,
            )
        )

    return results


# ──────────────────────────── Menu Analytics ─────────────────────────────────

def analyze_menu(menu_df: pd.DataFrame) -> dict:
    """Return a summary dict of menu-level statistics."""
    if menu_df is None or menu_df.empty:
        return {"error": "No menu data"}

    result: dict = {
        "total_items": len(menu_df),
        "categories": {},
        "price_stats": {},
        "missing_descriptions": 0,
        "missing_prices": 0,
    }

    if "price" in menu_df.columns:
        prices = menu_df["price"].dropna()
        if not prices.empty:
            result["price_stats"] = {
                "min": round(float(prices.min()), 2),
                "max": round(float(prices.max()), 2),
                "mean": round(float(prices.mean()), 2),
                "median": round(float(prices.median()), 2),
            }
        result["missing_prices"] = int(menu_df["price"].isna().sum())

    if "description" in menu_df.columns:
        result["missing_descriptions"] = int(
            menu_df["description"].isna().sum()
            + (menu_df["description"].astype(str).str.strip() == "").sum()
        )

    if "category" in menu_df.columns:
        cat_counts = menu_df["category"].fillna("Uncategorised").value_counts()
        result["categories"] = cat_counts.to_dict()

    return result


def impute_revenue(sales_df: pd.DataFrame, menu_df: pd.DataFrame | None) -> pd.DataFrame:
    """
    If sales_df has no revenue column but has quantity_sold, compute revenue
    by joining against menu prices via item_name or item_id.
    Returns a copy of sales_df with a populated 'revenue' column.
    """
    df = sales_df.copy()
    if "revenue" in df.columns:
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
        if df["revenue"].notna().any():
            return df

    if menu_df is None or "price" not in menu_df.columns:
        return df

    menu = menu_df.copy()
    menu["price"] = pd.to_numeric(menu["price"], errors="coerce")

    price_by_name: dict[str, float] = {}
    price_by_id: dict[str, float] = {}
    if "item_name" in menu.columns:
        price_by_name = {
            str(n).strip().lower(): p
            for n, p in zip(menu["item_name"], menu["price"])
            if pd.notna(p)
        }
    if "item_id" in menu.columns:
        price_by_id = {
            str(i).strip(): p
            for i, p in zip(menu["item_id"], menu["price"])
            if pd.notna(p)
        }

    def _get_price(row) -> float:
        name_col = "_matched_menu_name" if "_matched_menu_name" in row.index else (
            "item_name" if "item_name" in row.index else None
        )
        if name_col:
            key = str(row.get(name_col, "")).strip().lower()
            if key in price_by_name:
                return price_by_name[key]
        if "item_id" in row.index:
            key = str(row.get("item_id", "")).strip()
            if key in price_by_id:
                return price_by_id[key]
        return float("nan")

    qty = pd.to_numeric(df.get("quantity_sold", pd.Series(dtype=float)), errors="coerce")
    prices = df.apply(_get_price, axis=1)
    df["revenue"] = qty * prices
    return df


def impute_category(sales_df: pd.DataFrame, menu_df: pd.DataFrame | None) -> pd.DataFrame:
    """Attach category to sales rows if missing, so charts don't show all-Uncategorised."""
    df = sales_df.copy()
    if menu_df is None or "category" not in menu_df.columns:
        return df

    cat_by_name: dict[str, str] = {}
    cat_by_id: dict[str, str] = {}
    if "item_name" in menu_df.columns:
        cat_by_name = {
            str(n).strip().lower(): str(c)
            for n, c in zip(menu_df["item_name"], menu_df["category"])
            if pd.notna(c)
        }
    if "item_id" in menu_df.columns:
        cat_by_id = {
            str(i).strip(): str(c)
            for i, c in zip(menu_df["item_id"], menu_df["category"])
            if pd.notna(c)
        }

    def _get_cat(row) -> str:
        name_col = "_matched_menu_name" if "_matched_menu_name" in row.index else (
            "item_name" if "item_name" in row.index else None
        )
        if name_col:
            key = str(row.get(name_col, "")).strip().lower()
            if key in cat_by_name:
                return cat_by_name[key]
        if "item_id" in row.index:
            key = str(row.get("item_id", "")).strip()
            if key in cat_by_id:
                return cat_by_id[key]
        return "Other"

    if "category" not in df.columns or df["category"].isna().all():
        df["category"] = df.apply(_get_cat, axis=1)

    return df
