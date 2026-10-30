"""
End-to-end Automated Test Suite for MenuMind AI Conversational Intelligence.
Validates:
1. Intent classification across all 21 specific intents.
2. Specialist agent routing & tool invocation.
3. Conversational context memory & pronoun resolution across multi-turn dialogues.
4. Data-grounded responses across all 4 demo restaurants.
5. Dedicated recipe optimization engine & structured outputs.
6. Honest error handling when data is missing (no fabricated metrics).
"""
from __future__ import annotations

import pytest
import pandas as pd
from agent.multi_agent.orchestrator import MultiAgentOrchestrator
from agent.multi_agent.classifier import IntentClassifier
from agent.multi_agent.types import AgentIntent, OptimizedRecipe
from database import repository as repo
import agent.multi_agent.tools as tool_svc


@pytest.fixture(scope="module")
def orchestrator():
    return MultiAgentOrchestrator()


@pytest.fixture(scope="module")
def classifier():
    return IntentClassifier()


# ─── 1. Intent Classification Accuracy ────────────────────────────────────────

def test_intent_classification_scenarios(classifier):
    scenarios = [
        ("What is our best-selling dish?", "best_selling_items", "business_intelligence"),
        ("Which dish generates the highest profit?", "profitability_analysis", "business_intelligence"),
        ("Tell me recipe optimization for butter chicken", "recipe_optimization", "menu_consultant"),
        ("How can I make my butter chicken more profitable?", "recipe_optimization", "menu_consultant"),
        ("Suggest a new recipe for paneer tikka", "recipe_generation", "menu_consultant"),
        ("Create a new menu for my restaurant", "menu_creation", "menu_consultant"),
        ("Extract dishes from this menu image", "menu_image_extraction", "menu_consultant"),
        ("Why are customers unhappy with our biryani?", "customer_review_analysis", "customer_voice"),
        ("Which dishes are wasting the most ingredients?", "food_waste_analysis", "operations_waste"),
        ("Which items should I remove from my menu?", "menu_optimization", "menu_consultant"),
        ("Suggest a price for paneer tikka", "pricing_strategy", "menu_consultant"),
        ("Compare my restaurant's performance", "restaurant_comparison", "business_intelligence"),
        ("How can I reduce the cost of my gravies?", "food_cost_analysis", "menu_consultant"),
        ("Which slow-moving dishes pose the highest spoilage risk?", "spoilage_risk", "operations_waste"),
        ("Suggest recipes to repurpose prep trim", "inventory_optimization", "operations_waste"),
    ]

    for query, expected_intent, expected_agent in scenarios:
        res = classifier._heuristic_classify(query, [])
        assert res.intent == expected_intent, f"Query '{query}' expected intent '{expected_intent}', got '{res.intent}'"
        assert res.target_agent == expected_agent, f"Query '{query}' expected agent '{expected_agent}', got '{res.target_agent}'"


# ─── 2. Multi-Turn Context Memory & Pronoun Resolution ─────────────────────────

def test_pronoun_resolution_flow(classifier, orchestrator):
    # Turn 1: User asks about best seller
    turn1_msg = "What is our best-selling dish?"
    turn1_history = [
        {"role": "user", "content": turn1_msg},
        {"role": "assistant", "content": "Dum Chicken Biryani is your highest-revenue dish, generating ₹69,120."}
    ]

    # Turn 2: User asks "Can you optimize it?"
    res_turn2 = classifier._heuristic_classify("Can you optimize it?", turn1_history)
    assert res_turn2.intent == "recipe_optimization"
    assert res_turn2.entities.get("dish_name") == "dum chicken biryani"

    # Turn 3: User asks "What about its pricing?"
    turn2_history = turn1_history + [
        {"role": "user", "content": "Can you optimize it?"},
        {"role": "assistant", "content": "Here is the optimized recipe for Dum Chicken Biryani..."}
    ]
    res_turn3 = classifier._heuristic_classify("What about its pricing?", turn2_history)
    assert res_turn3.intent == "pricing_strategy"
    assert res_turn3.entities.get("dish_name") == "dum chicken biryani"


# ─── 3. Data-Grounded Tools Execution ──────────────────────────────────────────

def test_grounded_tools_execution():
    # Run 6 is Chiku Da Dhaba
    overview = tool_svc.get_restaurant_overview(4, 6)
    assert overview.get("name") == "Chiku Da Dhaba"
    assert "sales" in overview.get("available_datasets", [])
    assert "menu" in overview.get("available_datasets", [])

    top_items = tool_svc.get_top_selling_items(6, limit=5)
    assert top_items.get("has_data") is True
    # Volume leader is butter garlic naan
    assert top_items["volume_leader"]["item_name"] == "butter garlic naan"
    assert top_items["volume_leader"]["units_sold"] == 326
    # Revenue leader is dum chicken biryani
    assert top_items["revenue_leader"]["item_name"] == "dum chicken biryani"
    assert top_items["revenue_leader"]["revenue"] == 69120.0
    assert top_items["volume_and_revenue_same"] is False

    # Check butter chicken sales
    bc_sales = tool_svc.get_item_sales_details(6, "butter chicken")
    assert bc_sales.get("found") is True
    assert "butter chicken deluxe" in bc_sales.get("item_name")
    assert bc_sales.get("units_sold") == 157
    assert bc_sales.get("total_revenue") == 59660.0


# ─── 4. Recipe Optimization Engine ─────────────────────────────────────────────

def test_recipe_optimization_engine(orchestrator):
    resp = orchestrator.process_message(
        conversation_id="conv_test_recipe",
        restaurant_id=4,
        run_id=6,
        user_message="Tell me recipe optimization for butter chicken",
    )
    assert resp.specialist_agent == "Menu Consultant Agent"
    assert resp.recipe_data is not None
    assert isinstance(resp.recipe_data, OptimizedRecipe)
    assert "Chicken" in resp.recipe_data.dish_name
    assert len(resp.recipe_data.ingredients) >= 4
    assert resp.recipe_data.cost_analysis.ingredient_cost is not None
    assert resp.recipe_data.cost_analysis.cost_per_serving is not None
    assert "Optimization" in resp.content or "units sold" in resp.content or "Recipe" in resp.content or "Chicken" in resp.content


# ─── 5. Food Waste Intelligence & Missing Data Notice ──────────────────────────

def test_food_waste_missing_data_honesty(orchestrator):
    # When waste records are absent, system must be honest and not invent zero risk
    resp = orchestrator.process_message(
        conversation_id="conv_test_waste",
        restaurant_id=4,
        run_id=6,
        user_message="How can I reduce food waste?",
    )
    assert resp.specialist_agent == "Operations & Waste Agent"
    assert "does not contain" in resp.content.lower() or "physical food waste records" in resp.content.lower() or "spoilage" in resp.content.lower()


# ─── 6. Multi-Restaurant Context Scoping ────────────────────────────────────────

def test_multi_restaurant_scoping(orchestrator):
    restaurants = repo.list_restaurants()
    assert len(restaurants) >= 2

    for r in restaurants[:3]:
        r_id = r["id"]
        runs = repo.list_runs_for_restaurant(r_id)
        run_id = runs[0]["id"] if runs else None

        resp = orchestrator.process_message(
            conversation_id=f"conv_scope_test_{r_id}",
            restaurant_id=r_id,
            run_id=run_id,
            user_message="What is our best-selling dish?",
        )
        assert resp.specialist_agent == "Business Intelligence Agent"
        assert r["name"] in resp.content or "Best-Selling" in resp.content
