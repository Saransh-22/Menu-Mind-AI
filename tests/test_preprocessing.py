"""
Tests for preprocessing_service.py
"""
import io
import pandas as pd
import pytest

from services.preprocessing_service import (
    clean_menu, clean_sales, clean_reviews, clean_costs
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_menu_df():
    return pd.DataFrame({
        "item_name": ["Margherita Pizza", "Caesar Salad", "Tiramisu"],
        "category":  ["Pizza", "Salad", "Dessert"],
        "price":     ["12.99", "9.99", "7.50"],
        "description": ["Classic pizza", "Caesar salad", "Italian dessert"],
    })


@pytest.fixture
def valid_sales_df():
    return pd.DataFrame({
        "item_name":     ["Margherita Pizza", "Caesar Salad", "Tiramisu"],
        "date":          ["2024-01-15", "2024-01-15", "2024-01-16"],
        "quantity_sold": ["3", "1", "2"],
        "revenue":       ["38.97", "9.99", "15.00"],
        "transaction_id": ["TXN001", "TXN002", "TXN003"],
    })


@pytest.fixture
def valid_reviews_df():
    return pd.DataFrame({
        "review_text": [
            "Great pizza! Loved the crust.",
            "Salad was a bit soggy.",
            "Best tiramisu I ever had.",
        ],
        "rating":   ["5", "3", "5"],
        "source":   ["example", "example", "example"],
        "item_name": ["Margherita Pizza", "Caesar Salad", "Tiramisu"],
    })


@pytest.fixture
def valid_costs_df():
    return pd.DataFrame({
        "item_id":         ["ITEM001", "ITEM002", "ITEM003"],
        "ingredient_cost": ["4.50", "2.20", "2.00"],
        "packaging_cost":  ["0.50", "0.30", "0.25"],
    })


# ─── Menu Tests ───────────────────────────────────────────────────────────────

def test_clean_menu_valid(valid_menu_df):
    df, report = clean_menu(valid_menu_df)
    assert report.accepted_records == 3
    assert report.rejected_records == 0
    assert report.quality_score > 0.8


def test_clean_menu_negative_price():
    df = pd.DataFrame({
        "item_name": ["Bad Item"],
        "price": ["-5.00"],
    })
    cleaned, report = clean_menu(df)
    assert cleaned["price"].isna().all()
    assert any("negative" in w.lower() for w in report.warnings)


def test_clean_menu_duplicate():
    df = pd.DataFrame({
        "item_name": ["Pizza", "Pizza"],
        "price": ["12.00", "12.00"],
    })
    cleaned, report = clean_menu(df)
    assert report.duplicate_records == 1
    assert len(cleaned) == 1


def test_clean_menu_missing_item_name():
    df = pd.DataFrame({
        "price": ["12.00", "9.00"],
    })
    _, report = clean_menu(df)
    assert any("item_name" in e.lower() or "name" in e.lower() for e in report.errors)


# ─── Sales Tests ──────────────────────────────────────────────────────────────

def test_clean_sales_valid(valid_sales_df, valid_menu_df):
    cleaned_menu, _ = clean_menu(valid_menu_df)
    cleaned, report, ambiguous = clean_sales(valid_sales_df, cleaned_menu)
    assert report.accepted_records == 3
    assert report.rejected_records == 0


def test_clean_sales_duplicate_transaction(valid_sales_df):
    df = valid_sales_df.copy()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    _, report, _ = clean_sales(df)
    assert report.duplicate_records >= 1


def test_clean_sales_invalid_date():
    df = pd.DataFrame({
        "item_name": ["Pizza"],
        "date": ["not-a-date"],
        "quantity_sold": ["2"],
        "revenue": ["25.00"],
        "transaction_id": ["T1"],
    })
    cleaned, report, _ = clean_sales(df)
    assert any("date" in w.lower() for w in report.warnings)


def test_clean_sales_negative_quantity():
    df = pd.DataFrame({
        "item_name": ["Pizza"],
        "date": ["2024-01-01"],
        "quantity_sold": ["-3"],
        "revenue": ["0"],
        "transaction_id": ["T1"],
    })
    cleaned, report, _ = clean_sales(df)
    assert any("negative" in w.lower() for w in report.warnings)


def test_clean_sales_missing_columns():
    df = pd.DataFrame({
        "item_name": ["Pizza"],
        "quantity_sold": ["3"],
        # No date, no revenue
    })
    _, report, _ = clean_sales(df)
    # Should not crash; warnings present
    assert isinstance(report.warnings, list)


# ─── Reviews Tests ────────────────────────────────────────────────────────────

def test_clean_reviews_valid(valid_reviews_df):
    cleaned, report = clean_reviews(valid_reviews_df)
    assert report.accepted_records == 3
    assert report.rejected_records == 0


def test_clean_reviews_empty_text():
    df = pd.DataFrame({
        "review_text": ["   ", "Good food!"],
        "source": ["x", "x"],
    })
    cleaned, report = clean_reviews(df)
    assert len(cleaned) == 1


def test_clean_reviews_duplicate():
    df = pd.DataFrame({
        "review_text": ["Same review text", "Same review text"],
        "source": ["x", "x"],
    })
    cleaned, report = clean_reviews(df)
    assert report.duplicate_records >= 1
    assert len(cleaned) == 1


# ─── Costs Tests ─────────────────────────────────────────────────────────────

def test_clean_costs_valid(valid_costs_df):
    cleaned, report = clean_costs(valid_costs_df)
    assert report.accepted_records == 3
    assert report.quality_score > 0.8


def test_clean_costs_negative_values():
    df = pd.DataFrame({
        "item_id": ["A"],
        "ingredient_cost": ["-2.00"],
    })
    cleaned, report = clean_costs(df)
    assert cleaned["ingredient_cost"].isna().all()
    assert any("negative" in w.lower() for w in report.warnings)


def test_clean_costs_duplicate_item_id():
    df = pd.DataFrame({
        "item_id": ["A", "A"],
        "ingredient_cost": ["2.00", "3.00"],
    })
    cleaned, report = clean_costs(df)
    assert len(cleaned) == 1
    assert report.duplicate_records == 1
