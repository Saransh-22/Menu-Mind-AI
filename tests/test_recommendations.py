"""
Tests for recommendation schemas, validation and database persistence.
Uses isolated temporary databases — no shared state between tests.
"""
import pytest

from agent.schemas import Recommendation, MenuAction, Priority
from database.connection import initialize_database
from database import repository as repo


# ─── Schema Validation ────────────────────────────────────────────────────────

def test_recommendation_valid():
    rec = Recommendation(
        item_name="Margherita Pizza",
        action=MenuAction.PROMOTE,
        priority=Priority.HIGH,
        confidence_score=0.85,
        reasoning="Strong sales and positive sentiment.",
    )
    assert rec.confidence_label() == "High"
    assert rec.action == MenuAction.PROMOTE


def test_recommendation_confidence_medium():
    rec = Recommendation(
        item_name="Caesar Salad",
        action=MenuAction.IMPROVE,
        priority=Priority.MEDIUM,
        confidence_score=0.6,
        reasoning="Mixed reviews.",
    )
    assert rec.confidence_label() == "Medium"


def test_recommendation_confidence_low():
    rec = Recommendation(
        item_name="Mystery Dish",
        action=MenuAction.INSUFFICIENT_EVIDENCE,
        priority=Priority.LOW,
        confidence_score=0.2,
        reasoning="Insufficient data.",
    )
    assert rec.confidence_label() == "Low"


def test_recommendation_confidence_rounded():
    rec = Recommendation(
        item_name="Test",
        action=MenuAction.IMPROVE,
        priority=Priority.MEDIUM,
        confidence_score=0.33333,
        reasoning="Test reasoning.",
    )
    assert 0.0 <= rec.confidence_score <= 1.0
    assert rec.confidence_score == round(0.33333, 3)


def test_recommendation_invalid_confidence():
    with pytest.raises(Exception):
        Recommendation(
            item_name="Test",
            action=MenuAction.IMPROVE,
            priority=Priority.LOW,
            confidence_score=1.5,  # out of range
            reasoning="Test.",
        )


def test_recommendation_invalid_action():
    with pytest.raises(Exception):
        Recommendation(
            item_name="Test",
            action="INVALID_ACTION",
            priority=Priority.LOW,
            confidence_score=0.5,
            reasoning="Test.",
        )


def test_insufficient_evidence_recommendation():
    rec = Recommendation(
        item_name="Mystery Dish",
        action=MenuAction.INSUFFICIENT_EVIDENCE,
        priority=Priority.LOW,
        confidence_score=0.2,
        reasoning="Insufficient data to justify any action.",
        missing_information="Need sales history and customer reviews.",
    )
    assert rec.action == MenuAction.INSUFFICIENT_EVIDENCE
    assert rec.missing_information != ""


def test_all_four_actions_valid():
    for action in (MenuAction.IMPROVE, MenuAction.REMOVE, MenuAction.PROMOTE, MenuAction.REPRICE):
        rec = Recommendation(
            item_name=f"Item {action.value}",
            action=action,
            priority=Priority.MEDIUM,
            confidence_score=0.6,
            reasoning=f"Test for {action.value}",
        )
        assert rec.action == action


# ─── Database Persistence ─────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    """Isolated temporary database for each test."""
    path = str(tmp_path / "test.db")
    initialize_database(path)
    return path


def test_save_and_load_recommendation(db):
    rest_id = repo.create_restaurant("Test Resto", "TestCity", db_path=db)
    run_id = repo.create_analysis_run(rest_id, "2024-01-01", "2024-03-31", db_path=db)

    rec = Recommendation(
        item_id="I1",
        item_name="Margherita Pizza",
        action=MenuAction.PROMOTE,
        priority=Priority.HIGH,
        confidence_score=0.85,
        reasoning="Top seller with positive reviews.",
        next_steps=["Feature on front page"],
        success_metrics="Revenue +10%",
    )
    rec_id = repo.save_recommendation(run_id, rec.model_dump(mode="json"), db_path=db)
    assert rec_id > 0

    loaded = repo.list_recommendations(run_id, db_path=db)
    assert len(loaded) == 1
    assert loaded[0]["item_name"] == "Margherita Pizza"
    assert loaded[0]["action"] == "PROMOTE"


def test_save_multiple_recommendations(db):
    rest_id = repo.create_restaurant("Bistro", "Paris", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)

    for action in (MenuAction.IMPROVE, MenuAction.REMOVE, MenuAction.PROMOTE):
        rec = Recommendation(
            item_name=f"Item {action.value}",
            action=action,
            priority=Priority.MEDIUM,
            confidence_score=0.6,
            reasoning=f"Reasoning for {action.value}",
        )
        repo.save_recommendation(run_id, rec.model_dump(mode="json"), db_path=db)

    loaded = repo.list_recommendations(run_id, db_path=db)
    assert len(loaded) == 3


def test_save_and_load_approval(db):
    rest_id = repo.create_restaurant("Test Resto", "TestCity", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    rec = Recommendation(
        item_name="Caesar Salad",
        action=MenuAction.IMPROVE,
        priority=Priority.MEDIUM,
        confidence_score=0.6,
        reasoning="Consistency complaints.",
    )
    rec_id = repo.save_recommendation(run_id, rec.model_dump(mode="json"), db_path=db)
    repo.save_approval(rec_id, "approved", "Looks good", db_path=db)

    approval = repo.get_approval(rec_id, db_path=db)
    assert approval is not None
    assert approval["decision"] == "approved"


def test_approval_persists_across_connections(db):
    """Simulate app restart by creating new connection to same DB path."""
    rest_id = repo.create_restaurant("Bistro", "Paris", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    rec = Recommendation(
        item_name="Croissant",
        action=MenuAction.REPRICE,
        priority=Priority.LOW,
        confidence_score=0.55,
        reasoning="Price-value mismatch reported.",
    )
    rec_id = repo.save_recommendation(run_id, rec.model_dump(mode="json"), db_path=db)
    repo.save_approval(rec_id, "rejected", db_path=db)

    # Re-load using db_path (simulates new app session connecting to same file)
    approval = repo.get_approval(rec_id, db_path=db)
    assert approval["decision"] == "rejected"


def test_no_approval_returns_none(db):
    rest_id = repo.create_restaurant("Test", "City", db_path=db)
    run_id = repo.create_analysis_run(rest_id, db_path=db)
    rec = Recommendation(
        item_name="Unapproved",
        action=MenuAction.INSUFFICIENT_EVIDENCE,
        priority=Priority.LOW,
        confidence_score=0.1,
        reasoning="No data.",
    )
    rec_id = repo.save_recommendation(run_id, rec.model_dump(mode="json"), db_path=db)
    approval = repo.get_approval(rec_id, db_path=db)
    assert approval is None


# ─── Deterministic Engine & Extended Schema Tests ────────────────────────────

def test_recommendation_title_and_suggested_action():
    rec = Recommendation(
        item_name="Truffle Fries",
        title="Optimize Recipe Margin: Truffle Fries",
        action=MenuAction.REPRICE,
        priority=Priority.HIGH,
        confidence_score=0.82,
        reasoning="High sales volume but margin is constrained.",
        suggested_action="Increase price by $1.50 or reduce portion size.",
    )
    assert rec.title == "Optimize Recipe Margin: Truffle Fries"
    assert rec.suggested_action == "Increase price by $1.50 or reduce portion size."
    dump = rec.model_dump(mode="json")
    assert dump["title"] == "Optimize Recipe Margin: Truffle Fries"
    assert dump["suggested_action"] == "Increase price by $1.50 or reduce portion size."


def test_deterministic_recommendations_promote():
    import pandas as pd
    from agent.state import create_initial_state
    from agent.tools import ToolExecutor
    from agent.schemas import ProfitabilityMetrics

    menu_df = pd.DataFrame([
        {"item_name": "Signature Burger", "price": 18.0, "category": "Mains"},
    ])
    sales_df = pd.DataFrame([
        {"item_name": "Signature Burger", "quantity_sold": 50, "revenue": 900.0},
    ])
    reviews_df = pd.DataFrame([
        {"item_name": "Signature Burger", "rating": 5.0, "review_text": "Best burger in town!"},
        {"item_name": "Signature Burger", "rating": 4.5, "review_text": "Juicy and delicious."},
    ])

    state = create_initial_state(run_id=1, restaurant_name="Test Diner", available_data=["menu", "sales", "reviews"])
    state.profitability_metrics = [
        ProfitabilityMetrics(item_name="Signature Burger", selling_price=18.0, total_cost=6.0, margin_pct=66.7, calculable=True)
    ]

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=None,
        gemini_client=None,
    )

    recs = executor._generate_deterministic_recommendations({})
    assert len(recs) == 1
    assert recs[0].action == MenuAction.PROMOTE
    assert recs[0].priority == Priority.HIGH
    assert recs[0].confidence_score >= 0.75
    assert "Signature Burger" in recs[0].title


def test_deterministic_recommendations_reprice():
    import pandas as pd
    from agent.state import create_initial_state
    from agent.tools import ToolExecutor
    from agent.schemas import ProfitabilityMetrics

    menu_df = pd.DataFrame([
        {"item_name": "Steak Frites", "price": 28.0, "category": "Mains"},
    ])
    sales_df = pd.DataFrame([
        {"item_name": "Steak Frites", "quantity_sold": 45, "revenue": 1260.0},
    ])
    reviews_df = pd.DataFrame([
        {"item_name": "Steak Frites", "rating": 4.5, "review_text": "Great steak."},
    ])

    state = create_initial_state(run_id=1, restaurant_name="Steakhouse", available_data=["menu", "sales", "costs"])
    # Low margin of 32%
    state.profitability_metrics = [
        ProfitabilityMetrics(item_name="Steak Frites", selling_price=28.0, total_cost=19.0, margin_pct=32.1, calculable=True)
    ]

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=None,
        gemini_client=None,
    )

    recs = executor._generate_deterministic_recommendations({})
    assert len(recs) == 1
    assert recs[0].action == MenuAction.REPRICE
    assert recs[0].priority == Priority.HIGH
    assert "Price" in recs[0].title or "Margin" in recs[0].title


def test_deterministic_recommendations_improve():
    import pandas as pd
    from agent.state import create_initial_state
    from agent.tools import ToolExecutor

    menu_df = pd.DataFrame([
        {"item_name": "Fish & Chips", "price": 16.0, "category": "Mains"},
    ])
    sales_df = pd.DataFrame([
        {"item_name": "Fish & Chips", "quantity_sold": 30, "revenue": 480.0},
    ])
    # Bad reviews
    reviews_df = pd.DataFrame([
        {"item_name": "Fish & Chips", "rating": 2.0, "review_text": "Too greasy and salty."},
        {"item_name": "Fish & Chips", "rating": 2.0, "review_text": "Soggy batter, very cold."},
    ])

    state = create_initial_state(run_id=1, restaurant_name="Seafood Pub", available_data=["menu", "sales", "reviews"])

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=None,
        gemini_client=None,
    )

    recs = executor._generate_deterministic_recommendations({})
    assert len(recs) == 1
    assert recs[0].action == MenuAction.IMPROVE
    assert "Prep" in recs[0].title or "Quality" in recs[0].title or "Refine" in recs[0].title


def test_deterministic_recommendations_remove():
    import pandas as pd
    from agent.state import create_initial_state
    from agent.tools import ToolExecutor

    menu_df = pd.DataFrame([
        {"item_name": "Boiled Cabbage", "price": 8.0, "category": "Sides"},
        {"item_name": "Popular Burger", "price": 15.0, "category": "Mains"},
    ])
    sales_df = pd.DataFrame([
        {"item_name": "Boiled Cabbage", "quantity_sold": 1, "revenue": 8.0},
        {"item_name": "Popular Burger", "quantity_sold": 100, "revenue": 1500.0},
    ])
    reviews_df = pd.DataFrame([
        {"item_name": "Boiled Cabbage", "rating": 1.0, "review_text": "Bland and stale cabbage."},
    ])

    state = create_initial_state(run_id=1, restaurant_name="Tavern", available_data=["menu", "sales", "reviews"])

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
        costs_df=None,
        gemini_client=None,
    )

    recs = executor._generate_deterministic_recommendations({})
    cabbage_rec = next((r for r in recs if r.item_name == "Boiled Cabbage"), None)
    assert cabbage_rec is not None
    assert cabbage_rec.action == MenuAction.REMOVE


def test_deterministic_recommendations_insufficient_evidence():
    import pandas as pd
    from agent.state import create_initial_state
    from agent.tools import ToolExecutor

    menu_df = pd.DataFrame([
        {"item_name": "Mystery Daily Special", "price": 22.0, "category": "Specials"},
    ])
    # No sales, no reviews, no costs
    state = create_initial_state(run_id=1, restaurant_name="New Cafe", available_data=["menu"])

    executor = ToolExecutor(
        state=state,
        menu_df=menu_df,
        sales_df=None,
        reviews_df=None,
        costs_df=None,
        gemini_client=None,
    )

    recs = executor._generate_deterministic_recommendations({})
    assert len(recs) == 1
    assert recs[0].action == MenuAction.INSUFFICIENT_EVIDENCE
    assert recs[0].priority == Priority.LOW
    assert recs[0].confidence_score <= 0.40


def test_orchestrator_recommendations_without_gemini(monkeypatch):
    """Ensure run_analysis generates recommendations even when Gemini client is None."""
    import pandas as pd
    import agent.orchestrator as orch

    monkeypatch.setattr(orch, "_get_gemini_client", lambda: None)

    menu_df = pd.DataFrame([
        {"item_name": "Classic Margherita", "price": 14.0, "category": "Pizza"},
    ])
    sales_df = pd.DataFrame([
        {"item_name": "Classic Margherita", "quantity_sold": 60, "revenue": 840.0},
    ])
    reviews_df = pd.DataFrame([
        {"item_name": "Classic Margherita", "rating": 5.0, "review_text": "Super tasty pizza!"},
    ])

    state = orch.run_analysis(
        run_id=999,
        restaurant_name="Pizza House",
        menu_df=menu_df,
        sales_df=sales_df,
        reviews_df=reviews_df,
    )
    assert state.finished is True
    assert len(state.recommendations) == 1
    assert state.recommendations[0].item_name == "Classic Margherita"
    assert state.recommendations[0].title is not None
    assert state.recommendations[0].suggested_action is not None

