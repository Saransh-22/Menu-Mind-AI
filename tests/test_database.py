"""
Tests for database operations.
"""
import pytest
import tempfile
from database.connection import initialize_database
from database import repository as repo


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test_db.db")
    initialize_database(path)
    return path


def test_create_restaurant(db):
    rest_id = repo.create_restaurant("Pizzeria Roma", "Rome", db_path=db)
    assert rest_id > 0
    rest = repo.get_restaurant(rest_id, db_path=db)
    assert rest["name"] == "Pizzeria Roma"
    assert rest["city"] == "Rome"


def test_list_restaurants(db):
    repo.create_restaurant("R1", "C1", db_path=db)
    repo.create_restaurant("R2", "C2", db_path=db)
    results = repo.list_restaurants(db_path=db)
    assert len(results) >= 2


def test_create_analysis_run(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, "2024-01-01", "2024-12-31", db_path=db)
    assert run_id > 0
    run = repo.get_analysis_run(run_id, db_path=db)
    assert run["status"] == "pending"


def test_update_run_status(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    repo.update_run_status(run_id, "completed", 0.92, db_path=db)
    run = repo.get_analysis_run(run_id, db_path=db)
    assert run["status"] == "completed"
    assert abs(run["data_quality_score"] - 0.92) < 0.001


def test_create_experiment(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    exp_id = repo.create_experiment(run_id, {
        "title": "Price Increase Test",
        "hypothesis": "Increasing price by $1 will not reduce demand.",
        "intervention": "Raise Margherita Pizza price from $12.99 to $13.99",
        "baseline_start": "2024-01-01",
        "baseline_end": "2024-01-31",
        "test_start": "2024-02-01",
        "test_end": "2024-02-29",
        "success_criteria": "Revenue ≥ baseline",
        "guardrail_metrics": "Quantity drop ≤ 10%",
    }, db_path=db)
    assert exp_id > 0
    experiments = repo.list_experiments(run_id, db_path=db)
    assert any(e["id"] == exp_id for e in experiments)


def test_experiment_status_transitions(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    exp_id = repo.create_experiment(run_id, {"title": "Test", "hypothesis": "H"}, db_path=db)
    repo.update_experiment_status(exp_id, "approved", db_path=db)
    exps = repo.list_experiments(run_id, db_path=db)
    exp = next(e for e in exps if e["id"] == exp_id)
    assert exp["status"] == "approved"


def test_save_experiment_results(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    exp_id = repo.create_experiment(run_id, {"title": "T"}, db_path=db)
    repo.save_experiment_result(exp_id, [
        {"metric_name": "revenue", "baseline_value": 1000.0, "test_value": 1100.0,
         "change_pct": 10.0, "notes": ""},
    ], db_path=db)
    results = repo.get_experiment_results(exp_id, db_path=db)
    assert len(results) == 1
    assert results[0]["metric_name"] == "revenue"


def test_retrieval_metadata(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    meta_id = repo.save_retrieval_metadata(
        run_id, "Google Search API", "https://example.com", 5, db_path=db
    )
    assert meta_id > 0
    meta_list = repo.list_retrieval_metadata(run_id, db_path=db)
    assert len(meta_list) == 1
    assert meta_list[0]["source"] == "Google Search API"
