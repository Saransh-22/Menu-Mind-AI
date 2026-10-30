"""
Comprehensive API integration tests using FastAPI TestClient.
Tests verify end-to-end functionality across all REST endpoints using isolated test databases.
"""
import io
import pytest
from fastapi.testclient import TestClient

from api.main import app
from database.connection import initialize_database
from database import repository as repo


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fixture providing a TestClient with an isolated temporary SQLite database and data directory."""
    test_db = str(tmp_path / "test_api.db")
    test_data = tmp_path / "data" / "runs"
    test_data.mkdir(parents=True, exist_ok=True)

    initialize_database(test_db)
    monkeypatch.setattr("database.connection.DATABASE_PATH", test_db)
    monkeypatch.setattr("database.repository.DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr("services.dataset_storage.DATA_DIR", test_data)

    with TestClient(app) as test_client:
        yield test_client


def test_healthcheck(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_restaurant_lifecycle(client):
    # 1. Create restaurant
    res = client.post("/api/restaurants", json={
        "name": "Amber Spice",
        "city": "Bengaluru",
        "category": "North Indian",
        "location": "Indiranagar",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Amber Spice"
    assert data["is_new"] is True
    rest_id = data["id"]

    # 2. Deduplication check
    res_dup = client.post("/api/restaurants", json={
        "name": "amber spice",
        "city": "bengaluru",
    })
    assert res_dup.status_code == 201
    assert res_dup.json()["id"] == rest_id
    assert res_dup.json()["is_new"] is False

    # 3. Autocomplete
    res_auto = client.get("/api/restaurants/autocomplete?query=Amb")
    assert res_auto.status_code == 200
    assert any("Amber" in r["name"] for r in res_auto.json())

    # 4. List restaurants
    res_list = client.get("/api/restaurants")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_analysis_run_lifecycle(client):
    # Create restaurant
    r = client.post("/api/restaurants", json={"name": "Curry Leaf", "city": "Chennai"}).json()
    rest_id = r["id"]

    # Create run
    res = client.post(f"/api/restaurants/{rest_id}/runs", json={
        "period_start": "2024-01-01",
        "period_end": "2024-01-31",
        "notes": "Q1 Performance review",
    })
    assert res.status_code == 201
    run_id = res.json()["id"]

    # Get run details
    res_get = client.get(f"/api/runs/{run_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == run_id
    assert res_get.json()["status"] == "pending"


def test_dataset_upload_and_validation(client):
    r = client.post("/api/restaurants", json={"name": "Dosa Corner", "city": "Mysuru"}).json()
    run = client.post(f"/api/restaurants/{r['id']}/runs", json={}).json()
    run_id = run["id"]

    # Upload Menu CSV
    menu_csv = (
        "item_id,item_name,category,price\n"
        "ITEM1,Masala Dosa,South Indian,80.0\n"
        "ITEM2,Filter Coffee,Beverages,30.0\n"
    )
    res_menu = client.post(
        f"/api/runs/{run_id}/upload/menu",
        files={"file": ("menu.csv", io.BytesIO(menu_csv.encode("utf-8")), "text/csv")},
    )
    assert res_menu.status_code == 200
    assert res_menu.json()["accepted_records"] == 2

    # Upload Sales CSV
    sales_csv = (
        "item_id,date,quantity_sold,revenue\n"
        "ITEM1,2024-01-10,10,800.0\n"
        "ITEM2,2024-01-10,20,600.0\n"
    )
    res_sales = client.post(
        f"/api/runs/{run_id}/upload/sales",
        files={"file": ("sales.csv", io.BytesIO(sales_csv.encode("utf-8")), "text/csv")},
    )
    assert res_sales.status_code == 200
    assert res_sales.json()["accepted_records"] == 2

    # Validate Datasets
    res_val = client.get(f"/api/runs/{run_id}/validate")
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is True

    # Dataset Preview
    res_prev = client.get(f"/api/runs/{run_id}/datasets/menu/preview")
    assert res_prev.status_code == 200
    assert res_prev.json()["total_rows"] == 2


def test_analytics_endpoints(client):
    r = client.post("/api/restaurants", json={"name": "Tandoor King", "city": "Delhi"}).json()
    run = client.post(f"/api/restaurants/{r['id']}/runs", json={}).json()
    run_id = run["id"]

    menu_csv = "item_id,item_name,category,price\nITEM1,Butter Chicken,Curry,350.0\n"
    sales_csv = "item_id,date,quantity_sold,revenue\nITEM1,2024-01-15,5,1750.0\n"

    client.post(f"/api/runs/{run_id}/upload/menu", files={"file": ("menu.csv", menu_csv.encode("utf-8"), "text/csv")})
    client.post(f"/api/runs/{run_id}/upload/sales", files={"file": ("sales.csv", sales_csv.encode("utf-8"), "text/csv")})

    res_sum = client.get(f"/api/runs/{run_id}/analytics/summary")
    assert res_sum.status_code == 200
    data = res_sum.json()
    assert data["summary"]["total_revenue"] == 1750.0
    assert len(data["daily_trends"]) == 1


def test_recommendation_and_approval_flow(client):
    r = client.post("/api/restaurants", json={"name": "Biryani Zone", "city": "Hyderabad"}).json()
    run = client.post(f"/api/restaurants/{r['id']}/runs", json={}).json()
    run_id = run["id"]

    # Directly save a recommendation to repository
    rec_id = repo.save_recommendation(run_id, {
        "item_name": "Hyderabadi Biryani",
        "action": "PROMOTE",
        "priority": "high",
        "confidence_score": 0.95,
        "reasoning": "High sales margin with strong customer sentiment.",
    })
    assert rec_id > 0

    # Fetch via API
    res_recs = client.get(f"/api/runs/{run_id}/recommendations")
    assert res_recs.status_code == 200
    recs = res_recs.json()
    assert len(recs) == 1
    assert recs[0]["item_name"] == "Hyderabadi Biryani"
    assert recs[0]["approval"] is None

    # Approve recommendation
    res_app = client.post(f"/api/recommendations/{rec_id}/approval", json={
        "decision": "approved",
        "notes": "Feature on the weekend special chalkboard.",
    })
    assert res_app.status_code == 200
    assert res_app.json()["decision"] == "approved"

    # Verify updated approval is returned in list
    res_recs_after = client.get(f"/api/runs/{run_id}/recommendations")
    assert res_recs_after.json()[0]["approval"]["decision"] == "approved"


def test_experiment_management(client):
    r = client.post("/api/restaurants", json={"name": "Pasta Fresca", "city": "Goa"}).json()
    run = client.post(f"/api/restaurants/{r['id']}/runs", json={}).json()
    run_id = run["id"]

    res_exp = client.post(f"/api/runs/{run_id}/experiments", json={
        "title": "Truffle Pasta Price Test",
        "hypothesis": "Increase price by 10% without affecting orders.",
        "intervention": "New printed table cards.",
    })
    assert res_exp.status_code == 201
    exp_id = res_exp.json()["id"]

    # Update status
    res_status = client.patch(f"/api/experiments/{exp_id}/status", json={"status": "active"})
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "active"


def test_food_waste_and_reports(client):
    r = client.post("/api/restaurants", json={"name": "Green Kitchen", "city": "Bengaluru"}).json()
    run = client.post(f"/api/restaurants/{r['id']}/runs", json={}).json()
    run_id = run["id"]

    # Record verified waste
    res_waste = client.post(f"/api/runs/{run_id}/waste/records", json={
        "ingredient_name": "Tomatoes",
        "quantity": 3.5,
        "unit": "kg",
        "unit_cost": 40.0,
        "waste_reason": "Overripe",
    })
    assert res_waste.status_code == 201

    res_summary = client.get(f"/api/runs/{run_id}/waste/summary")
    assert res_summary.status_code == 200
    assert res_summary.json()["measured"]["total_waste_cost"] == 140.0

    # Test HTML report download
    res_html = client.get(f"/api/runs/{run_id}/reports/html")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
