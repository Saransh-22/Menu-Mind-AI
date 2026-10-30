"""
Tests for agent tool executor (mocked — no real API calls).
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from agent.schemas import AgentState, MenuAction
from agent.state import create_initial_state
from agent.tools import ToolExecutor


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def basic_menu():
    return pd.DataFrame({
        "item_id":   ["I1", "I2"],
        "item_name": ["margherita pizza", "caesar salad"],
        "category":  ["Pizza", "Salad"],
        "price":     [12.99, 9.99],
    })


@pytest.fixture
def basic_sales():
    return pd.DataFrame({
        "item_name":     ["margherita pizza", "caesar salad"],
        "date":          pd.to_datetime(["2024-01-10", "2024-01-10"]),
        "quantity_sold": [5, 2],
        "revenue":       [64.95, 19.98],
    })


@pytest.fixture
def basic_reviews():
    return pd.DataFrame({
        "review_text": ["Best pizza ever!", "Salad was okay."],
        "rating":      [5.0, 3.0],
        "source":      ["test", "test"],
        "item_name":   ["margherita pizza", "caesar salad"],
    })


@pytest.fixture
def state():
    return create_initial_state(1, "Test Restaurant, TestCity", ["menu", "sales"], 20)


@pytest.fixture
def executor(state, basic_menu, basic_sales, basic_reviews):
    return ToolExecutor(
        state=state,
        menu_df=basic_menu,
        sales_df=basic_sales,
        reviews_df=basic_reviews,
        costs_df=None,
        gemini_client=None,
    )


# ─── Tool: analyze_sales ──────────────────────────────────────────────────────

def test_tool_analyze_sales(executor):
    result = executor.execute("analyze_sales", {})
    assert "error" not in result
    assert result["total_units"] == 7
    assert result["total_revenue"] > 0
    assert executor.state.sales_summary is not None


def test_tool_analyze_sales_no_data(state):
    exec_ = ToolExecutor(state, None, None, None, None, None)
    result = exec_.execute("analyze_sales", {})
    assert "error" in result


# ─── Tool: analyze_sentiment ─────────────────────────────────────────────────

def test_tool_analyze_sentiment_no_gemini(executor):
    result = executor.execute("analyze_sentiment", {})
    assert "error" not in result
    assert result["review_count"] == 2


def test_tool_analyze_sentiment_item_filter(executor):
    result = executor.execute("analyze_sentiment", {"item_name": "margherita pizza"})
    assert result["review_count"] == 1


def test_tool_analyze_sentiment_no_reviews(state, basic_menu, basic_sales):
    exec_ = ToolExecutor(state, basic_menu, basic_sales, None, None, None)
    result = exec_.execute("analyze_sentiment", {})
    assert "error" in result


# ─── Tool: calculate_profitability ───────────────────────────────────────────

def test_tool_calculate_profitability_no_costs(executor):
    result = executor.execute("calculate_profitability", {})
    assert result.get("calculable_items") == 0


def test_tool_calculate_profitability_with_costs(state, basic_menu, basic_sales):
    costs = pd.DataFrame({
        "item_id":         ["I1", "I2"],
        "item_name":       ["margherita pizza", "caesar salad"],
        "ingredient_cost": [4.50, 2.20],
        "packaging_cost":  [0.50, 0.30],
    })
    exec_ = ToolExecutor(state, basic_menu, basic_sales, None, costs, None)
    result = exec_.execute("calculate_profitability", {})
    assert result.get("calculable_items") == 2


# ─── Tool: search_restaurant_reviews ─────────────────────────────────────────

def test_tool_search_reviews_no_api_key(executor):
    """Should return gracefully without API key."""
    with patch("services.review_retrieval_service.SEARCH_API_KEY", ""):
        with patch("services.review_retrieval_service.SEARCH_ENGINE_ID", ""):
            result = executor.execute("search_restaurant_reviews", {})
    assert result.get("success") is False
    assert result.get("review_count") == 0


# ─── Tool: unknown tool ───────────────────────────────────────────────────────

def test_tool_unknown(executor):
    result = executor.execute("nonexistent_tool", {})
    assert "error" in result


# ─── Max tool calls ───────────────────────────────────────────────────────────

def test_max_tool_calls_respected():
    state = create_initial_state(1, "Restaurant", ["sales"], max_tool_calls=1)
    assert state.can_call_tool() is True
    state.tool_calls_made = 1
    assert state.can_call_tool() is False


# ─── Recommend menu actions (mocked Gemini) ───────────────────────────────────

def test_tool_recommend_actions_mocked_gemini(state, basic_menu, basic_sales, basic_reviews):
    mock_response = MagicMock()
    mock_response.text = '''{
      "recommendations": [{
        "item_id": "I1",
        "item_name": "margherita pizza",
        "action": "PROMOTE",
        "priority": "high",
        "confidence_score": 0.85,
        "reasoning": "Strong sales, positive reviews.",
        "alternative_actions": ["REPRICE"],
        "expected_benefits": "Higher visibility.",
        "potential_risks": "Margin pressure.",
        "missing_information": "Cost data.",
        "next_steps": ["Feature prominently on menu."],
        "sales_metrics": {},
        "review_themes": {},
        "profitability": {},
        "success_metrics": "Revenue increase of 10%."
      }]
    }'''

    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value = mock_response

    # Build sales summary first
    exec_ = ToolExecutor(state, basic_menu, basic_sales, basic_reviews, None, mock_gemini)
    exec_.execute("analyze_sales", {})
    exec_.execute("analyze_sentiment", {})
    result = exec_.execute("recommend_menu_actions", {})

    assert "error" not in result
    assert result["count"] == 1
    assert state.recommendations[0].action == MenuAction.PROMOTE


def test_tool_recommend_actions_insufficient_evidence(state, basic_menu, basic_sales):
    mock_response = MagicMock()
    mock_response.text = '''{
      "recommendations": [{
        "item_id": "I2",
        "item_name": "caesar salad",
        "action": "INSUFFICIENT_EVIDENCE",
        "priority": "low",
        "confidence_score": 0.2,
        "reasoning": "Limited data available.",
        "alternative_actions": [],
        "expected_benefits": "N/A",
        "potential_risks": "N/A",
        "missing_information": "Cost and review data needed.",
        "next_steps": ["Gather more customer feedback."],
        "sales_metrics": {},
        "review_themes": {},
        "profitability": {},
        "success_metrics": "N/A"
      }]
    }'''
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value = mock_response

    exec_ = ToolExecutor(state, basic_menu, basic_sales, None, None, mock_gemini)
    exec_.execute("analyze_sales", {})
    result = exec_.execute("recommend_menu_actions", {})
    assert result["count"] == 1
    assert state.recommendations[0].action == MenuAction.INSUFFICIENT_EVIDENCE
