"""
Intelligent Intent Classifier and Conversational Context Resolver.
Leverages Gemini with structured JSON output and Pydantic validation.
Handles natural language nuances, spelling errors, entity extraction, and pronoun resolution.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from agent.multi_agent.types import AgentIntent, IntentClassificationResult
from services.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

INTENT_AGENT_MAP: Dict[str, str] = {
    # Menu Consultant
    "menu_optimization": "menu_consultant",
    "recipe_optimization": "menu_consultant",
    "recipe_generation": "menu_consultant",
    "menu_creation": "menu_consultant",
    "pricing_strategy": "menu_consultant",
    "food_cost_analysis": "menu_consultant",
    "ingredient_analysis": "menu_consultant",
    "menu_image_extraction": "menu_consultant",
    "menu_consulting": "menu_consultant",

    # Business Intelligence
    "sales_analysis": "business_intelligence",
    "best_selling_items": "business_intelligence",
    "profitability_analysis": "business_intelligence",
    "restaurant_comparison": "business_intelligence",
    "report_generation": "business_intelligence",
    "business_intelligence": "business_intelligence",

    # Customer Voice
    "customer_review_analysis": "customer_voice",
    "review_search": "customer_voice",
    "customer_voice": "customer_voice",

    # Operations & Waste
    "food_waste_analysis": "operations_waste",
    "spoilage_risk": "operations_waste",
    "inventory_optimization": "operations_waste",
    "operations_waste": "operations_waste",

    # Menu Designer
    "menu_design": "menu_designer",

    # Orchestrator
    "general_inquiry": "orchestrator",
    "follow_up_question": "orchestrator",
    "multi_specialist": "orchestrator",
}


class IntentClassifier:
    """Classifies user intent, resolves conversational pronouns, and identifies target agent."""

    def __init__(self):
        self.gemini_svc = get_gemini_service()

    def classify(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        has_image: bool = False,
        force_llm: bool = False,
    ) -> IntentClassificationResult:
        """
        Classify intent using semantic understanding.
        Evaluates unambiguous domain queries instantly; uses Gemini for nuanced/conversational queries.
        """
        history_snippet = self._format_history(conversation_history or [])
        dish_from_history = self._extract_dish_from_history(conversation_history or [])

        # Fast-path unambiguous queries
        heuristic_res = self._heuristic_classify(user_message, conversation_history or [], has_image)
        if not force_llm and heuristic_res.confidence >= 0.94:
            return heuristic_res

        # 1. Attempt Gemini classification for conversational/ambiguous queries
        if self.gemini_svc.is_available():
            try:
                system_instruction = (
                    "You are the Chief Intent Classifier for MenuMind AI, an agentic restaurant intelligence platform.\n"
                    "Your job is to accurately classify the user's message into EXACTLY ONE of the supported intents.\n"
                    "Supported Intents:\n"
                    "1. general_inquiry: General greetings, asking how the assistant works, small talk.\n"
                    "2. sales_analysis: High-level sales revenue, daily/monthly volume, trends.\n"
                    "3. best_selling_items: Identifying top sellers by volume (units sold) or gross revenue.\n"
                    "4. profitability_analysis: Margin %, profit contribution, high/low margin dishes.\n"
                    "5. menu_optimization: Menu engineering, identifying what dishes to prune/remove/promote.\n"
                    "6. recipe_optimization: Improving existing recipes, portioning, taste, cutting recipe costs.\n"
                    "7. recipe_generation: Creating brand new recipes from scratch or culinary ideation.\n"
                    "8. menu_creation: Building a new restaurant menu from scratch with sections and pricing.\n"
                    "9. menu_image_extraction: OCR, digitizing, or reading food items/prices from an uploaded menu image/PDF.\n"
                    "10. menu_design: Visual layout, graphic styling, typography, printable menu templates.\n"
                    "11. pricing_strategy: Suggesting price points for specific dishes or price elasticity.\n"
                    "12. customer_review_analysis: Review sentiment, customer complaints, dish mentions in reviews.\n"
                    "13. review_search: Fetching external Google/SerpApi reviews from the web.\n"
                    "14. food_waste_analysis: Kitchen food waste logs, discard costs, waste reduction methods.\n"
                    "15. spoilage_risk: Slow-moving ingredients/dishes vulnerable to expiry/spoilage.\n"
                    "16. inventory_optimization: Par levels, inventory turnover, stock ordering efficiency.\n"
                    "17. ingredient_analysis: Cross-utilization of ingredients, substitutes, procurement.\n"
                    "18. food_cost_analysis: Gravy/base sauce cost reduction, batch prep ingredient savings.\n"
                    "19. report_generation: Generating full restaurant PDF/HTML summary reports.\n"
                    "20. restaurant_comparison: Comparing venue performance against sister outlets or benchmarks.\n"
                    "21. follow_up_question: Direct continuation of previous turn (e.g. 'Can you improve it?').\n\n"
                    "Context Resolution Rule:\n"
                    "If the user uses pronouns like 'it', 'this dish', 'its pricing', 'optimize it', resolve the referent "
                    "from previous turns and populate entities.dish_name accordingly."
                )

                prompt = (
                    f"Recent Conversation History:\n{history_snippet or 'None'}\n\n"
                    f"Attached Image: {'Yes' if has_image else 'No'}\n"
                    f"User Message: \"{user_message}\"\n\n"
                    "Classify this message and extract relevant entities (e.g., dish_name, target_style, category).\n"
                    "Include fields: intent, confidence, target_agent (one of 'menu_consultant', 'business_intelligence', 'customer_voice', 'operations_waste', 'menu_designer', 'orchestrator'), entities, requires_database, requires_tool_call, response_mode.\n"
                    "Return ONLY a valid JSON object matching the IntentClassificationResult schema."
                )

                result = self.gemini_svc.generate_json(
                    prompt=prompt,
                    schema=IntentClassificationResult,
                    system_instruction=system_instruction,
                    temperature=0.1,
                )

                # Ensure target_agent is populated correctly
                mapped_agent = INTENT_AGENT_MAP.get(result.intent)
                if mapped_agent:
                    result.target_agent = mapped_agent

                # If pronoun resolution missed dish_name, inject from history
                if not result.entities.get("dish_name") and dish_from_history:
                    if any(p in user_message.lower().split() for p in ["it", "its", "this", "that", "dish"]):
                        result.entities["dish_name"] = dish_from_history

                return result
            except Exception as exc:
                logger.warning("Gemini classification failed; falling back to heuristic: %s", exc)

        # 2. Comprehensive semantic heuristic classification
        return self._heuristic_classify(user_message, conversation_history or [], has_image)

    def _heuristic_classify(
        self,
        message: str,
        history: List[Dict[str, Any]],
        has_image: bool = False,
    ) -> IntentClassificationResult:
        """Robust semantic heuristic fallback for classification and pronoun resolution."""
        msg = message.lower().strip()
        dish_from_history = self._extract_dish_from_history(history)

        # Extract potential dish names directly from query
        extracted_dish = None
        dish_candidates = [
            "dum chicken biryani", "butter chicken deluxe", "paneer butter masala",
            "butter garlic naan", "paneer tikka angara", "truffle tagliatelle",
            "butter chicken", "chicken biryani", "paneer tikka", "dal makhani",
            "biryani", "naan", "chaas", "tandoori chicken", "masala dosa", "burger", "pizza", "pasta", "salad",
        ]
        dish_candidates.sort(key=len, reverse=True)
        for dish in dish_candidates:
            if dish in msg:
                extracted_dish = dish
                break

        # Check for pronoun reference
        has_pronoun = bool(re.search(r"\b(it|its|this|that|this dish|the dish)\b", msg))
        if has_pronoun and not extracted_dish and dish_from_history:
            extracted_dish = dish_from_history

        # 1. Image extraction
        if has_image or any(k in msg for k in ["extract dishes", "menu image", "extract from this image", "scan menu", "digitize menu", "read menu photo"]):
            return IntentClassificationResult(
                intent="menu_image_extraction",
                confidence=0.95,
                target_agent="menu_consultant",
                entities={"dish_name": extracted_dish} if extracted_dish else {},
                requires_database=False,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 2. Recipe generation (creating new recipes)
        if any(k in msg for k in ["suggest a new recipe", "create a recipe", "recipe generation", "new recipe", "give me a recipe"]):
            return IntentClassificationResult(
                intent="recipe_generation",
                confidence=0.96,
                target_agent="menu_consultant",
                entities={"dish_name": extracted_dish or "Special Dish"},
                requires_database=False,
                requires_tool_call=False,
                response_mode="detailed_consultation",
            )

        # 3. Recipe optimization (improving existing recipes)
        if any(k in msg for k in ["recipe optimization", "optimize recipe", "optimize the recipe", "recipe improve", "make my recipe", "recipe for"]) or (
            any(k in msg for k in ["optimize", "improve", "more profitable", "increase profit", "profitable", "reduce cost", "cut cost"]) and extracted_dish
        ):
            return IntentClassificationResult(
                intent="recipe_optimization",
                confidence=0.97,
                target_agent="menu_consultant",
                entities={"dish_name": extracted_dish or "Signature Dish"},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 4. Best-selling items
        if any(k in msg for k in ["best-selling", "best selling", "top seller", "top-selling", "highest volume", "highest revenue dish", "most sold"]):
            return IntentClassificationResult(
                intent="best_selling_items",
                confidence=0.98,
                target_agent="business_intelligence",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 5. Profitability analysis
        if any(k in msg for k in ["highest profit", "highest margin", "profitability", "most profitable dish", "margin analysis", "contribution margin"]):
            return IntentClassificationResult(
                intent="profitability_analysis",
                confidence=0.96,
                target_agent="business_intelligence",
                entities={"dish_name": extracted_dish} if extracted_dish else {},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 6. Pricing strategy
        if any(k in msg for k in ["suggest a price", "how should i price", "price for", "pricing strategy", "pricing recommendation", "pricing", "its price", "what price"]):
            return IntentClassificationResult(
                intent="pricing_strategy",
                confidence=0.94,
                target_agent="menu_consultant",
                entities={"dish_name": extracted_dish} if extracted_dish else {},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 7. Visual Menu design
        if any(k in msg for k in ["design a menu", "menu design", "visual layout", "printable menu", "menu template", "menu poster", "artwork", "flyer", "publication layout"]):
            return IntentClassificationResult(
                intent="menu_design",
                confidence=0.96,
                target_agent="menu_designer",
                entities={},
                requires_database=False,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 8. Menu creation
        if (any(k in msg for k in ["create a new menu", "create new menu", "create a menu", "draft a menu", "make a new menu", "build a menu"]) or (
            "menu" in msg and any(k in msg for k in ["create", "generate", "make", "draft", "build"])
        )) and not any(v in msg for k in ["visual", "layout", "template", "poster", "artwork"] for v in [k]):
            return IntentClassificationResult(
                intent="menu_creation",
                confidence=0.97,
                target_agent="menu_consultant",
                entities={},
                requires_database=False,
                requires_tool_call=False,
                response_mode="detailed_consultation",
            )

        # 9. Menu optimization (what to remove / prune)
        if any(k in msg for k in ["which items should i remove", "what to remove", "remove from my menu", "prune menu", "menu engineering", "optimize menu", "streamline menu"]):
            return IntentClassificationResult(
                intent="menu_optimization",
                confidence=0.95,
                target_agent="menu_consultant",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 10. Customer review analysis
        if any(k in msg for k in ["review", "unhappy", "complaint", "feedback", "sentiment", "customer voice", "praise"]):
            return IntentClassificationResult(
                intent="customer_review_analysis",
                confidence=0.96,
                target_agent="customer_voice",
                entities={"dish_name": extracted_dish} if extracted_dish else {},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 11. Food waste & spoilage
        if any(k in msg for k in ["food waste", "reduce waste", "reduce food waste", "wasting", "wasting ingredients", "waste ingredients", "waste records", "kitchen waste", "ingredient waste"]):
            return IntentClassificationResult(
                intent="food_waste_analysis",
                confidence=0.97,
                target_agent="operations_waste",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        if any(k in msg for k in ["spoilage", "spoilage risk", "slow-moving dishes", "slow moving dishes", "holding risk"]):
            return IntentClassificationResult(
                intent="spoilage_risk",
                confidence=0.95,
                target_agent="operations_waste",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        if any(k in msg for k in ["prep trim", "trim", "repurpose", "leftover"]):
            return IntentClassificationResult(
                intent="inventory_optimization",
                confidence=0.93,
                target_agent="operations_waste",
                entities={},
                requires_database=False,
                requires_tool_call=False,
                response_mode="detailed_consultation",
            )

        # 12. Food cost & ingredient analysis
        if any(k in msg for k in ["reduce the cost of my gravies", "reduce cost of", "food cost", "cost of gravies", "ingredient cost"]):
            return IntentClassificationResult(
                intent="food_cost_analysis",
                confidence=0.94,
                target_agent="menu_consultant",
                entities={"dish_name": extracted_dish} if extracted_dish else {},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 13. Restaurant comparison
        if any(k in msg for k in ["compare my restaurant", "restaurant comparison", "benchmark"]):
            return IntentClassificationResult(
                intent="restaurant_comparison",
                confidence=0.92,
                target_agent="business_intelligence",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 14. Sales analysis
        if any(k in msg for k in ["sales", "revenue", "turnover", "how are sales", "sales trend"]):
            return IntentClassificationResult(
                intent="sales_analysis",
                confidence=0.92,
                target_agent="business_intelligence",
                entities={},
                requires_database=True,
                requires_tool_call=True,
                response_mode="detailed_consultation",
            )

        # 15. General inquiry / Greetings
        if any(k in msg for k in ["hello", "hi", "hey", "help me", "can you help", "who are you", "what can you do"]):
            return IntentClassificationResult(
                intent="general_inquiry",
                confidence=0.96,
                target_agent="orchestrator",
                entities={},
                requires_database=False,
                requires_tool_call=False,
                response_mode="conversational",
            )

        return IntentClassificationResult(
            intent="general_inquiry",
            confidence=0.85,
            target_agent="orchestrator",
            entities={},
            requires_database=False,
            requires_tool_call=False,
            response_mode="conversational",
        )

    def _format_history(self, history: List[Dict[str, Any]], max_turns: int = 4) -> str:
        """Format recent conversation turns into a compact context string."""
        if not history:
            return ""
        recent = history[-max_turns:]
        lines = []
        for m in recent:
            role = m.get("role", "user").capitalize()
            content = m.get("content", "").strip()
            # Truncate content to 150 chars to avoid prompt bloat
            short_content = content[:150] + ("..." if len(content) > 150 else "")
            lines.append(f"{role}: {short_content}")
        return "\n".join(lines)

    def _extract_dish_from_history(self, history: List[Dict[str, Any]]) -> Optional[str]:
        """Scan recent turns to find the most recently discussed dish for pronoun resolution."""
        if not history:
            return None

        dishes = [
            "dum chicken biryani", "butter chicken deluxe", "paneer butter masala",
            "butter garlic naan", "paneer tikka angara", "truffle tagliatelle",
            "butter chicken", "chicken biryani", "paneer tikka", "dal makhani",
            "biryani", "naan", "chaas", "tandoori chicken",
        ]
        # Sort by length descending to match longest specific dish first
        dishes.sort(key=len, reverse=True)

        # Scan backwards from newest to oldest
        for m in reversed(history[-6:]):
            txt = m.get("content", "").lower()
            for d in dishes:
                if d in txt:
                    return d
        return None
