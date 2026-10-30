"""
Central Multi-Agent Orchestrator.
Performs semantic intent routing, execution event tracking,
context assembly, specialist coordination, and persistent conversation management.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Optional
import pandas as pd

from agent.multi_agent.types import (
    AgentIntent,
    AgentActivityEvent,
    AgentResponse,
    StructuredMenuDraft,
    DesignSpecification,
)
from agent.multi_agent.specialists.menu_consultant import MenuConsultantAgent
from agent.multi_agent.specialists.menu_design import MenuDesignAgent
from agent.multi_agent.specialists.business_intelligence import BusinessIntelligenceAgent
from agent.multi_agent.specialists.customer_voice import CustomerVoiceAgent
from agent.multi_agent.specialists.operations_waste import OperationsWasteAgent
from database import repository as repo
from services.dataset_storage import load_run_dataset
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)


def _get_gemini_client():
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        logger.warning("Could not initialize genai Client: %s", exc)
        return None


class MultiAgentOrchestrator:
    """Central coordinator for specialized restaurant intelligence agents."""

    def __init__(self):
        self.gemini_client = _get_gemini_client()
        self.menu_consultant = MenuConsultantAgent(self.gemini_client)
        self.menu_design = MenuDesignAgent()
        self.bi_agent = BusinessIntelligenceAgent(self.gemini_client)
        self.customer_voice = CustomerVoiceAgent(self.gemini_client)
        self.waste_agent = OperationsWasteAgent(self.gemini_client)

    def classify_intent(self, user_message: str, has_image: bool = False) -> AgentIntent:
        """Heuristic and keyword intent classification."""
        msg = user_message.lower().strip()

        # Image attached with menu intent
        if has_image and any(k in msg for k in ["menu", "extract", "read", "transcribe", "digitize", "item", "price"]):
            return AgentIntent.MENU_CONSULTING

        # Visual design intent
        if any(k in msg for k in ["design", "template", "poster", "visual", "layout", "print", "flyer", "artwork"]):
            return AgentIntent.MENU_DESIGN

        # Menu strategy or creation
        if "menu" in msg and any(k in msg for k in ["create", "generate", "make", "draft", "new", "suggest", "optimize", "review", "audit", "items", "dishes", "recipes", "dessert", "brunch", "dinner", "specials"]):
            return AgentIntent.MENU_CONSULTING

        if any(k in msg for k in ["create menu", "new menu", "make a menu", "draft a menu", "add dishes", "suggest menu", "menu idea", "optimize menu", "menu strategy", "what to remove", "audit menu"]):
            return AgentIntent.MENU_CONSULTING

        # Business intelligence & sales
        if any(k in msg for k in ["sales", "revenue", "ticket", "profit", "margin", "trend", "money", "growth", "performance", "top selling", "underperforming", "why did my"]):
            return AgentIntent.BUSINESS_INTELLIGENCE

        # Customer voice & reviews
        if any(k in msg for k in ["review", "sentiment", "rating", "customer", "complaint", "feedback", "love", "hate", "praise", "opinion"]):
            return AgentIntent.CUSTOMER_VOICE

        # Operations & food waste
        if any(k in msg for k in ["waste", "spoilage", "discard", "trim", "leftover", "inventory", "loss", "spoil"]):
            return AgentIntent.OPERATIONS_WASTE

        # Multi-specialist / comprehensive audit
        if any(k in msg for k in ["audit", "analyze everything", "full report", "comprehensive", "how is my restaurant doing"]):
            return AgentIntent.MULTI_SPECIALIST

        return AgentIntent.GENERAL_INQUIRY

    def process_message(
        self,
        conversation_id: str,
        restaurant_id: int,
        user_message: str,
        run_id: Optional[int] = None,
        attachments: Optional[list[dict]] = None,
        activity_callback: Optional[Callable[[AgentActivityEvent], None]] = None,
    ) -> AgentResponse:
        """Execute intent-driven multi-agent analysis and return structured response."""
        start_time = time.time()
        attachments = attachments or []
        has_image = any(a.get("mime_type", "").startswith("image/") for a in attachments)

        # Retrieve restaurant info
        restaurant = repo.get_restaurant(restaurant_id)
        restaurant_name = restaurant["name"] if restaurant else "Restaurant"
        cuisine = restaurant.get("category") or "Multi-cuisine"

        # Resolve active run datasets if run_id provided
        menu_df = load_run_dataset(run_id, "menu") if run_id else None
        sales_df = load_run_dataset(run_id, "sales") if run_id else None
        reviews_df = load_run_dataset(run_id, "reviews") if run_id else None
        costs_df = load_run_dataset(run_id, "costs") if run_id else None
        waste_records = repo.list_waste_records(run_id) if run_id else []

        # 1. Activity Event: Understanding request
        intent = self.classify_intent(user_message, has_image=has_image)
        events: list[AgentActivityEvent] = []

        def emit(step: str, agent_name: str, message: str, status: str = "running"):
            evt = AgentActivityEvent(step=step, agent_name=agent_name, message=message, status=status)
            events.append(evt)
            if activity_callback:
                activity_callback(evt)

        emit("routing", "Orchestrator", f"Classified user intent as {intent.value.replace('_', ' ').title()}")

        response_content = ""
        specialist_name = "MenuMind Orchestrator"
        tools_called: list[str] = []
        menu_draft: Optional[StructuredMenuDraft] = None
        menu_design = None
        suggested_followups: list[str] = []

        # 2. Dispatch based on intent
        if intent == AgentIntent.MENU_CONSULTING:
            specialist_name = "Menu Consultant Agent"
            emit("analyzing", specialist_name, "Evaluating restaurant concept and culinary balance...")
            tools_called.append("menu_consultant_engine")

            # Check if user wants creation or existing audit
            if any(k in user_message.lower() for k in ["create", "generate", "make a menu", "draft", "new menu"]):
                explanation, menu_draft = self.menu_consultant.create_menu_from_scratch(
                    restaurant_name=restaurant_name,
                    user_brief=user_message,
                    cuisine=cuisine,
                )
                response_content = explanation
                suggested_followups = [
                    "Design a printable menu for this selection",
                    "Add more vegetarian options",
                    "Estimate profit margins for these items",
                ]
            else:
                response_content = self.menu_consultant.analyze_existing_menu(
                    restaurant_name=restaurant_name,
                    menu_df=menu_df,
                    sales_df=sales_df,
                    costs_df=costs_df,
                    reviews_df=reviews_df,
                )
                suggested_followups = [
                    "Which dishes should I reprice?",
                    "Suggest new high-margin items",
                    "Show revenue trends",
                ]

        elif intent == AgentIntent.MENU_DESIGN:
            specialist_name = "Menu Design Agent"
            emit("designing", specialist_name, "Generating thematic artwork and structured menu typography...")
            tools_called.append("thematic_vector_engine")
            tools_called.append("hybrid_html_renderer")

            # Extract or fallback to sample draft
            _, draft_to_design = self.menu_consultant.create_menu_from_scratch(
                restaurant_name=restaurant_name,
                user_brief="Signature dining menu",
                cuisine=cuisine,
            )

            # Determine style
            style = "Modern Minimalist"
            msg_low = user_message.lower()
            if "traditional" in msg_low or "indian" in msg_low or "dhaba" in msg_low:
                style = "Traditional Indian"
            elif "cafe" in msg_low or "bakery" in msg_low or "coffee" in msg_low:
                style = "Cafe & Bakery"
            elif "luxury" in msg_low or "black" in msg_low or "gold" in msg_low:
                style = "Luxury Black & Gold"
            elif "fine dining" in msg_low or "premium" in msg_low:
                style = "Premium Fine Dining"

            spec = DesignSpecification(style=style)
            menu_design = self.menu_design.create_menu_design(
                restaurant_id=restaurant_id,
                restaurant_name=restaurant_name,
                cuisine=cuisine,
                menu_draft=draft_to_design,
                spec=spec,
                conversation_id=conversation_id,
            )

            response_content = (
                f"### Visual Menu Design Generated: {style}\n\n"
                f"I have created a publication-ready **{style}** menu for **{restaurant_name}**.\n\n"
                "- **Typography & Accuracy:** Exact dish names and prices with high-contrast readability.\n"
                "- **Thematic Artwork:** Customized background motifs matching your venue's identity.\n"
                "- **Export Options:** Print-ready HTML, high-res SVG, or interactive editing below.\n\n"
                "You can inspect the live layout preview and make real-time adjustments below."
            )
            menu_draft = draft_to_design
            suggested_followups = [
                "Switch to Luxury Black & Gold style",
                "Switch to Cafe & Bakery style",
                "Edit dish prices in this design",
            ]

        elif intent == AgentIntent.BUSINESS_INTELLIGENCE:
            specialist_name = "Business Intelligence Agent"
            emit("analyzing", specialist_name, "Inspecting sales transactions and margin contribution...")
            tools_called.append("sales_analytics_service")
            tools_called.append("profitability_engine")

            response_content = self.bi_agent.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                sales_df=sales_df,
                menu_df=menu_df,
                costs_df=costs_df,
            )
            suggested_followups = [
                "Which dishes have the highest margin?",
                "What do customer reviews say about my food?",
                "How can I cut food waste?",
            ]

        elif intent == AgentIntent.CUSTOMER_VOICE:
            specialist_name = "Customer Voice Agent"
            emit("analyzing", specialist_name, "Synthesizing guest reviews and sentiment feedback...")
            tools_called.append("sentiment_service")
            tools_called.append("review_item_insights")

            response_content = self.customer_voice.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                reviews_df=reviews_df,
                menu_df=menu_df,
            )
            suggested_followups = [
                "What dishes do customers complain about most?",
                "Show sales trends for praised items",
                "Create a promotional special for top-rated dishes",
            ]

        elif intent == AgentIntent.OPERATIONS_WASTE:
            specialist_name = "Operations & Waste Agent"
            emit("analyzing", specialist_name, "Analyzing kitchen waste logs and inventory velocity risk...")
            tools_called.append("waste_analysis_service")
            tools_called.append("spoilage_risk_engine")

            response_content = self.waste_agent.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                waste_records=waste_records,
                sales_df=sales_df,
                menu_df=menu_df,
                costs_df=costs_df,
            )
            suggested_followups = [
                "Which slow-moving dishes pose the highest spoilage risk?",
                "Suggest recipes to repurpose prep trim",
                "Log a new physical waste record",
            ]

        else:
            # Multi-specialist / General
            specialist_name = "Executive Restaurant Orchestrator"
            emit("synthesizing", specialist_name, "Consulting Business Intelligence and Menu Specialists...")
            tools_called.extend(["bi_specialist", "menu_consultant_specialist"])

            bi_summary = self.bi_agent.answer_query(
                query="Summary of sales and profitability",
                restaurant_name=restaurant_name,
                sales_df=sales_df,
                menu_df=menu_df,
                costs_df=costs_df,
            )

            response_content = (
                f"### Executive Intelligence Brief: {restaurant_name}\n\n"
                f"Welcome to your unified restaurant intelligence workspace. I coordinate our specialized agents:\n"
                f"- **Menu Consultant:** Strategy, pricing, and creating menus from scratch.\n"
                f"- **Menu Designer:** Producing customer-facing visual menu layouts.\n"
                f"- **Business Intelligence:** Revenue velocity, sales ranking, and margin analytics.\n"
                f"- **Customer Voice:** Review trends, customer praise, and friction points.\n"
                f"- **Operations & Waste:** Cutting food waste and mitigating inventory spoilage.\n\n"
                f"{bi_summary}"
            )
            suggested_followups = [
                "Create a new menu for my restaurant",
                "Analyze my customer reviews",
                "How can I reduce food waste?",
            ]

        emit("completed", specialist_name, "Response formulated successfully.", status="completed")
        execution_time = int((time.time() - start_time) * 1000)

        # Log agent run into SQLite ai_agent_runs
        run_log_id = f"arun_{uuid.uuid4().hex[:10]}"
        repo.log_agent_run(
            run_id=run_log_id,
            conversation_id=conversation_id,
            restaurant_id=restaurant_id,
            agent_name=specialist_name,
            intent=intent.value,
            tools_invoked=tools_called,
            status="completed",
            execution_time_ms=execution_time,
        )

        return AgentResponse(
            content=response_content,
            specialist_agent=specialist_name,
            intent=intent,
            tools_called=tools_called,
            activity_events=events,
            menu_draft=menu_draft,
            menu_design=menu_design,
            suggested_followups=suggested_followups,
        )
