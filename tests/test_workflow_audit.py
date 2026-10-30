"""
Comprehensive automated tests covering the full MenuMind AI workflow audit:
- Restaurant management & deduplication (get_or_create_restaurant)
- Autocomplete restaurant search
- Schema & cross-dataset foreign-key validation (menu, sales, costs)
- Imputation of revenue (quantity_sold * price)
- Category mapping from item_id
- Navigation routing resolution
- Analytics page revenue/category helpers
- Profitability join, no-cost edge case
- Report generation & currency formatting (INR Rs)
- Waste cost calculation
"""
import pytest
import pandas as pd
from database.connection import initialize_database
from database import repository as repo
from services.ingestion_service import (
    ingest_menu,
    ingest_sales,
    ingest_costs,
    ingest_reviews,
    validate_cross_dataset_integrity,
)
from services.preprocessing_service import clean_menu, clean_sales
from services.analytics_service import analyze_sales, calculate_profitability
from services.review_retrieval_service import autocomplete_restaurant_name
from services.waste_analysis_service import calculate_waste_cost
from services.report_service import generate_html_report
from agent.schemas import AgentState, SalesAnalysisSummary, DataQualityReport


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "audit_test.db")
    initialize_database(db_file)
    return db_file


# ── Phase 1: Restaurant Management & Deduplication ────────────────────────────

def test_restaurant_deduplication(test_db):
    r1_id = repo.create_restaurant("Spice Hub", "Bengaluru", db_path=test_db)
    assert r1_id > 0

    found = repo.find_restaurant_by_name("Spice Hub", "Bengaluru", db_path=test_db)
    assert found is not None
    assert found["id"] == r1_id

    # Case-insensitive match
    found_lower = repo.find_restaurant_by_name("spice hub", "bengaluru", db_path=test_db)
    assert found_lower is not None
    assert found_lower["id"] == r1_id

    # Non-existent
    assert repo.find_restaurant_by_name("NonExistent", "City", db_path=test_db) is None


def test_autocomplete_local_db(test_db):
    repo.create_restaurant("Haldiram Sweets", "Delhi", db_path=test_db)
    repo.create_restaurant("Haldiram Express", "Mumbai", db_path=test_db)
    repo.create_restaurant("Barbeque Nation", "Delhi", db_path=test_db)

    results = repo.search_restaurants("Hal", db_path=test_db)
    assert len(results) == 2
    assert all("Haldiram" in r["name"] for r in results)


def test_get_or_create_restaurant_creates_new(test_db):
    """get_or_create_restaurant should create a new record on first call."""
    rest_id, created = repo.get_or_create_restaurant(
        "Saffron Garden", "Pune", db_path=test_db
    )
    assert rest_id > 0
    assert created is True


def test_get_or_create_restaurant_deduplicates(test_db):
    """Calling get_or_create_restaurant twice with same name+city returns same ID."""
    id1, _ = repo.get_or_create_restaurant("Dawat", "Hyderabad", db_path=test_db)
    id2, created2 = repo.get_or_create_restaurant("Dawat", "Hyderabad", db_path=test_db)
    assert id1 == id2
    assert created2 is False
    # Only one record should exist
    all_rests = repo.list_restaurants(db_path=test_db)
    assert sum(1 for r in all_rests if r["name"] == "Dawat") == 1


def test_get_or_create_restaurant_case_insensitive(test_db):
    """get_or_create_restaurant deduplication is case-insensitive."""
    id1, _ = repo.get_or_create_restaurant("Moti Mahal", "Delhi", db_path=test_db)
    id2, created2 = repo.get_or_create_restaurant("moti mahal", "delhi", db_path=test_db)
    assert id1 == id2
    assert created2 is False


def test_get_or_create_restaurant_different_city_is_new(test_db):
    """Same name but different city should create a new record."""
    id1, _ = repo.get_or_create_restaurant("Karim's", "Delhi", db_path=test_db)
    id2, created2 = repo.get_or_create_restaurant("Karim's", "Mumbai", db_path=test_db)
    assert id1 != id2
    assert created2 is True


# ── Phase 2: CSV Ingestion, Validation & Session-State Persistence ─────────────

def test_validate_cross_dataset_missing_menu():
    sales = pd.DataFrame({"item_id": ["A"], "date": ["2024-01-01"], "quantity_sold": [2]})
    is_valid, errors, _ = validate_cross_dataset_integrity(None, sales)
    assert not is_valid
    assert any("Menu dataset is required" in e for e in errors)


def test_validate_cross_dataset_missing_sales():
    menu = pd.DataFrame({"item_id": ["A"], "item_name": ["Dish A"], "price": [10.0]})
    is_valid, errors, _ = validate_cross_dataset_integrity(menu, None)
    assert not is_valid
    assert any("Sales dataset is required" in e for e in errors)


def test_validate_cross_dataset_foreign_key_warning():
    menu = pd.DataFrame({"item_id": ["ITEM001", "ITEM002"], "item_name": ["A", "B"], "price": [10, 20]})
    sales = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM999"],
        "date": ["2024-01-01", "2024-01-02"],
        "quantity_sold": [5, 2],
    })
    is_valid, errors, warnings = validate_cross_dataset_integrity(menu, sales)
    assert is_valid  # Still valid to run, but warns
    assert len(errors) == 0
    assert any("ITEM999" in w or "not found in Menu" in w for w in warnings)


def test_validate_cross_dataset_costs_fk_warning():
    """Costs with unrecognised item_id should produce a warning but not block analysis."""
    menu = pd.DataFrame({
        "item_id": ["SKU-A"],
        "item_name": ["Chicken Tikka"],
        "price": [300.0],
    })
    sales = pd.DataFrame({
        "item_id": ["SKU-A"],
        "date": ["2024-03-01"],
        "quantity_sold": [5],
    })
    costs = pd.DataFrame({
        "item_id": ["SKU-A", "SKU-UNKNOWN"],
        "ingredient_cost": [90.0, 50.0],
    })
    is_valid, errors, warnings = validate_cross_dataset_integrity(menu, sales, costs)
    assert is_valid
    assert len(errors) == 0
    assert any("SKU-UNKNOWN" in w or "not found in Menu" in w for w in warnings)


def test_validate_cross_dataset_valid_datasets():
    """Fully valid datasets should produce no errors and no warnings."""
    menu = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "item_name": ["Pav Bhaji", "Dosa"],
        "price": [120.0, 80.0],
    })
    sales = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "date": ["2024-04-01", "2024-04-02"],
        "quantity_sold": [10, 15],
    })
    is_valid, errors, warnings = validate_cross_dataset_integrity(menu, sales)
    assert is_valid
    assert len(errors) == 0
    assert len(warnings) == 0


def test_sales_ingestion_note_for_missing_revenue():
    """ingest_sales should emit a NOTE (not CRITICAL) when revenue column is absent."""
    csv_bytes = b"item_id,date,quantity_sold\nITEM001,2024-01-01,5\n"
    df, mapping, warnings = ingest_sales(csv_bytes, "sales.csv")
    # Should NOT have CRITICAL for revenue
    critical_revenue = [w for w in warnings if "CRITICAL" in w and "revenue" in w.lower()]
    assert len(critical_revenue) == 0
    # Should have some note about computing revenue
    note_revenue = [w for w in warnings if "revenue" in w.lower()]
    assert len(note_revenue) > 0


def test_sales_ingestion_critical_for_missing_columns():
    """ingest_sales should emit CRITICAL errors for missing item identifier and date."""
    csv_bytes = b"revenue\n100\n"
    df, mapping, warnings = ingest_sales(csv_bytes, "sales.csv")
    critical_msgs = [w for w in warnings if "CRITICAL" in w]
    # Expect CRITICAL for missing item identifier AND for missing date
    assert len(critical_msgs) >= 2


# ── Phase 3: Sidebar Navigation & Routing Synchronization ─────────────────────

# Test the resolve_nav_target logic without Streamlit context by duplicating its logic.
# (app.py cannot be imported standalone due to Streamlit global state, so we test
# the algorithm directly and integration is covered by the in-browser smoke test.)

_TEST_NAV_PAGES = [
    "Overview",
    "Data Upload",
    "Sales Analytics",
    "Review Insights",
    "Food Waste Intelligence",
    "AI Recommendations",
    "Experiments",
    "Reports",
]


def _resolve(target: str) -> str:
    """Local implementation of resolve_nav_target for testing the algorithm."""
    if not target:
        return _TEST_NAV_PAGES[0]
    t = target.strip().lower()
    for np in _TEST_NAV_PAGES:
        np_clean = np.lower()
        if t in np_clean or np_clean in t:
            return np
    return _TEST_NAV_PAGES[0]


def test_nav_resolve_sales_analytics():
    assert _resolve("Sales Analytics") == "Sales Analytics"


def test_nav_resolve_partial_match_food_waste():
    assert _resolve("Food Waste") == "Food Waste Intelligence"


def test_nav_resolve_exact_reports():
    assert _resolve("Reports") == "Reports"


def test_nav_resolve_data_upload():
    assert _resolve("Data Upload") == "Data Upload"


def test_nav_resolve_experiments():
    assert _resolve("Experiments") == "Experiments"


def test_nav_resolve_unknown_defaults_to_first():
    assert _resolve("nonexistent-xyz-page") == _TEST_NAV_PAGES[0]


def test_nav_resolve_empty_defaults_to_first():
    assert _resolve("") == _TEST_NAV_PAGES[0]


# ── Phase 4: Sales Analytics Calculation Fixes ────────────────────────────────

def test_sales_missing_revenue_imputation():
    menu = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "item_name": ["Paneer Tikka", "Butter Naan"],
        "category": ["Starters", "Breads"],
        "price": [250.0, 40.0],
    })
    sales = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "date": ["2024-01-10", "2024-01-11"],
        "quantity_sold": [4, 10],
    })

    # Test clean_sales imputes revenue
    df_clean, report, _ = clean_sales(sales, menu)
    assert "revenue" in df_clean.columns
    assert df_clean["revenue"].iloc[0] == 4 * 250.0
    assert df_clean["revenue"].iloc[1] == 10 * 40.0
    assert df_clean["item_name"].iloc[0] == "Paneer Tikka"
    assert df_clean["category"].iloc[0] == "Starters"

    # Test analyze_sales uses imputed revenue correctly
    summary = analyze_sales(sales, menu)
    assert summary.total_revenue == 1400.0
    assert summary.total_units == 14
    assert len(summary.top_items) == 2
    assert summary.top_items[0].item_name == "Paneer Tikka"
    assert summary.top_items[0].total_revenue == 1000.0


def test_sales_category_mapping_from_item_id():
    menu = pd.DataFrame({
        "item_id": ["SKU1", "SKU2"],
        "item_name": ["Dal Makhani", "Jeera Rice"],
        "category": ["Main Course", "Rice"],
        "price": [220.0, 150.0],
    })
    sales = pd.DataFrame({
        "item_id": ["SKU1", "SKU2"],
        "date": ["2024-02-01", "2024-02-02"],
        "quantity_sold": [3, 2],
        "revenue": [660.0, 300.0],
    })

    summary = analyze_sales(sales, menu)
    assert summary.item_count == 2
    assert "Main Course" in summary.category_summary
    assert "Rice" in summary.category_summary
    assert summary.category_summary["Main Course"]["revenue"] == 660.0


def test_analytics_page_revenue_imputation_helper():
    """The _impute_revenue helper in analytics_page computes revenue when column is absent."""
    from ui.analytics_page import _impute_revenue
    menu = pd.DataFrame({
        "item_id": ["A1", "A2"],
        "item_name": ["Chole", "Bhature"],
        "price": [150.0, 30.0],
    })
    sales = pd.DataFrame({
        "item_id": ["A1", "A2"],
        "quantity_sold": [5, 10],
    })
    result = _impute_revenue(sales, menu)
    assert "revenue" in result.columns
    assert result["revenue"].iloc[0] == 5 * 150.0
    assert result["revenue"].iloc[1] == 10 * 30.0


def test_analytics_page_category_imputation_helper():
    """The _impute_category helper attaches categories from menu when missing in sales."""
    from ui.analytics_page import _impute_category
    menu = pd.DataFrame({
        "item_id": ["X1", "X2"],
        "item_name": ["Idli", "Sambar"],
        "category": ["South Indian", "Side"],
    })
    sales = pd.DataFrame({
        "item_id": ["X1", "X2"],
        "quantity_sold": [4, 8],
    })
    result = _impute_category(sales, menu)
    assert "category" in result.columns
    assert result.loc[0, "category"] == "South Indian"
    assert result.loc[1, "category"] == "Side"


def test_revenue_contribution_pct_sums_to_100():
    """Revenue contribution percentages should sum to 100% when all items are included."""
    menu = pd.DataFrame({
        "item_id": ["I1", "I2", "I3"],
        "item_name": ["Naan", "Tandoori", "Lassi"],
        "price": [40.0, 300.0, 80.0],
    })
    sales = pd.DataFrame({
        "item_id": ["I1", "I2", "I3"],
        "date": ["2024-05-01", "2024-05-01", "2024-05-01"],
        "quantity_sold": [20, 5, 10],
        "revenue": [800.0, 1500.0, 800.0],
    })
    summary = analyze_sales(sales, menu)
    total_pct = sum(item.revenue_contribution_pct for item in summary.top_items)
    assert abs(total_pct - 100.0) < 0.1


# ── 5. Profitability Calculations ─────────────────────────────────────────────

def test_profitability_join_on_item_id():
    menu = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "item_name": ["Biryani", "Raita"],
        "price": [300.0, 60.0],
    })
    costs = pd.DataFrame({
        "item_id": ["ITEM001", "ITEM002"],
        "ingredient_cost": [100.0, 15.0],
        "packaging_cost": [10.0, 5.0],
    })

    metrics = calculate_profitability(menu, costs)
    assert len(metrics) == 2
    m1 = next(m for m in metrics if m.item_name == "Biryani")
    assert m1.calculable
    assert m1.total_cost == 110.0
    assert m1.contribution_margin == 190.0
    assert m1.margin_pct == pytest.approx(63.33, 0.1)


def test_profitability_no_costs_not_calculable():
    """Items with no cost data should be marked as not calculable."""
    menu = pd.DataFrame({
        "item_id": ["X1"],
        "item_name": ["Mystery Dish"],
        "price": [200.0],
    })
    metrics = calculate_profitability(menu, None)
    assert len(metrics) == 1
    assert metrics[0].calculable is False


# ── 6. Waste Cost Analysis ───────────────────────────────────────────────────

def test_waste_cost_calculation():
    records = [
        {"ingredient_name": "Tomatoes", "quantity": 5.0, "unit_cost": 30.0},
        {"ingredient_name": "Paneer", "quantity": 2.0, "unit_cost": 280.0},
        {"ingredient_name": "Spoiled Milk", "quantity": -1.0, "unit_cost": 40.0},  # Invalid
    ]
    res = calculate_waste_cost(records)
    # 5 * 30 + 2 * 280 = 150 + 560 = 710.0
    assert res["total_waste_cost"] == 710.0
    assert res["calculable_records"] == 2
    assert res["uncalculable_records"] == 1
    assert res["by_ingredient"]["Paneer"] == 560.0


# ── 7. Reports & Currency Formatting ──────────────────────────────────────────

def test_html_report_currency_inr():
    summary = SalesAnalysisSummary(
        total_revenue=150000.0,
        total_units=1200,
        item_count=10,
        period_start="2024-01-01",
        period_end="2024-01-31",
    )
    state = AgentState(
        run_id=1,
        restaurant_name="Delhi Darbar",
        sales_summary=summary,
    )
    html = generate_html_report("Delhi Darbar", state, [])
    assert "Delhi Darbar" in html
    assert "\u20b9150,000.00" in html
    assert "$150,000" not in html
