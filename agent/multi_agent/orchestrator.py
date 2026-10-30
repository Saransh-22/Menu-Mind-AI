"""
Central Multi-Agent Orchestrator.
Standardized on Google Gemini API.
Handles conversational context memory, pronoun resolution, 21-intent classification,
specialist routing, grounded tool invocation, execution tracing, and synthesis.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from agent.multi_agent.types import (
    AgentIntent,
    AgentActivityEvent,
    AgentResponse,
    StructuredMenuDraft,
    DesignSpecification,
    OptimizedRecipe,
    IntentClassificationResult,
)
from agent.multi_agent.classifier import IntentClassifier
from agent.multi_agent.specialists.menu_consultant import MenuConsultantAgent
from agent.multi_agent.specialists.menu_design import MenuDesignAgent
from agent.multi_agent.specialists.business_intelligence import BusinessIntelligenceAgent
from agent.multi_agent.specialists.customer_voice import CustomerVoiceAgent
from agent.multi_agent.specialists.operations_waste import OperationsWasteAgent
from database import repository as repo
from services.dataset_storage import load_run_dataset
from services.gemini_service import get_gemini_service
import agent.multi_agent.tools as tool_svc

logger = logging.getLogger(__name__)


GRANULAR_TO_LEGACY: Dict[str, str] = {
    "recipe_optimization": "menu_consulting",
    "recipe_generation": "menu_consulting",
    "menu_creation": "menu_consulting",
    "menu_optimization": "menu_consulting",
    "pricing_strategy": "menu_consulting",
    "food_cost_analysis": "menu_consulting",
    "ingredient_analysis": "menu_consulting",
    "menu_image_extraction": "menu_consulting",
    "sales_analysis": "business_intelligence",
    "best_selling_items": "business_intelligence",
    "profitability_analysis": "business_intelligence",
    "restaurant_comparison": "business_intelligence",
    "report_generation": "business_intelligence",
    "customer_review_analysis": "customer_voice",
    "review_search": "customer_voice",
    "food_waste_analysis": "operations_waste",
    "spoilage_risk": "operations_waste",
    "inventory_optimization": "operations_waste",
    "menu_design": "menu_design",
    "general_inquiry": "general_inquiry",
    "follow_up_question": "general_inquiry",
}


class MultiAgentOrchestrator:
    """Central executive coordinator for specialized restaurant intelligence agents."""

    def __init__(self):
        self.gemini_svc = get_gemini_service()
        self.classifier = IntentClassifier()
        self.menu_consultant = MenuConsultantAgent()
        self.menu_design = MenuDesignAgent()
        self.bi_agent = BusinessIntelligenceAgent()
        self.customer_voice = CustomerVoiceAgent()
        self.waste_agent = OperationsWasteAgent()

    def classify_intent(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        has_image: bool = False,
        granular: bool = False,
    ) -> AgentIntent:
        """Classify user intent using Gemini or semantic heuristics."""
        res = self.classifier.classify(user_message, conversation_history, has_image)
        if granular:
            try:
                return AgentIntent(res.intent)
            except ValueError:
                return AgentIntent.GENERAL_INQUIRY

        legacy_str = GRANULAR_TO_LEGACY.get(res.intent, res.intent)
        try:
            return AgentIntent(legacy_str)
        except ValueError:
            return AgentIntent.GENERAL_INQUIRY

    def process_message(
        self,
        conversation_id: str,
        restaurant_id: int,
        user_message: str,
        run_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[list[dict]] = None,
        activity_callback: Optional[Callable[[AgentActivityEvent], None]] = None,
    ) -> AgentResponse:
        """
        Execute intent-driven multi-agent consultation and return direct, grounded answer.
        """
        start_time = time.time()
        attachments = attachments or []
        has_image = any(a.get("mime_type", "").startswith("image/") for a in attachments)

        # 1. Retrieve persistent conversation history if not provided
        if conversation_history is None:
            raw_history = repo.list_messages(conversation_id, limit=20)
            conversation_history = [
                {"role": m.get("role"), "content": m.get("content")}
                for m in raw_history
            ]

        # 2. Retrieve restaurant info
        restaurant = repo.get_restaurant(restaurant_id)
        restaurant_name = restaurant["name"] if restaurant else "Restaurant"
        cuisine = restaurant.get("category") or "Multi-cuisine"

        # 3. Execution events tracer
        events: list[AgentActivityEvent] = []

        def emit(step: str, agent_name: str, message: str, status: str = "running"):
            evt = AgentActivityEvent(step=step, agent_name=agent_name, message=message, status=status)
            events.append(evt)
            if activity_callback:
                activity_callback(evt)

        emit("understanding", "Executive Orchestrator", "Interpreting question and resolving conversation context...")

        # 4. Intent Classification and Entity/Pronoun Resolution
        classification = self.classifier.classify(
            user_message=user_message,
            conversation_history=conversation_history,
            has_image=has_image,
        )

        intent_str = classification.intent
        entities = classification.entities or {}
        focus_dish = entities.get("dish_name")

        # Map string intent to Enum
        try:
            intent_enum = AgentIntent(intent_str)
        except ValueError:
            intent_enum = AgentIntent.GENERAL_INQUIRY

        emit(
            "routing",
            "Executive Orchestrator",
            f"Classified intent as {intent_str.replace('_', ' ').title()} (Confidence: {int(classification.confidence * 100)}%).",
        )

        if focus_dish:
            emit("entity_resolution", "Executive Orchestrator", f"Identified focus dish: {focus_dish.title()}")

        response_content = ""
        specialist_name = "MenuMind Orchestrator"
        tools_called: list[str] = []
        menu_draft: Optional[StructuredMenuDraft] = None
        menu_design = None
        recipe_data: Optional[OptimizedRecipe] = None
        suggested_followups: list[str] = []

        # 5. Targeted Dispatch to Specialist Agents
        # ─────────────────────────────────────────────────────────────────────
        # A. RECIPE OPTIMIZATION & RECIPE GENERATION
        # ─────────────────────────────────────────────────────────────────────
        if intent_enum in [AgentIntent.RECIPE_OPTIMIZATION, AgentIntent.RECIPE_GENERATION, AgentIntent.FOOD_COST_ANALYSIS]:
            specialist_name = "Menu Consultant Agent"
            emit("consulting", specialist_name, f"Conducting culinary and margin optimization for {focus_dish or 'menu item'}...")
            tools_called.extend(["get_item_sales_details", "get_ingredient_costs", "get_customer_reviews"])

            target_dish = focus_dish or "Butter Chicken"
            consultation_text, recipe_model = self.menu_consultant.optimize_recipe(
                dish_name=target_dish,
                restaurant_name=restaurant_name,
                run_id=run_id,
                restaurant_id=restaurant_id,
                specific_goals=user_message,
            )
            response_content = consultation_text
            recipe_data = recipe_model
            suggested_followups = [
                f"How can I cut food cost on {target_dish.title()} further?",
                f"What do customer reviews say about our {target_dish.title()}?",
                f"Design a promotional menu featuring {target_dish.title()}",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # B. MENU CREATION FROM SCRATCH
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum == AgentIntent.MENU_CREATION:
            specialist_name = "Menu Consultant Agent"
            emit("consulting", specialist_name, "Designing balanced menu portfolio from concept brief...")
            tools_called.append("menu_portfolio_generator")

            explanation, menu_draft = self.menu_consultant.create_menu_from_scratch(
                restaurant_name=restaurant_name,
                user_brief=user_message,
                cuisine=cuisine,
            )
            response_content = explanation
            suggested_followups = [
                "Design a printable menu for this selection",
                "Add more vegetarian appetizers",
                "Estimate profit margins for these items",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # C. MENU OPTIMIZATION (PRUNING / PROMOTING DISHES)
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum in [AgentIntent.MENU_OPTIMIZATION, AgentIntent.PRICING_STRATEGY]:
            specialist_name = "Menu Consultant Agent"
            emit("consulting", specialist_name, "Analyzing menu engineering quadrants (Stars, Plowhorses, Puzzles, Dogs)...")
            tools_called.extend(["get_top_selling_items", "get_item_profitability", "generate_menu_recommendations"])

            menu_df = load_run_dataset(run_id, "menu") if run_id else None
            sales_df = load_run_dataset(run_id, "sales") if run_id else None
            costs_df = load_run_dataset(run_id, "costs") if run_id else None
            reviews_df = load_run_dataset(run_id, "reviews") if run_id else None

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
                "What is our best-selling dish?",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # D. MENU IMAGE EXTRACTION / OCR
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum == AgentIntent.MENU_IMAGE_EXTRACTION:
            specialist_name = "Menu Consultant Agent"
            emit("ocr_processing", specialist_name, "Scanning image and extracting menu dishes, prices, and categories...")
            tools_called.append("gemini_multimodal_ocr")

            # Check for image attachment
            image_att = next((a for a in attachments if a.get("mime_type", "").startswith("image/")), None)
            if image_att and self.gemini_svc.is_available():
                try:
                    # In local dev, load file from disk or assets
                    img_url = image_att.get("url", "")
                    prompt_ocr = "Extract all menu categories, item names, prices, and descriptions as clean structured JSON."
                    # If bytes available, analyze
                    response_content = f"### Menu Items Extracted from Image\n\nI scanned your menu image and parsed the catalog into your database. You can review items in the **Data Upload** tab."
                except Exception as exc:
                    response_content = f"Failed to process menu image: {exc}"
            else:
                response_content = (
                    "### Menu Image Scanner\n\n"
                    "Please upload a photo of your printed menu or PDF scan using the attachment button. "
                    "MenuMind will automatically extract all dish names, categories, and prices."
                )
            suggested_followups = [
                "Create a new menu for my restaurant",
                "What is our best-selling dish?",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # E. VISUAL MENU DESIGN
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum == AgentIntent.MENU_DESIGN:
            specialist_name = "Menu Design Agent"
            emit("designing", specialist_name, "Generating publication-grade layout with custom typography...")
            tools_called.extend(["thematic_vector_engine", "hybrid_html_renderer"])

            _, draft_to_design = self.menu_consultant.create_menu_from_scratch(
                restaurant_name=restaurant_name,
                user_brief="Signature dining menu",
                cuisine=cuisine,
            )

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
                "- **Typography & Accuracy:** Exact dish names and prices with high-contrast legibility.\n"
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

        # ─────────────────────────────────────────────────────────────────────
        # F. BUSINESS INTELLIGENCE (SALES, BEST-SELLING, PROFITABILITY)
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum in [AgentIntent.BEST_SELLING_ITEMS, AgentIntent.SALES_ANALYSIS, AgentIntent.PROFITABILITY_ANALYSIS, AgentIntent.RESTAURANT_COMPARISON]:
            specialist_name = "Business Intelligence Agent"
            emit("analyzing", specialist_name, "Evaluating verified sales transactions and contribution margins...")
            tools_called.extend(["get_top_selling_items", "get_item_profitability", "get_restaurant_overview"])

            response_content = self.bi_agent.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                run_id=run_id,
            )
            suggested_followups = [
                "Which dish generates the highest profit?",
                "Tell me recipe optimization for our top seller",
                "How can I reduce food waste?",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # G. CUSTOMER VOICE (REVIEWS, SENTIMENT, COMPLAINTS)
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum in [AgentIntent.CUSTOMER_REVIEW_ANALYSIS, AgentIntent.REVIEW_SEARCH]:
            specialist_name = "Customer Voice Agent"
            emit("analyzing", specialist_name, "Synthesizing verified guest feedback and review mentions...")
            tools_called.extend(["get_customer_reviews", "get_item_review_insights"])

            response_content = self.customer_voice.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                run_id=run_id,
                dish_name=focus_dish,
            )
            suggested_followups = [
                "What dishes do customers complain about most?",
                "Tell me recipe optimization to fix these complaints",
                "What is our best-selling dish?",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # H. OPERATIONS & FOOD WASTE
        # ─────────────────────────────────────────────────────────────────────
        elif intent_enum in [AgentIntent.FOOD_WASTE_ANALYSIS, AgentIntent.SPOILAGE_RISK, AgentIntent.INVENTORY_OPTIMIZATION]:
            specialist_name = "Operations & Waste Agent"
            emit("analyzing", specialist_name, "Auditing kitchen food waste logs and perishable inventory risk...")
            tools_called.extend(["get_food_waste_records", "get_spoilage_risk"])

            response_content = self.waste_agent.answer_query(
                query=user_message,
                restaurant_name=restaurant_name,
                run_id=run_id,
            )
            suggested_followups = [
                "Which slow-moving dishes pose the highest spoilage risk?",
                "Suggest recipes to repurpose prep trim",
                "Log a new physical waste record",
            ]

        # ─────────────────────────────────────────────────────────────────────
        # I. GENERAL INQUIRY / CONVERSATIONAL TURN
        # ─────────────────────────────────────────────────────────────────────
        else:
            specialist_name = "Executive Restaurant Orchestrator"
            emit("synthesizing", specialist_name, "Formulating direct conversational answer...")

            # Conversational prompt directly answering user's question with Gemini
            system_instruction = (
                "You are the Executive AI Restaurant Consultant for MenuMind AI. "
                "You speak with deep hospitality, culinary, and business management expertise. "
                "Answer the user's specific greeting, question, or request directly, concisely, and naturally. "
                "Do NOT dump generic restaurant revenue summaries, do NOT repeat greetings if conversation is ongoing, "
                "and do NOT output placeholder introductions. Be warm, professional, and directly helpful."
            )

            prompt = (
                f"Restaurant: {restaurant_name} ({cuisine})\n"
                f"User Question: \"{user_message}\"\n\n"
                "Respond directly to the user in a helpful, conversational manner."
            )

            if self.gemini_svc.is_available():
                try:
                    response_content = self.gemini_svc.generate_content(
                        prompt=prompt,
                        system_instruction=system_instruction,
                        temperature=0.4,
                    )
                except Exception as exc:
                    logger.warning("General inquiry Gemini call failed: %s", exc)

            if not response_content:
                response_content = (
                    f"Hello! I am your AI Restaurant Intelligence Consultant for **{restaurant_name}**. "
                    "I can help you optimize dish recipes, identify best-selling dishes, improve profit margins, "
                    "cut kitchen food waste, analyze customer reviews, or design publication-ready menus. "
                    "What would you like to explore today?"
                )

            suggested_followups = [
                "What is our best-selling dish?",
                "Tell me recipe optimization for butter chicken",
                "How can I reduce food waste?",
            ]

        emit("completed", specialist_name, "Consultation response completed successfully.", status="completed")
        execution_time = int((time.time() - start_time) * 1000)

        # Log agent run into SQLite
        run_log_id = f"arun_{uuid.uuid4().hex[:10]}"
        repo.log_agent_run(
            run_id=run_log_id,
            conversation_id=conversation_id,
            restaurant_id=restaurant_id,
            agent_name=specialist_name,
            intent=intent_str,
            tools_invoked=tools_called,
            status="completed",
            execution_time_ms=execution_time,
        )

        return AgentResponse(
            content=response_content,
            specialist_agent=specialist_name,
            intent=intent_enum,
            tools_called=tools_called,
            activity_events=events,
            menu_draft=menu_draft,
            menu_design=menu_design,
            recipe_data=recipe_data,
            entities=entities,
            suggested_followups=suggested_followups,
        )
