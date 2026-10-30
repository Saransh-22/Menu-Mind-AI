"""
Mocked tests for SerpApi review retrieval integration.

All tests intercept outbound HTTP requests — no real API calls are made.
Tests cover:
  - Successful retrieval (organic + local results)
  - HTTP 401 invalid credentials
  - HTTP 429 rate-limit
  - Request timeout
  - API-level JSON error body
  - Empty results (no snippets)
  - Duplicate snippet deduplication
  - Fallback to GoogleCustomSearchSource when SerpApi unavailable
  - MIN_REVIEWS_THRESHOLD auto-trigger in orchestrator
  - Tool-level isolation (retrieval failure must not crash the agent)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from services.review_retrieval_service import (
    SerpApiSource,
    GoogleCustomSearchSource,
    NullReviewSource,
    retrieve_reviews,
    RetrievalResult,
)
from agent.state import create_initial_state
from agent.tools import ToolExecutor


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock)
        mock.raise_for_status.side_effect = http_err
    else:
        mock.raise_for_status.return_value = None
    return mock


ORGANIC_RESULTS_FIXTURE = [
    {
        "title": "Best Pizza Review",
        "link": "https://example.com/review/1",
        "snippet": "The Margherita pizza was absolutely incredible — crispy crust and fresh basil.",
        "source": "ExampleReviews",
        "date": "Jan 5, 2024",
        "rich_snippet": {
            "top": {
                "extensions": ["4.5/5 stars"]
            }
        },
    },
    {
        "title": "Caesar Salad review",
        "link": "https://example.com/review/2",
        "snippet": "Caesar salad was average — dressing a little too salty for my taste.",
        "source": "FoodCritic",
        "date": "Feb 10, 2024",
    },
]

LOCAL_RESULTS_FIXTURE = [
    {
        "title": "Pizza Palace",
        "rating": 4.2,
        "description": "A cozy neighbourhood pizza spot with great wood-fired pies.",
        "links": {"website": "https://pizzapalace.example.com"},
    },
]

SERPAPI_SUCCESS_BODY = {
    "organic_results": ORGANIC_RESULTS_FIXTURE,
    "local_results": LOCAL_RESULTS_FIXTURE,
}


# ─── SerpApiSource.is_available ───────────────────────────────────────────────

def test_serpapi_available_with_key():
    with patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"):
        assert SerpApiSource().is_available() is True


def test_serpapi_unavailable_without_key():
    with patch("services.review_retrieval_service.SEARCH_API_KEY", ""):
        assert SerpApiSource().is_available() is False


# ─── Successful retrieval ─────────────────────────────────────────────────────

def test_serpapi_retrieval_success():
    """Extracts snippets from organic + local results; rating parsed correctly."""
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(SERPAPI_SUCCESS_BODY)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Pizza Palace", "New York")

    assert result.success is True
    assert len(result.reviews) >= 2  # at least organic results
    # First organic result should carry a rating
    organic_review = next(
        r for r in result.reviews if r.source == "ExampleReviews"
    )
    assert organic_review.rating == 4.5
    assert organic_review.review_date == "Jan 5, 2024"
    assert "Margherita pizza" in organic_review.review_text

    # Local result with place-level rating
    local_review = next(
        (r for r in result.reviews if r.source == "Pizza Palace"), None
    )
    assert local_review is not None
    assert local_review.rating == 4.2


def test_serpapi_attribution_field():
    """Every retrieved review carries an attribution string."""
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(SERPAPI_SUCCESS_BODY)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Pizza Palace", "New York")

    for review in result.reviews:
        assert review.attribution, "attribution must not be empty"
        assert "snippet" in review.attribution.lower()


# ─── Duplicate deduplication ──────────────────────────────────────────────────

def test_serpapi_deduplication():
    """Identical snippets appearing twice must yield only one review."""
    duplicate_snippet = "Best pizza in town — highly recommend the Margherita."
    body = {
        "organic_results": [
            {
                "link": "https://a.com",
                "snippet": duplicate_snippet,
                "source": "SiteA",
            },
            {
                "link": "https://b.com",
                "snippet": duplicate_snippet,  # exact duplicate
                "source": "SiteB",
            },
        ]
    }
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(body)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Pizzeria Roma", "London")

    assert result.success is True
    texts = [r.review_text for r in result.reviews]
    assert texts.count(duplicate_snippet) == 1, "duplicate snippet must be deduplicated"


# ─── Empty results ────────────────────────────────────────────────────────────

def test_serpapi_empty_results():
    """When no usable snippets are found, result.success is False."""
    body = {"organic_results": [{"link": "https://a.com", "snippet": "short"}]}
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(body)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Ghost Restaurant", "Nowhere")

    assert result.success is False
    assert result.reviews == []
    assert result.error is not None


# ─── HTTP 401 — invalid credentials ──────────────────────────────────────────

def test_serpapi_http_401():
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "bad-key"),
        patch("requests.get", return_value=_mock_response({}, status_code=401)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Any Restaurant", "Any City")

    assert result.success is False
    assert "401" in result.error or "credentials" in result.error.lower()


# ─── HTTP 429 — rate limit ────────────────────────────────────────────────────

def test_serpapi_http_429():
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response({}, status_code=429)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Any Restaurant", "Any City")

    assert result.success is False
    assert "429" in result.error or "rate limit" in result.error.lower()


# ─── Timeout ─────────────────────────────────────────────────────────────────

def test_serpapi_timeout():
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", side_effect=requests.exceptions.Timeout),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Any Restaurant", "Any City")

    assert result.success is False
    assert "timed out" in result.error.lower() or "timeout" in result.error.lower()


# ─── API-level JSON error ─────────────────────────────────────────────────────

def test_serpapi_api_level_error():
    """SerpApi returns 200 OK but includes an 'error' key in the JSON body."""
    body = {"error": "Invalid API key."}
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(body)),
        patch("time.sleep"),
    ):
        result = SerpApiSource().retrieve("Any Restaurant", "Any City")

    assert result.success is False
    assert "Invalid API key" in result.error


# ─── No SEARCH_API_KEY — returns graceful error ───────────────────────────────

def test_serpapi_no_key_graceful():
    with patch("services.review_retrieval_service.SEARCH_API_KEY", ""):
        result = SerpApiSource().retrieve("Restaurant", "City")

    assert result.success is False
    assert result.reviews == []
    assert "SEARCH_API_KEY" in (result.error or "") or any(
        "SEARCH_API_KEY" in lim for lim in result.limitations
    )


# ─── retrieve_reviews() fallback chain ───────────────────────────────────────

def test_retrieve_reviews_serpapi_used_first():
    """retrieve_reviews() picks SerpApi before Google Custom Search."""
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(SERPAPI_SUCCESS_BODY)),
        patch("time.sleep"),
    ):
        result = retrieve_reviews("Pizza Palace", "New York")

    assert result.success is True
    assert result.source == "SerpApi Google Search"


def test_retrieve_reviews_null_fallback():
    """
    With no key configured, SerpApi and GoogleCustomSearch both skip themselves
    (is_available() returns False).  NullReviewSource is_available() returns True
    but succeeds=False, so retrieve_reviews() falls through to the exhausted-all-sources
    fallback and returns source='None' with success=False.
    """
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", ""),
        patch("services.review_retrieval_service.SEARCH_ENGINE_ID", ""),
    ):
        result = retrieve_reviews("Restaurant", "City")

    assert result.success is False
    assert result.error is not None


# ─── ToolExecutor — retrieval failure isolation ───────────────────────────────

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


def test_tool_search_reviews_serpapi_success(basic_menu, basic_sales):
    """Tool returns retrieved reviews and merges them into executor.reviews_df."""
    state = create_initial_state(1, "Pizza Palace, New York", ["menu", "sales"], 20)
    executor = ToolExecutor(
        state=state,
        menu_df=basic_menu,
        sales_df=basic_sales,
        reviews_df=None,
        costs_df=None,
        gemini_client=None,
    )
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(SERPAPI_SUCCESS_BODY)),
        patch("time.sleep"),
    ):
        result = executor.execute("search_restaurant_reviews", {})

    assert result.get("success") is True
    assert result.get("review_count", 0) >= 2
    assert executor.reviews_df is not None
    assert len(executor.reviews_df) >= 2


def test_tool_search_reviews_network_error_does_not_crash(basic_menu, basic_sales):
    """A network error in retrieval must not propagate as an uncaught exception."""
    state = create_initial_state(1, "Pizza Palace, New York", ["menu", "sales"], 20)
    executor = ToolExecutor(
        state=state,
        menu_df=basic_menu,
        sales_df=basic_sales,
        reviews_df=None,
        costs_df=None,
        gemini_client=None,
    )
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("no route"),
        ),
        patch("time.sleep"),
    ):
        result = executor.execute("search_restaurant_reviews", {})

    # Tool executor must return a dict (error acceptable), not raise
    assert isinstance(result, dict)
    assert result.get("success") is False or "error" in result


# ─── MIN_REVIEWS_THRESHOLD — orchestrator auto-trigger ───────────────────────

def test_orchestrator_triggers_retrieval_below_threshold():
    """
    When uploaded reviews are below MIN_REVIEWS_THRESHOLD, the orchestrator
    must attempt web retrieval even if reviews_df is not None.
    """
    from agent.orchestrator import run_analysis

    menu_df = pd.DataFrame({
        "item_id": ["I1"],
        "item_name": ["Margherita Pizza"],
        "category": ["Pizza"],
        "price": [12.99],
    })
    # Only 2 reviews — below the default threshold of 5
    reviews_df = pd.DataFrame({
        "review_text": ["Good pizza.", "Nice place."],
        "rating": [4.0, 3.5],
        "source": ["manual", "manual"],
    })

    retrieval_called = []

    def _fake_retrieve(restaurant_name, city, website=None):
        retrieval_called.append(True)
        return RetrievalResult(
            reviews=[],
            source="SerpApi Google Search",
            limitations=["No results found."],
            success=False,
            error="No results found.",
        )

    with patch("agent.tools.retrieve_reviews", side_effect=_fake_retrieve):
        state = run_analysis(
            run_id=99,
            restaurant_name="Pizza Palace, New York",
            menu_df=menu_df,
            reviews_df=reviews_df,
        )

    assert len(retrieval_called) >= 1, (
        "Orchestrator must trigger web retrieval when reviews < MIN_REVIEWS_THRESHOLD"
    )


# ─── Phase 5: Caching, Attribution, and Sentiment Calculations ──────────────

def test_retrieve_reviews_caching():
    """Verify in-memory caching prevents duplicate API requests."""
    from services.review_retrieval_service import clear_review_cache

    clear_review_cache()
    mock_get = MagicMock(return_value=_mock_response(SERPAPI_SUCCESS_BODY))
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", mock_get),
        patch("time.sleep"),
    ):
        # First call hits API
        res1 = retrieve_reviews("Pizzeria Roma", "Rome")
        assert res1.success is True
        assert mock_get.call_count == 1

        # Second call with same restaurant/city returns cached result
        res2 = retrieve_reviews("Pizzeria Roma", "Rome")
        assert res2.success is True
        assert len(res2.reviews) == len(res1.reviews)
        assert mock_get.call_count == 1, "Second retrieve call must hit cache, not requests.get"


def test_retrieve_reviews_force_refresh():
    """Verify force_refresh=True bypasses the cache."""
    from services.review_retrieval_service import clear_review_cache

    clear_review_cache()
    mock_get = MagicMock(return_value=_mock_response(SERPAPI_SUCCESS_BODY))
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", mock_get),
        patch("time.sleep"),
    ):
        res1 = retrieve_reviews("Pizzeria Roma", "Rome")
        assert mock_get.call_count == 1

        # Force refresh makes a second API call
        res2 = retrieve_reviews("Pizzeria Roma", "Rome", force_refresh=True)
        assert mock_get.call_count == 2
        assert res2.success is True


def test_source_attribution_integrity():
    """Retrieved reviews must be explicitly marked as snippets with attribution."""
    from services.review_retrieval_service import clear_review_cache

    clear_review_cache()
    with (
        patch("services.review_retrieval_service.SEARCH_API_KEY", "test-key"),
        patch("requests.get", return_value=_mock_response(SERPAPI_SUCCESS_BODY)),
        patch("time.sleep"),
    ):
        result = retrieve_reviews("Pizza Palace", "New York", force_refresh=True)

    assert result.success is True
    for r in result.reviews:
        assert r.is_snippet is True, "External retrieved reviews must have is_snippet=True"
        assert r.attribution != "", "Attribution cannot be empty"
        assert "snippet" in r.attribution.lower() or "result" in r.attribution.lower()


def test_sentiment_distinguishes_verified_from_snippets():
    """Verify that sentiment calculation counts verified and snippet reviews separately."""
    from services.sentiment_service import analyze_sentiment_local

    df = pd.DataFrame([
        {"review_text": "Incredible crispy pizza crust!", "rating": 5.0, "is_snippet": False, "attribution": "Uploaded review"},
        {"review_text": "Great service and authentic sauce.", "rating": 4.5, "is_snippet": False, "attribution": "Uploaded review"},
        {"review_text": "Soggy salad and salty soup.", "rating": 2.0, "is_snippet": True, "attribution": "SerpApi Google Search snippet"},
        {"review_text": "Too expensive for small portions.", "rating": 2.0, "is_snippet": True, "attribution": "SerpApi Google Search snippet"},
    ])

    summary = analyze_sentiment_local(df)
    assert summary.review_count == 4
    assert summary.verified_count == 2
    assert summary.snippet_count == 2
    assert summary.verified_avg_rating == pytest.approx(4.75, rel=0.01)
    assert summary.snippet_avg_rating == pytest.approx(2.0, rel=0.01)
    assert summary.avg_rating == pytest.approx(3.38, rel=0.01)
    assert summary.positive_pct == 50.0
    assert summary.negative_pct == 50.0
    assert summary.neutral_pct == 0.0


def test_sentiment_text_keyword_fallback_no_ratings():
    """When ratings are absent, sentiment uses rule-based keyword scoring."""
    from services.sentiment_service import analyze_sentiment_local

    df = pd.DataFrame([
        {"review_text": "Delicious authentic pasta with crispy garlic bread.", "rating": None},
        {"review_text": "Terrible slow service, greasy and cold food.", "rating": None},
    ])

    summary = analyze_sentiment_local(df)
    assert summary.review_count == 2
    assert summary.avg_rating is None
    assert summary.positive_pct == 50.0
    assert summary.negative_pct == 50.0
    assert summary.neutral_pct == 0.0


def test_extract_complaints_and_appreciated_features():
    """Verify extraction of complaints and praised features with representative quotes."""
    from services.sentiment_service import analyze_sentiment_local

    df = pd.DataFrame([
        {"review_text": "The pizza had a wonderfully crispy and fresh crust. Delicious flavor!"},
        {"review_text": "Staff was friendly and welcoming. Great atmosphere."},
        {"review_text": "The soup was way too salty and over-seasoned. Very greasy garlic knots."},
        {"review_text": "Slow service with 45 minutes of waiting time."},
    ])

    summary = analyze_sentiment_local(df)
    complaint_themes = [c["theme"] for c in summary.complaints]
    praise_themes = [p["theme"] for p in summary.appreciated_features]

    # Compliments should include fresh/crispy or friendly
    assert any("Crispy" in t or "Delicious" in t for t in praise_themes)
    # Complaints should include salty, greasy, or slow
    assert any("Salty" in t or "Greasy" in t or "Slow" in t for t in complaint_themes)

    # Quotes should be exact verbatim quotes from review texts
    for c in summary.complaints:
        if c.get("representative_quote"):
            assert any(c["representative_quote"].strip("…") in row["review_text"] for _, row in df.iterrows())


def test_item_wise_review_insights():
    """Verify item-level insights aggregation."""
    from services.sentiment_service import extract_item_review_insights

    df = pd.DataFrame([
        {"item_name": "Margherita Pizza", "review_text": "Crispy and fresh Margherita pizza!", "rating": 5.0, "is_snippet": False},
        {"item_name": "Margherita Pizza", "review_text": "Delicious Margherita, loved the crust.", "rating": 4.5, "is_snippet": False},
        {"item_name": "Caesar Salad", "review_text": "Caesar salad was way too salty.", "rating": 2.0, "is_snippet": True},
    ])

    insights = extract_item_review_insights(df)
    assert len(insights) >= 2
    pizza_info = next(i for i in insights if i["item_name"] == "Margherita Pizza")
    assert pizza_info["mention_count"] == 2
    assert pizza_info["avg_rating"] == pytest.approx(4.75, rel=0.01)
    assert pizza_info["positive_pct"] == 100.0

    salad_info = next(i for i in insights if i["item_name"] == "Caesar Salad")
    assert salad_info["mention_count"] == 1
    assert salad_info["avg_rating"] == 2.0
    assert salad_info["negative_pct"] == 100.0


def test_review_trends_time_series():
    """Verify monthly review aggregation."""
    from services.sentiment_service import extract_review_trends

    df = pd.DataFrame([
        {"review_date": "2024-01-10", "rating": 5.0, "review_text": "Great pizza!"},
        {"review_date": "2024-01-15", "rating": 4.0, "review_text": "Nice place."},
        {"review_date": "2024-02-12", "rating": 2.0, "review_text": "Slow service."},
    ])

    trends = extract_review_trends(df)
    assert len(trends) == 2
    assert "2024-01" in trends["period"].values
    assert "2024-02" in trends["period"].values
    jan_row = trends[trends["period"] == "2024-01"].iloc[0]
    assert jan_row["total_reviews"] == 2
    assert jan_row["avg_rating"] == pytest.approx(4.5, rel=0.01)

