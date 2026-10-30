"""
Unit tests for the MenuMind AI Multi-Agent Architecture.
Covers Orchestrator intent classification, specialist routing, heuristic fallbacks,
menu generation, and visual design layout rendering.
"""
from __future__ import annotations

import pytest
import pandas as pd
from agent.multi_agent.orchestrator import MultiAgentOrchestrator
from agent.multi_agent.types import (
    AgentIntent,
    StructuredMenuDraft,
    StructuredMenuCategory,
    StructuredMenuItem,
    DesignSpecification,
)
from agent.multi_agent.specialists.menu_consultant import MenuConsultantAgent
from agent.multi_agent.specialists.menu_design import MenuDesignAgent
from agent.multi_agent.specialists.business_intelligence import BusinessIntelligenceAgent
from agent.multi_agent.specialists.customer_voice import CustomerVoiceAgent
from agent.multi_agent.specialists.operations_waste import OperationsWasteAgent
from database import repository as repo


@pytest.fixture
def orchestrator():
    return MultiAgentOrchestrator()


def test_orchestrator_intent_classification(orchestrator):
    assert orchestrator.classify_intent("Create a new 5-item dessert menu for our cafe") == AgentIntent.MENU_CONSULTING
    assert orchestrator.classify_intent("Review our dishes and tell me what to remove") == AgentIntent.MENU_CONSULTING
    assert orchestrator.classify_intent("Generate a visual publication layout for our brunch menu") == AgentIntent.MENU_DESIGN
    assert orchestrator.classify_intent("What is our total revenue and profit margin this month?") == AgentIntent.BUSINESS_INTELLIGENCE
    assert orchestrator.classify_intent("Summarize customer reviews and complaints about the pasta") == AgentIntent.CUSTOMER_VOICE
    assert orchestrator.classify_intent("Which dishes have high spoilage and kitchen waste risk?") == AgentIntent.OPERATIONS_WASTE
    assert orchestrator.classify_intent("Hello, can you help me?") == AgentIntent.GENERAL_INQUIRY


def test_menu_consultant_heuristic_generation():
    agent = MenuConsultantAgent()
    draft = agent._generate_fallback_menu(
        restaurant_name="Test Cafe",
        user_brief="Artisanal Espresso & Breakfast",
        target_bill=300.0,
        currency="₹",
    )
    assert isinstance(draft, StructuredMenuDraft)
    assert draft.total_items >= 4
    assert len(draft.categories) > 0
    assert all(it.price > 0 for cat in draft.categories for it in cat.items)


def test_menu_design_rendering():
    designer = MenuDesignAgent()
    draft = StructuredMenuDraft(
        title="Bistro Special Selection",
        concept="French Bistro Classics",
        currency="₹",
        categories=[
            StructuredMenuCategory(
                category="Starters",
                items=[
                    StructuredMenuItem(name="French Onion Soup", category="Starters", price=280.0, description="Caramelized onions with gruyere."),
                    StructuredMenuItem(name="Truffle Fries", category="Starters", price=220.0, description="Hand-cut russets with parmesan."),
                ]
            ),
            StructuredMenuCategory(
                category="Mains",
                items=[
                    StructuredMenuItem(name="Steak Frites", category="Mains", price=650.0, description="Prime tenderloin with herb butter."),
                ]
            )
        ],
        total_items=3,
        indicative_avg_bill=380.0,
    )

    design = designer.create_menu_design(
        restaurant_id=4,
        restaurant_name="Bistro Parisien",
        cuisine="French",
        menu_draft=draft,
        spec=DesignSpecification(style="Cafe & Bakery", layout="two_column"),
    )

    assert design.title == "Bistro Special Selection"
    assert "Cafe & Bakery" in design.style or design.spec.style == "Cafe & Bakery"
    assert design.menu_draft.total_items == 3
    assert "French Onion Soup" in design.html_preview
    assert "280" in design.html_preview


def test_business_intelligence_deterministic():
    agent = BusinessIntelligenceAgent()
    # Provide synthetic data
    sales_df = pd.DataFrame([
        {"item_name": "Chicken Tikka", "category": "Mains", "quantity": 10, "selling_price": 300.0, "total_revenue": 3000.0, "date": "2026-10-01"}
    ])
    menu_df = pd.DataFrame([
        {"item_name": "Chicken Tikka", "category": "Mains", "price": 300.0}
    ])
    costs_df = pd.DataFrame([
        {"item_name": "Chicken Tikka", "unit_cost": 120.0}
    ])

    resp = agent.answer_query(
        query="What is our total revenue and best seller?",
        restaurant_name="Chiku Da Dhaba",
        sales_df=sales_df,
        menu_df=menu_df,
        costs_df=costs_df,
    )
    assert "3,000" in resp or "Chicken Tikka" in resp or "Revenue" in resp


def test_customer_voice_insights():
    agent = CustomerVoiceAgent()
    reviews_df = pd.DataFrame([
        {"item_name": "Chicken Tikka", "review_text": "Incredible chicken tikka, succulent and perfectly spiced!", "rating": 5.0}
    ])
    menu_df = pd.DataFrame([
        {"item_name": "Chicken Tikka", "category": "Mains", "price": 300.0}
    ])

    resp = agent.answer_query(
        query="What are customers saying about our dishes?",
        restaurant_name="Chiku Da Dhaba",
        reviews_df=reviews_df,
        menu_df=menu_df,
    )
    assert len(resp) > 20
    assert "Chicken Tikka" in resp or "Customer" in resp or "Review" in resp or "rating" in resp.lower()


def test_operations_waste_insights():
    agent = OperationsWasteAgent()
    waste_records = [
        {"ingredient_name": "Onions", "quantity": 5, "unit": "kg", "unit_cost": 25.0, "waste_reason": "spoilage"}
    ]
    sales_df = pd.DataFrame([
        {"item_name": "Onion Salad", "category": "Sides", "quantity": 2, "selling_price": 50.0, "total_revenue": 100.0, "date": "2026-10-01"}
    ])
    menu_df = pd.DataFrame([
        {"item_name": "Onion Salad", "category": "Sides", "price": 50.0}
    ])
    costs_df = pd.DataFrame([
        {"item_name": "Onion Salad", "unit_cost": 20.0}
    ])

    resp = agent.answer_query(
        query="Which items have high waste risk?",
        restaurant_name="Chiku Da Dhaba",
        waste_records=waste_records,
        sales_df=sales_df,
        menu_df=menu_df,
        costs_df=costs_df,
    )
    assert len(resp) > 20
    assert "waste" in resp.lower() or "measured" in resp.lower() or "exposure" in resp.lower()
