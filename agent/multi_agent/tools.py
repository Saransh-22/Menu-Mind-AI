"""
Data-grounded Tool Execution Layer for MenuMind AI Multi-Agent System.
Connects agents to real database records, Parquet datasets, and analytics services.
Never fabricates metrics, mixes restaurant runs, or conceals missing data.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from database import repository as repo
from services.dataset_storage import load_run_dataset
from services.analytics_service import analyze_sales, calculate_profitability, impute_revenue, impute_category
from services.sentiment_service import analyze_sentiment_local, extract_item_review_insights
from services.waste_analysis_service import calculate_waste_cost, analyze_spoilage_risk

logger = logging.getLogger(__name__)


def _find_qty_col(df: pd.DataFrame) -> str:
    for col in ["quantity_sold", "quantity", "units_sold", "qty", "count"]:
        if col in df.columns:
            return col
    return "quantity"


def get_restaurant_overview(restaurant_id: int, run_id: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve verified restaurant profile and data availability for active run."""
    restaurant = repo.get_restaurant(restaurant_id)
    if not restaurant:
        return {"error": f"Restaurant #{restaurant_id} not found."}

    available_data = []
    dataset_counts = {}
    if run_id:
        for dtype in ["menu", "sales", "reviews", "costs"]:
            df = load_run_dataset(run_id, dtype)
            if df is not None and not df.empty:
                available_data.append(dtype)
                dataset_counts[dtype] = len(df)
            else:
                dataset_counts[dtype] = 0

    waste_records = repo.list_waste_records(run_id) if run_id else []

    return {
        "restaurant_id": restaurant_id,
        "name": restaurant.get("name"),
        "city": restaurant.get("city"),
        "category": restaurant.get("category"),
        "active_run_id": run_id,
        "available_datasets": available_data,
        "dataset_row_counts": dataset_counts,
        "waste_records_logged": len(waste_records),
    }


def get_top_selling_items(run_id: int, limit: int = 5, by: str = "quantity") -> Dict[str, Any]:
    """
    Retrieve top selling dishes for an active run.
    Distinguishes volume leaders (units sold) from revenue leaders (total INR).
    """
    sales_df = load_run_dataset(run_id, "sales")
    menu_df = load_run_dataset(run_id, "menu")
    if sales_df is None or sales_df.empty:
        return {
            "error": "No sales transaction records uploaded for this analysis run.",
            "run_id": run_id,
            "has_data": False,
        }

    sales = impute_revenue(sales_df, menu_df)
    qty_col = _find_qty_col(sales)

    # 1. Volume rankings
    vol_grouped = sales.groupby("item_name")[qty_col].sum().sort_values(ascending=False)
    vol_leaders = [
        {"item_name": item, "units_sold": int(qty)}
        for item, qty in vol_grouped.head(limit).items()
    ]

    # 2. Revenue rankings
    rev_grouped = sales.groupby("item_name")["revenue"].sum().sort_values(ascending=False)
    rev_leaders = [
        {"item_name": item, "revenue": round(float(rev), 2)}
        for item, rev in rev_grouped.head(limit).items()
    ]

    top_volume_item = vol_leaders[0] if vol_leaders else None
    top_revenue_item = rev_leaders[0] if rev_leaders else None

    # Check if volume leader is also revenue leader
    same_leader = bool(
        top_volume_item and top_revenue_item and
        top_volume_item["item_name"].lower() == top_revenue_item["item_name"].lower()
    )

    return {
        "run_id": run_id,
        "has_data": True,
        "primary_ranking_criterion": by,
        "volume_leader": top_volume_item,
        "revenue_leader": top_revenue_item,
        "volume_and_revenue_same": same_leader,
        "top_by_volume": vol_leaders,
        "top_by_revenue": rev_leaders,
        "total_dishes_with_sales": len(vol_grouped),
    }


def get_item_sales_details(run_id: int, item_name: str) -> Dict[str, Any]:
    """Retrieve detailed sales performance metrics for a specific dish."""
    sales_df = load_run_dataset(run_id, "sales")
    menu_df = load_run_dataset(run_id, "menu")
    if sales_df is None or sales_df.empty:
        return {"error": "No sales transactions available.", "item_name": item_name, "found": False}

    sales = impute_revenue(sales_df, menu_df)
    sales = impute_category(sales, menu_df)
    qty_col = _find_qty_col(sales)

    # Match dish case-insensitively or via substring
    clean_target = item_name.strip().lower()
    mask = sales["item_name"].astype(str).str.lower().str.contains(clean_target, regex=False)
    matched = sales[mask]

    if matched.empty:
        return {
            "item_name": item_name,
            "found": False,
            "message": f"No sales transactions found matching '{item_name}'.",
        }

    matched_name = matched["item_name"].iloc[0]
    total_units = int(matched[qty_col].sum())
    total_rev = round(float(matched["revenue"].sum()), 2)
    avg_price = round(total_rev / total_units, 2) if total_units > 0 else 0.0
    category = matched["category"].iloc[0] if "category" in matched.columns else "General"

    return {
        "item_name": matched_name,
        "found": True,
        "category": category,
        "units_sold": total_units,
        "total_revenue": total_rev,
        "average_realized_price": avg_price,
        "transaction_count": len(matched),
    }


def get_item_profitability(run_id: int, item_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve verified contribution margins and food cost ratios."""
    menu_df = load_run_dataset(run_id, "menu")
    sales_df = load_run_dataset(run_id, "sales")
    costs_df = load_run_dataset(run_id, "costs")

    if menu_df is None or menu_df.empty:
        return {"error": "Menu dataset not uploaded.", "calculable": False}

    sales_summary = None
    if sales_df is not None and not sales_df.empty:
        clean_sales = impute_revenue(sales_df, menu_df)
        sales_summary = analyze_sales(clean_sales, menu_df)

    profit_metrics = calculate_profitability(menu_df, costs_df, sales_summary)

    def _to_dict(p):
        return {
            "item_name": getattr(p, "item_name", "Item"),
            "category": getattr(p, "category", "General"),
            "selling_price": getattr(p, "selling_price", 0.0),
            "cost_per_unit": getattr(p, "cost_per_unit", None),
            "margin_amount": getattr(p, "margin_amount", None),
            "margin_pct": getattr(p, "margin_pct", None),
            "is_high_margin": getattr(p, "is_high_margin", False),
        }

    items_list = [_to_dict(p) for p in profit_metrics]

    if item_name:
        clean_name = item_name.strip().lower()
        matched = [i for i in items_list if clean_name in i["item_name"].lower()]
        if matched:
            return {"item": matched[0], "found": True, "calculable": True}
        return {"item_name": item_name, "found": False, "calculable": True}

    # Top high margin & low margin items
    with_margin = [i for i in items_list if i["margin_pct"] is not None]
    with_margin.sort(key=lambda x: x["margin_pct"], reverse=True)

    return {
        "calculable": bool(with_margin),
        "total_items_costed": len(with_margin),
        "top_margin_items": with_margin[:5],
        "lowest_margin_items": with_margin[-5:] if with_margin else [],
    }


def get_menu_item_details(run_id: int, item_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve catalog listings, prices, categories, and descriptions."""
    menu_df = load_run_dataset(run_id, "menu")
    if menu_df is None or menu_df.empty:
        return {"error": "Menu catalog not uploaded for this run.", "has_data": False}

    items = []
    for _, row in menu_df.iterrows():
        name = str(row.get("item_name") or row.get("name") or "")
        cat = str(row.get("category") or "General")
        price = float(row.get("price") or 0.0)
        desc = str(row.get("description") or "")
        items.append({"item_name": name, "category": cat, "price": price, "description": desc})

    if item_name:
        clean_target = item_name.strip().lower()
        matched = [it for it in items if clean_target in it["item_name"].lower()]
        return {"found": bool(matched), "items": matched, "query": item_name}

    return {"total_items": len(items), "items": items[:20], "has_data": True}


def get_ingredient_costs(run_id: int, item_name: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve ingredient cost breakdown from cost dataset."""
    costs_df = load_run_dataset(run_id, "costs")
    if costs_df is None or costs_df.empty:
        return {
            "has_data": False,
            "message": "No ingredient cost dataset uploaded for this run. Food costs cannot be calculated from records.",
        }

    records = []
    for _, row in costs_df.iterrows():
        records.append({
            "item_name": str(row.get("item_name") or row.get("name") or ""),
            "cost_per_unit": float(row.get("cost_per_unit") or row.get("ingredient_cost") or 0.0),
            "unit": str(row.get("unit") or "serving"),
        })

    if item_name:
        clean_target = item_name.strip().lower()
        matched = [r for r in records if clean_target in r["item_name"].lower()]
        return {"has_data": bool(matched), "records": matched, "query": item_name}

    return {"has_data": True, "total_cost_records": len(records), "records": records[:10]}


def get_recipe_details(restaurant_id: int, dish_name: str) -> Dict[str, Any]:
    """Check if proprietary recipe records exist in database for this restaurant."""
    assets = repo.list_generated_assets(restaurant_id, asset_type="recipe")
    clean_target = dish_name.strip().lower()
    for a in assets:
        content = a.get("content")
        if isinstance(content, dict) and clean_target in content.get("dish_name", "").lower():
            return {"exists_in_database": True, "recipe": content, "source": "saved_asset"}

    return {
        "exists_in_database": False,
        "dish_name": dish_name,
        "message": f"No custom recipe dataset or saved recipe found for '{dish_name}'. Suggestions will be based on culinary benchmarks.",
    }


def get_customer_reviews(run_id: int, item_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Retrieve verified customer reviews, ratings, and dish feedback."""
    reviews_df = load_run_dataset(run_id, "reviews")
    if reviews_df is None or reviews_df.empty:
        return {
            "has_reviews": False,
            "message": "No customer reviews uploaded for this run.",
            "review_count": 0,
        }

    text_col = "review_text" if "review_text" in reviews_df.columns else "text"
    rating_col = "rating" if "rating" in reviews_df.columns else None

    reviews = []
    for _, row in reviews_df.iterrows():
        t = str(row.get(text_col, ""))
        r = float(row.get(rating_col, 0.0)) if rating_col else None
        dt = str(row.get("date", "N/A"))
        reviews.append({"text": t, "rating": r, "date": dt})

    if item_name:
        target = item_name.strip().lower()
        matched = [rv for rv in reviews if target in rv["text"].lower()]
        avg_rat = (
            sum(rv["rating"] for rv in matched if rv["rating"]) / len(matched)
            if matched and any(rv["rating"] for rv in matched)
            else None
        )
        return {
            "has_reviews": bool(matched),
            "item_name": item_name,
            "mention_count": len(matched),
            "average_rating_for_item": round(avg_rat, 2) if avg_rat else None,
            "reviews": matched[:limit],
        }

    avg_all = (
        sum(rv["rating"] for rv in reviews if rv["rating"]) / len(reviews)
        if any(rv["rating"] for rv in reviews)
        else None
    )
    return {
        "has_reviews": True,
        "review_count": len(reviews),
        "overall_average_rating": round(avg_all, 2) if avg_all else None,
        "sample_reviews": reviews[:limit],
    }


def get_item_review_insights(run_id: int, item_name: Optional[str] = None) -> Dict[str, Any]:
    """Extract item-level sentiment, praised features, and customer friction points."""
    reviews_df = load_run_dataset(run_id, "reviews")
    menu_df = load_run_dataset(run_id, "menu")
    if reviews_df is None or reviews_df.empty:
        return {"has_data": False, "message": "No reviews available."}

    insights = extract_item_review_insights(reviews_df, menu_df)
    if item_name:
        target = item_name.strip().lower()
        matched = [i for i in insights if target in i.get("item_name", "").lower()]
        return {"has_data": bool(matched), "insights": matched}

    return {"has_data": True, "insights": insights[:10]}


def get_food_waste_records(run_id: int) -> Dict[str, Any]:
    """Retrieve logged kitchen food waste incidents."""
    records = repo.list_waste_records(run_id)
    if not records:
        return {
            "has_records": False,
            "record_count": 0,
            "message": "The current dataset does not contain physical waste records to identify the biggest sources.",
        }

    calc = calculate_waste_cost(records)
    return {
        "has_records": True,
        "record_count": len(records),
        "total_waste_cost": calc.get("total_waste_cost", 0.0),
        "by_ingredient": calc.get("by_ingredient", {}),
        "recent_records": records[:5],
    }


def get_inventory_data(run_id: int) -> Dict[str, Any]:
    """Assess inventory velocity and holding exposure."""
    sales_df = load_run_dataset(run_id, "sales")
    menu_df = load_run_dataset(run_id, "menu")
    costs_df = load_run_dataset(run_id, "costs")

    spoilage = analyze_spoilage_risk(sales_df, menu_df, costs_df)
    return {
        "inventory_exposure_weekly": spoilage.get("total_weekly_exposure", 0.0),
        "slow_moving_items": spoilage.get("slow_moving_items", [])[:5],
        "inventory_risk_level": "High" if spoilage.get("total_weekly_exposure", 0) > 5000 else "Moderate",
    }


def get_spoilage_risk(run_id: int) -> Dict[str, Any]:
    """Identify slow-moving items with high holding costs and spoilage risk."""
    sales_df = load_run_dataset(run_id, "sales")
    menu_df = load_run_dataset(run_id, "menu")
    costs_df = load_run_dataset(run_id, "costs")

    if sales_df is None or sales_df.empty:
        return {
            "has_data": False,
            "message": "Sales records are required to calculate spoilage risk from sales velocity.",
        }

    return analyze_spoilage_risk(sales_df, menu_df, costs_df)


def generate_menu_recommendations(run_id: int) -> Dict[str, Any]:
    """Retrieve verified menu engineering recommendations (Stars, Plowhorses, Puzzles, Dogs)."""
    recs = repo.list_recommendations(run_id)
    return {
        "run_id": run_id,
        "recommendation_count": len(recs),
        "recommendations": recs[:10],
    }


def generate_restaurant_report(run_id: int) -> Dict[str, Any]:
    """Generate high-level verified KPI snapshot for an active run."""
    sales_df = load_run_dataset(run_id, "sales")
    menu_df = load_run_dataset(run_id, "menu")
    reviews_df = load_run_dataset(run_id, "reviews")

    summary = {}
    if sales_df is not None and not sales_df.empty:
        clean_sales = impute_revenue(sales_df, menu_df)
        sales_sum = analyze_sales(clean_sales, menu_df)
        summary["total_revenue"] = sales_sum.total_revenue
        summary["total_units"] = sales_sum.total_units
        summary["period"] = f"{sales_sum.period_start} to {sales_sum.period_end}"

    if reviews_df is not None and not reviews_df.empty:
        sent = analyze_sentiment_local(reviews_df)
        summary["review_count"] = sent.review_count
        summary["avg_rating"] = sent.avg_rating

    return summary
