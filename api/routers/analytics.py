"""
Sales analytics and financial profitability endpoints.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_verified_run, get_run_datasets
from api.schemas import (
    SalesAnalysisSummary,
    ProfitabilityMetrics,
    RevenueTrendPoint,
    CategoryShare,
    AnalyticsSummaryOut,
)
from services.analytics_service import (
    analyze_sales,
    calculate_profitability,
    analyze_menu,
    impute_revenue,
    impute_category,
)

router = APIRouter(prefix="/api/runs", tags=["Sales Analytics"])


@router.get("/{run_id}/analytics/summary", response_model=AnalyticsSummaryOut)
def get_analytics_summary(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch complete sales overview, daily trends, and category distribution."""
    datasets = get_run_datasets(run_id)
    sales_df_raw = datasets.get("sales")
    menu_df = datasets.get("menu")

    if sales_df_raw is None or sales_df_raw.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sales dataset uploaded for this run. Upload sales data first.",
        )

    # Impute missing revenue and category if needed
    sales_df = impute_revenue(sales_df_raw, menu_df)
    sales_df = impute_category(sales_df, menu_df)

    summary = analyze_sales(sales_df, menu_df)

    # Generate daily trend series
    daily_trends: list[RevenueTrendPoint] = []
    if "date" in sales_df.columns and "revenue" in sales_df.columns:
        df_time = sales_df.copy()
        df_time["date"] = pd.to_datetime(df_time["date"], errors="coerce")
        df_time["revenue"] = pd.to_numeric(df_time["revenue"], errors="coerce")
        df_time = df_time.dropna(subset=["date", "revenue"])
        if not df_time.empty:
            df_daily = df_time.groupby(df_time["date"].dt.strftime("%Y-%m-%d"))["revenue"].sum().reset_index()
            df_daily.columns = ["date", "revenue"]
            df_daily = df_daily.sort_values("date")
            df_daily["rolling_7d"] = df_daily["revenue"].rolling(7, min_periods=1).mean().round(2)
            for _, r in df_daily.iterrows():
                daily_trends.append(
                    RevenueTrendPoint(
                        date=str(r["date"]),
                        revenue=round(float(r["revenue"]), 2),
                        rolling_7d=round(float(r["rolling_7d"]), 2),
                    )
                )

    # Generate category share series
    category_shares: list[CategoryShare] = []
    total_rev = summary.total_revenue
    for cat_name, metrics in summary.category_summary.items():
        cat_rev = float(metrics.get("revenue", 0.0))
        cat_qty = int(metrics.get("quantity", 0))
        pct = round(cat_rev / total_rev * 100, 2) if total_rev > 0 else 0.0
        category_shares.append(
            CategoryShare(
                category=cat_name,
                revenue=round(cat_rev, 2),
                units=cat_qty,
                percentage=pct,
            )
        )
    category_shares.sort(key=lambda c: c.revenue, reverse=True)

    return AnalyticsSummaryOut(
        summary=summary,
        daily_trends=daily_trends,
        category_shares=category_shares,
    )


@router.get("/{run_id}/analytics/trends", response_model=list[RevenueTrendPoint])
def get_revenue_trends(
    run_id: int,
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    run: dict = Depends(get_verified_run),
):
    """Fetch daily revenue trends with optional start and end date filtering."""
    datasets = get_run_datasets(run_id)
    sales_df_raw = datasets.get("sales")
    menu_df = datasets.get("menu")

    if sales_df_raw is None or sales_df_raw.empty:
        return []

    sales_df = impute_revenue(sales_df_raw, menu_df)
    if "date" not in sales_df.columns or "revenue" not in sales_df.columns:
        return []

    df_time = sales_df.copy()
    df_time["date"] = pd.to_datetime(df_time["date"], errors="coerce")
    df_time["revenue"] = pd.to_numeric(df_time["revenue"], errors="coerce")
    df_time = df_time.dropna(subset=["date", "revenue"])

    if start_date:
        df_time = df_time[df_time["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df_time = df_time[df_time["date"] <= pd.to_datetime(end_date)]

    if df_time.empty:
        return []

    df_daily = df_time.groupby(df_time["date"].dt.strftime("%Y-%m-%d"))["revenue"].sum().reset_index()
    df_daily.columns = ["date", "revenue"]
    df_daily = df_daily.sort_values("date")
    df_daily["rolling_7d"] = df_daily["revenue"].rolling(7, min_periods=1).mean().round(2)

    return [
        RevenueTrendPoint(
            date=str(r["date"]),
            revenue=round(float(r["revenue"]), 2),
            rolling_7d=round(float(r["rolling_7d"]), 2),
        )
        for _, r in df_daily.iterrows()
    ]


@router.get("/{run_id}/analytics/profitability", response_model=list[ProfitabilityMetrics])
def get_profitability_metrics(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch item-level contribution margins and profitability."""
    datasets = get_run_datasets(run_id)
    menu_df = datasets.get("menu")
    costs_df = datasets.get("costs")
    sales_df = datasets.get("sales")

    if menu_df is None or menu_df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No menu dataset found. Upload menu data first.",
        )

    sales_summary = analyze_sales(sales_df, menu_df) if sales_df is not None else None
    return calculate_profitability(menu_df, costs_df, sales_summary)


@router.get("/{run_id}/analytics/menu")
def get_menu_analytics(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch menu item counts, price distributions, and missing fields."""
    datasets = get_run_datasets(run_id)
    menu_df = datasets.get("menu")
    if menu_df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No menu dataset found for this run.",
        )
    return analyze_menu(menu_df)
