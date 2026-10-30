import pandas as pd

from database.connection import initialize_database
from database import repository as repo
from services.waste_analysis_service import calculate_waste_cost


def test_waste_cost_uses_verified_quantity_and_unit_cost():
    result = calculate_waste_cost([
        {"ingredient_name": "Rice", "quantity": 2.5, "unit_cost": 40},
        {"ingredient_name": "Paneer", "quantity": 1, "unit_cost": 300},
        {"ingredient_name": "Unknown", "quantity": None, "unit_cost": 10},
    ])
    assert result["total_waste_cost"] == 400.0
    assert result["calculable_records"] == 2
    assert result["uncalculable_records"] == 1
    assert result["by_ingredient"]["Paneer"] == 300.0


def test_waste_records_persist_per_analysis_run(tmp_path):
    db = str(tmp_path / "waste.db")
    initialize_database(db)
    restaurant_id = repo.create_restaurant("Test Restaurant", db_path=db)
    run_id = repo.create_analysis_run(restaurant_id, db_path=db)

    record_id = repo.save_waste_record(run_id, {
        "ingredient_name": "Cooked rice",
        "quantity": 2,
        "unit": "kg",
        "unit_cost": 40,
        "waste_reason": "Over-preparation",
        "associated_dish": "Fried Rice",
        "verified_by_user": True,
    }, db_path=db)

    rows = repo.list_waste_records(run_id, db_path=db)
    assert record_id > 0
    assert len(rows) == 1
    assert rows[0]["ingredient_name"] == "Cooked rice"
    assert rows[0]["associated_dish"] == "Fried Rice"
    assert rows[0]["verified_by_user"] == 1


def test_waste_image_metadata_persists(tmp_path):
    db = str(tmp_path / "waste_images.db")
    initialize_database(db)
    restaurant_id = repo.create_restaurant("Test Restaurant", db_path=db)
    run_id = repo.create_analysis_run(restaurant_id, db_path=db)
    image_id = repo.save_waste_image(
        run_id, "leftovers.jpg", "image/jpeg",
        [{"name": "Rice", "confidence": 0.9}], ["Cannot infer quantity"],
        db_path=db,
    )
    assert image_id > 0


# ─── Phase 6: Spoilage & Demand Risk Analytics ───────────────────────────────

def test_analyze_spoilage_risk_identifies_slow_movers():
    from services.waste_analysis_service import analyze_spoilage_risk

    sales_df = pd.DataFrame({
        "item_name": ["Fast Pizza", "Slow Salad", "Fast Pizza", "Slow Salad", "Rare Dish"],
        "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-01"],
        "quantity_sold": [10, 1, 12, 1, 1],
    })
    costs_df = pd.DataFrame({
        "item_name": ["Fast Pizza", "Slow Salad", "Rare Dish"],
        "ingredient_cost": [40.0, 30.0, 80.0],
    })

    result = analyze_spoilage_risk(sales_df, costs_df=costs_df)
    assert result["median_velocity"] > 0
    slow_items = result["slow_moving_items"]
    assert len(slow_items) >= 2
    item_names = [i["item_name"] for i in slow_items]
    assert "Slow Salad" in item_names
    assert "Rare Dish" in item_names
    assert "Fast Pizza" not in item_names
    assert result["total_weekly_exposure"] > 0
    assert len(result["action_items"]) >= 3


def test_analyze_spoilage_risk_handles_empty_sales():
    from services.waste_analysis_service import analyze_spoilage_risk

    result = analyze_spoilage_risk(None)
    assert result["slow_moving_items"] == []
    assert result["total_weekly_exposure"] == 0.0
    assert len(result["limitations"]) >= 1

    result_empty = analyze_spoilage_risk(pd.DataFrame())
    assert result_empty["slow_moving_items"] == []


def test_analyze_spoilage_risk_handles_missing_costs():
    from services.waste_analysis_service import analyze_spoilage_risk

    sales_df = pd.DataFrame({
        "item_name": ["Soup"],
        "quantity_sold": [1],
    })
    result = analyze_spoilage_risk(sales_df, costs_df=None)
    assert len(result["slow_moving_items"]) == 1
    soup = result["slow_moving_items"][0]
    assert soup["cost_is_estimated"] is True
    assert soup["weekly_exposure"] > 0

