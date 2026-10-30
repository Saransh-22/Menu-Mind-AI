"""
Tests for analytics_service.py
"""
import pandas as pd
import pytest

from services.analytics_service import (
    analyze_sales,
    calculate_profitability,
    analyze_menu,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_menu_df():
    return pd.DataFrame({
        "item_id":   ["I1", "I2", "I3"],
        "item_name": ["margherita pizza", "caesar salad", "tiramisu"],
        "category":  ["Pizza", "Salad", "Dessert"],
        "price":     [12.99, 9.99, 7.50],
    })


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame({
        "item_name":    ["margherita pizza", "caesar salad", "tiramisu", "margherita pizza"],
        "date":         pd.to_datetime(["2024-01-10", "2024-01-10", "2024-01-11", "2024-02-10"]),
        "quantity_sold": [3, 1, 2, 5],
        "revenue":       [38.97, 9.99, 15.00, 64.95],
    })


@pytest.fixture
def sample_costs_df():
    return pd.DataFrame({
        "item_id":         ["I1",  "I2",  "I3"],
        "item_name":       ["margherita pizza", "caesar salad", "tiramisu"],
        "ingredient_cost": [4.50, 2.20, 2.00],
        "packaging_cost":  [0.50, 0.30, 0.25],
    })


# ─── Sales Analytics ──────────────────────────────────────────────────────────

def test_analyze_sales_totals(sample_sales_df, sample_menu_df):
    result = analyze_sales(sample_sales_df, sample_menu_df)
    assert result.total_revenue == pytest.approx(128.91, rel=0.01)
    assert result.total_units == 11
    assert result.item_count == 3


def test_analyze_sales_top_items(sample_sales_df, sample_menu_df):
    result = analyze_sales(sample_sales_df, sample_menu_df)
    top_names = [i.item_name for i in result.top_items]
    assert "margherita pizza" in top_names


def test_analyze_sales_revenue_contribution(sample_sales_df, sample_menu_df):
    result = analyze_sales(sample_sales_df, sample_menu_df)
    total_pct = sum(
        i.revenue_contribution_pct for i in result.top_items if i.revenue_contribution_pct
    )
    assert abs(total_pct - 100.0) < 1.0  # should sum to ~100%


def test_analyze_sales_period_detection(sample_sales_df, sample_menu_df):
    result = analyze_sales(sample_sales_df, sample_menu_df)
    assert result.period_start == "2024-01-10"
    assert result.period_end == "2024-02-10"


def test_analyze_sales_empty():
    result = analyze_sales(pd.DataFrame())
    assert result.total_revenue == 0.0
    assert result.total_units == 0


def test_analyze_sales_no_revenue_column():
    df = pd.DataFrame({
        "item_name": ["Pizza"],
        "date": pd.to_datetime(["2024-01-01"]),
        "quantity_sold": [5],
    })
    result = analyze_sales(df)
    assert result.total_units == 5


def test_analyze_sales_category_summary(sample_sales_df, sample_menu_df):
    result = analyze_sales(sample_sales_df, sample_menu_df)
    assert "Pizza" in result.category_summary or len(result.category_summary) > 0


# ─── Profitability ────────────────────────────────────────────────────────────

def test_calculate_profitability_full(sample_menu_df, sample_costs_df):
    results = calculate_profitability(sample_menu_df, sample_costs_df)
    calculable = [r for r in results if r.calculable]
    assert len(calculable) == 3
    pizza = next(r for r in calculable if "pizza" in r.item_name)
    assert pizza.contribution_margin == pytest.approx(12.99 - 4.50 - 0.50, rel=0.01)
    assert pizza.margin_pct is not None and pizza.margin_pct > 0


def test_calculate_profitability_no_costs(sample_menu_df):
    results = calculate_profitability(sample_menu_df, None)
    assert all(not r.calculable for r in results)
    assert all(r.limitation_note for r in results)


def test_calculate_profitability_missing_ingredient_cost(sample_menu_df):
    costs = pd.DataFrame({
        "item_id":         ["I1"],
        "item_name":       ["margherita pizza"],
        "ingredient_cost": [None],   # missing
        "packaging_cost":  [0.50],
    })
    results = calculate_profitability(sample_menu_df, costs)
    pizza = next((r for r in results if "pizza" in r.item_name), None)
    assert pizza is not None
    assert not pizza.calculable


def test_calculate_profitability_negative_margin(sample_menu_df):
    costs = pd.DataFrame({
        "item_id":         ["I2"],
        "item_name":       ["caesar salad"],
        "ingredient_cost": [15.00],  # exceeds price
        "packaging_cost":  [1.00],
    })
    results = calculate_profitability(sample_menu_df, costs)
    salad = next((r for r in results if "salad" in r.item_name), None)
    if salad and salad.calculable:
        assert salad.contribution_margin < 0


# ─── Menu Analytics ───────────────────────────────────────────────────────────

def test_analyze_menu_counts(sample_menu_df):
    result = analyze_menu(sample_menu_df)
    assert result["total_items"] == 3


def test_analyze_menu_price_stats(sample_menu_df):
    result = analyze_menu(sample_menu_df)
    assert result["price_stats"]["min"] == 7.50
    assert result["price_stats"]["max"] == 12.99


def test_analyze_menu_empty():
    result = analyze_menu(pd.DataFrame())
    assert "error" in result
