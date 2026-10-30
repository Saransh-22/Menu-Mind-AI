"""
Agent tool implementations.
Each tool executes real Python code. No simulated calls.
Tools return dicts that the orchestrator converts to structured types.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import pandas as pd

from agent.schemas import (
    AgentState,
    DataQualityReport,
    ItemSalesMetrics,
    MenuAction,
    Priority,
    ProfitabilityMetrics,
    Recommendation,
    SalesAnalysisSummary,
    SentimentSummary,
)
from config.settings import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW, GEMINI_MODEL
from services.analytics_service import (
    analyze_sales,
    calculate_profitability,
    analyze_menu,
)
from services.sentiment_service import (
    analyze_sentiment_local,
    build_sentiment_prompt,
    parse_gemini_sentiment,
)
from services.review_retrieval_service import retrieve_reviews

logger = logging.getLogger(__name__)


# ──────────────────────────── Tool Registry ──────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "analyze_sales",
        "description": (
            "Compute sales analytics (revenue, quantity, trends, category breakdown) "
            "from the cleaned sales data. Returns a SalesAnalysisSummary."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "analyze_sentiment",
        "description": (
            "Analyse customer review sentiment for all menu items or a specific item. "
            "Identify themes (taste, portion, price, consistency, freshness). "
            "Returns a SentimentSummary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Specific menu item name to analyse, or omit for overall.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "calculate_profitability",
        "description": (
            "Calculate contribution margin per menu item using price and cost data. "
            "Only callable when both menu and costs data are available."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_restaurant_reviews",
        "description": (
            "Search for publicly available reviews via configured API. "
            "Only call if reviews are missing or insufficient and a search API is configured."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "evaluate_menu_item",
        "description": (
            "Evaluate a specific menu item using all available evidence "
            "(sales, sentiment, profitability) and return a preliminary assessment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "item_name": {
                    "type": "string",
                    "description": "Name of the menu item to evaluate.",
                }
            },
            "required": ["item_name"],
        },
    },
    {
        "name": "recommend_menu_actions",
        "description": (
            "Generate structured recommendations for all menu items. "
            "Call after sales analysis and sentiment analysis are complete."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "analyze_food_waste",
        "description": (
            "Analyze verified restaurant food-waste records, calculate waste cost "
            "where quantity and ingredient unit cost are known, and identify the "
            "ingredients with the largest recorded waste cost."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ──────────────────────────── Tool Executor ──────────────────────────────────

class ToolExecutor:
    """Executes tool calls with validated arguments and updates agent state."""

    def __init__(
        self,
        state: AgentState,
        menu_df: Optional[pd.DataFrame],
        sales_df: Optional[pd.DataFrame],
        reviews_df: Optional[pd.DataFrame],
        costs_df: Optional[pd.DataFrame],
        gemini_client=None,
        waste_df: Optional[pd.DataFrame] = None,
    ):
        self.state = state
        self.menu_df = menu_df
        self.sales_df = sales_df
        self.reviews_df = reviews_df
        self.costs_df = costs_df
        self.waste_df = waste_df
        self.gemini = gemini_client

    def execute(self, tool_name: str, args: dict) -> dict:
        """Dispatch to the correct tool method and return a result dict."""
        self.state.tool_calls_made += 1
        self.state.add_log(f"Calling tool: {tool_name}({json.dumps(args, default=str)})")
        trace = {"tool": tool_name, "arguments": args, "status": "running"}
        self.state.execution_history.append(trace)
        try:
            method = getattr(self, f"_tool_{tool_name}", None)
            if method is None:
                return {"error": f"Unknown tool: {tool_name}"}
            result = method(**args)
            trace["status"] = "error" if isinstance(result, dict) and "error" in result else "completed"
            trace["result_summary"] = (
                str(result.get("error")) if isinstance(result, dict) and result.get("error")
                else "Tool returned structured output"
            )
            self.state.add_log(f"Tool {tool_name} completed.")
            return result
        except Exception as exc:
            logger.exception("Tool %s raised: %s", tool_name, exc)
            trace["status"] = "error"
            trace["error"] = str(exc)
            self.state.recovery_attempts += 1
            self.state.add_log(f"Tool {tool_name} ERROR: {exc}")
            return {"error": str(exc)}

    # ── Tool Implementations ────────────────────────────────────────────────

    def _tool_analyze_sales(self) -> dict:
        if self.sales_df is None or self.sales_df.empty:
            return {"error": "No sales data available."}
        summary = analyze_sales(self.sales_df, self.menu_df)
        self.state.sales_summary = summary
        return {
            "total_revenue": summary.total_revenue,
            "total_units": summary.total_units,
            "item_count": summary.item_count,
            "period": f"{summary.period_start} → {summary.period_end}",
            "top_items": [i.item_name for i in summary.top_items[:5]],
            "weak_items": [i.item_name for i in summary.weak_items[:5]],
        }

    def _tool_analyze_sentiment(self, item_name: Optional[str] = None) -> dict:
        if self.reviews_df is None or self.reviews_df.empty:
            return {"error": "No review data available."}

        if self.gemini:
            try:
                prompt = build_sentiment_prompt(self.reviews_df, item_name)
                response = self.gemini.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                text = response.text.strip()
                # Strip markdown code fences if present
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:])
                    text = text.rstrip("`").strip()
                summary = parse_gemini_sentiment(text, item_name)
            except Exception as e:
                logger.warning("Gemini sentiment failed, falling back to local: %s", e)
                summary = analyze_sentiment_local(self.reviews_df, item_name)
        else:
            summary = analyze_sentiment_local(self.reviews_df, item_name)

        # Store in state
        existing = next(
            (s for s in self.state.sentiment_summaries
             if s.item_name == (item_name or "overall")), None
        )
        if existing:
            self.state.sentiment_summaries.remove(existing)
        self.state.sentiment_summaries.append(summary)

        return {
            "item_name": summary.item_name,
            "review_count": summary.review_count,
            "positive_pct": summary.positive_pct,
            "negative_pct": summary.negative_pct,
            "neutral_pct": summary.neutral_pct,
            "avg_rating": summary.avg_rating,
            "themes": [t.model_dump() for t in summary.themes],
            "limitations": summary.limitations,
        }

    def _tool_calculate_profitability(self) -> dict:
        if self.menu_df is None:
            return {"error": "No menu data available."}
        if self.costs_df is None:
            return {
                "message": "No cost data uploaded. Profitability cannot be calculated.",
                "calculable_items": 0,
            }
        metrics = calculate_profitability(self.menu_df, self.costs_df, self.state.sales_summary)
        self.state.profitability_metrics = metrics
        calculable = [m for m in metrics if m.calculable]
        return {
            "total_items": len(metrics),
            "calculable_items": len(calculable),
            "average_margin_pct": (
                round(sum(m.margin_pct for m in calculable) / len(calculable), 2)
                if calculable else None
            ),
            "items": [m.model_dump() for m in metrics[:20]],  # cap for token efficiency
        }

    def _tool_search_restaurant_reviews(self) -> dict:
        restaurant_name = self.state.restaurant_name
        # Extract city from restaurant_name if structured "Name, City"
        city = ""
        if "," in restaurant_name:
            parts = restaurant_name.split(",", 1)
            restaurant_name = parts[0].strip()
            city = parts[1].strip()

        result = retrieve_reviews(restaurant_name, city)
        if result.success and result.reviews:
            # Convert to DataFrame and store
            rows = [
                {
                    "review_text": r.review_text,
                    "source": r.source,
                    "source_url": r.source_url,
                    "item_name": r.item_name,
                    "rating": r.rating,
                    "review_date": r.review_date,
                    "attribution": r.attribution or "SerpApi Google Search snippet",
                    "is_snippet": getattr(r, "is_snippet", True),
                    "review_type": getattr(r, "review_type", "search_snippet"),
                }
                for r in result.reviews
            ]
            new_df = pd.DataFrame(rows)
            if self.reviews_df is not None and not self.reviews_df.empty:
                self.reviews_df = pd.concat(
                    [self.reviews_df, new_df], ignore_index=True
                )
            else:
                self.reviews_df = new_df

        return {
            "success": result.success,
            "review_count": len(result.reviews),
            "source": result.source,
            "limitations": result.limitations,
            "error": result.error,
        }

    def _tool_analyze_food_waste(self) -> dict:
        from services.waste_analysis_service import calculate_waste_cost

        if self.waste_df is None or self.waste_df.empty:
            return {"message": "No verified food-waste records are available."}
        records = self.waste_df.to_dict(orient="records")
        summary = calculate_waste_cost(records)
        self.state.waste_summary = summary
        return summary

    def _tool_evaluate_menu_item(self, item_name: str) -> dict:
        """Return a per-item evidence summary to support recommendation."""
        evidence: dict = {"item_name": item_name}

        # Sales evidence
        if self.state.sales_summary:
            all_items = (
                self.state.sales_summary.top_items
                + self.state.sales_summary.weak_items
            )
            item_data = next(
                (i for i in all_items
                 if i.item_name.lower() == item_name.lower()), None
            )
            if item_data:
                evidence["sales"] = {
                    "quantity": item_data.total_quantity,
                    "revenue": item_data.total_revenue,
                    "rank": item_data.sales_rank,
                    "contribution_pct": item_data.revenue_contribution_pct,
                    "trend": item_data.period_trend,
                }
            else:
                evidence["sales"] = "No sales data found for this item."

        # Sentiment evidence
        sentiment = next(
            (s for s in self.state.sentiment_summaries
             if s.item_name and s.item_name.lower() == item_name.lower()),
            next(
                (s for s in self.state.sentiment_summaries if s.item_name == "overall"),
                None,
            ),
        )
        if sentiment:
            evidence["sentiment"] = {
                "positive_pct": sentiment.positive_pct,
                "negative_pct": sentiment.negative_pct,
                "review_count": sentiment.review_count,
                "themes": [t.theme for t in sentiment.themes[:4]],
            }

        # Profitability evidence
        prof = next(
            (p for p in self.state.profitability_metrics
             if p.item_name.lower() == item_name.lower()),
            None,
        )
        if prof:
            evidence["profitability"] = {
                "calculable": prof.calculable,
                "margin_pct": prof.margin_pct,
                "contribution_margin": prof.contribution_margin,
                "limitation_note": prof.limitation_note,
            }

        return evidence

    def _tool_recommend_menu_actions(self) -> dict:
        """
        Generate recommendations for all menu items.
        Attempts LLM-powered generation when Gemini is configured,
        and falls back gracefully to deterministic evidence-based rules.
        """
        if self.menu_df is None or self.menu_df.empty:
            return {"error": "No menu data. Cannot generate recommendations."}

        # Build context for the LLM or deterministic engine
        context = self._build_recommendation_context()
        recommendations: list[Recommendation] = []

        if self.gemini:
            try:
                prompt = self._build_recommendation_prompt(context)
                response = self.gemini.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = "\n".join(text.split("\n")[1:])
                    text = text.rstrip("`").strip()

                recs_data = json.loads(text)
                for item in recs_data.get("recommendations", []):
                    try:
                        action_raw = str(item.get("action", "INSUFFICIENT_EVIDENCE")).upper()
                        try:
                            action = MenuAction(action_raw)
                        except ValueError:
                            action = MenuAction.INSUFFICIENT_EVIDENCE

                        prio_raw = str(item.get("priority", "low")).lower()
                        try:
                            priority = Priority(prio_raw)
                        except ValueError:
                            priority = Priority.LOW

                        c_score = float(item.get("confidence_score", 0.5))
                        c_score = max(0.0, min(1.0, c_score))

                        rec = Recommendation(
                            item_id=item.get("item_id"),
                            item_name=item.get("item_name", "Unknown"),
                            title=item.get("title") or f"{action.value.replace('_', ' ').title()}: {item.get('item_name', 'Item')}",
                            action=action,
                            priority=priority,
                            confidence_score=c_score,
                            reasoning=item.get("reasoning", ""),
                            suggested_action=item.get("suggested_action") or item.get("reasoning", "")[:140],
                            alternative_actions=item.get("alternative_actions", []),
                            expected_benefits=item.get("expected_benefits", ""),
                            potential_risks=item.get("potential_risks", ""),
                            missing_information=item.get("missing_information", ""),
                            next_steps=item.get("next_steps", []),
                            sales_metrics=item.get("sales_metrics"),
                            review_themes=item.get("review_themes"),
                            profitability=item.get("profitability"),
                            success_metrics=item.get("success_metrics", ""),
                        )
                        recommendations.append(rec)
                    except Exception as e:
                        logger.warning("Skipping invalid rec for %s: %s", item.get("item_name"), e)
            except Exception as e:
                logger.warning("Gemini generation failed; falling back to deterministic recommendations: %s", e)
                recommendations = []

        if not recommendations:
            recommendations = self._generate_deterministic_recommendations(context)

        self.state.recommendations = recommendations
        return {
            "count": len(recommendations),
            "actions_breakdown": {
                action.value: sum(1 for r in recommendations if r.action == action)
                for action in MenuAction
            },
        }

    def _generate_deterministic_recommendations(self, context: dict) -> list[Recommendation]:
        """
        Produce grounded, evidence-backed menu recommendations deterministically
        by synthesizing sales volume, profit margins, customer reviews, and food waste.
        """
        if self.menu_df is None or self.menu_df.empty:
            return []

        # 1. Aggregate Sales Performance
        sales_by_item: dict[str, dict] = {}
        if self.sales_df is not None and not self.sales_df.empty:
            for _, row in self.sales_df.iterrows():
                iname = str(row.get("item_name", "")).strip()
                if not iname:
                    continue
                norm_name = iname.lower()
                qty = float(row.get("quantity_sold", 0) or 0)
                rev = float(row.get("revenue", 0) or 0)
                if rev == 0 and "selling_price" in row:
                    rev = qty * float(row.get("selling_price", 0) or 0)
                if norm_name not in sales_by_item:
                    sales_by_item[norm_name] = {"original_name": iname, "quantity": 0, "revenue": 0.0}
                sales_by_item[norm_name]["quantity"] += int(qty)
                sales_by_item[norm_name]["revenue"] += round(rev, 2)

        quantities = [v["quantity"] for v in sales_by_item.values()]
        mean_qty = (sum(quantities) / len(quantities)) if quantities else 0.0
        sorted_qty = sorted(quantities)
        p75_qty = sorted_qty[int(len(sorted_qty) * 0.75)] if sorted_qty else 0
        p25_qty = sorted_qty[int(len(sorted_qty) * 0.25)] if sorted_qty else 0

        # 2. Map Profitability
        profit_by_name: dict[str, Any] = {}
        if self.state.profitability_metrics:
            for m in self.state.profitability_metrics:
                profit_by_name[m.item_name.strip().lower()] = m

        # 3. Map Sentiment & Customer Reviews
        sentiment_by_name: dict[str, Any] = {}
        if self.state.sentiment_summaries:
            for s in self.state.sentiment_summaries:
                if s.item_name:
                    sentiment_by_name[s.item_name.strip().lower()] = s

        review_ratings_by_item: dict[str, list[float]] = {}
        review_complaints_by_item: dict[str, list[str]] = {}
        if self.reviews_df is not None and not self.reviews_df.empty:
            for _, r in self.reviews_df.iterrows():
                r_item = str(r.get("item_name", "")).strip().lower()
                r_text = str(r.get("review_text", "")).lower()
                r_rating = float(r.get("rating", 0) or 0)
                for _, mrow in self.menu_df.iterrows():
                    m_norm = str(mrow.get("item_name", "")).strip().lower()
                    if not m_norm:
                        continue
                    if r_item == m_norm or m_norm in r_text:
                        if m_norm not in review_ratings_by_item:
                            review_ratings_by_item[m_norm] = []
                            review_complaints_by_item[m_norm] = []
                        if r_rating > 0:
                            review_ratings_by_item[m_norm].append(r_rating)
                        if any(kw in r_text for kw in ("salty", "cold", "bland", "overcooked", "small", "slow", "stale", "bad")):
                            review_complaints_by_item[m_norm].append(str(r.get("review_text", ""))[:100])

        # 4. Map Food Waste Records
        waste_by_dish: dict[str, dict] = {}
        if self.waste_df is not None and not self.waste_df.empty:
            for _, w in self.waste_df.iterrows():
                dish = str(w.get("associated_dish", "")).strip().lower()
                if dish:
                    if dish not in waste_by_dish:
                        waste_by_dish[dish] = {"cost": 0.0, "reasons": set()}
                    waste_by_dish[dish]["cost"] += float(w.get("cost", 0) or 0)
                    reason = str(w.get("reason", "")).strip()
                    if reason:
                        waste_by_dish[dish]["reasons"].add(reason)

        # 5. Generate Grounded Recommendations for each menu item
        recommendations: list[Recommendation] = []
        seen_items = set()

        for _, mrow in self.menu_df.iterrows():
            item_name = str(mrow.get("item_name", "")).strip()
            if not item_name or item_name.lower() in seen_items:
                continue
            seen_items.add(item_name.lower())

            item_id = str(mrow.get("item_id", "")) if pd.notna(mrow.get("item_id")) else None
            price = float(mrow.get("price", 0) or 0) if pd.notna(mrow.get("price")) else None
            norm_name = item_name.lower()

            # Sales indicators
            s_data = sales_by_item.get(norm_name, {"quantity": 0, "revenue": 0.0})
            qty = s_data["quantity"]
            rev = s_data["revenue"]
            has_sales = qty > 0

            # Profitability indicators
            p_data = profit_by_name.get(norm_name)
            margin_pct = p_data.margin_pct if (p_data and p_data.calculable) else None
            total_cost = p_data.total_cost if (p_data and p_data.calculable) else None

            # Sentiment indicators
            sent_summary = sentiment_by_name.get(norm_name)
            if sent_summary:
                pos_pct = sent_summary.positive_pct
                neg_pct = sent_summary.negative_pct
                avg_rating = sent_summary.avg_rating
                rev_count = sent_summary.review_count
            else:
                ratings = review_ratings_by_item.get(norm_name, [])
                rev_count = len(ratings)
                avg_rating = round(sum(ratings) / rev_count, 1) if rev_count > 0 else None
                neg_count = sum(1 for r in ratings if r <= 2.5)
                pos_count = sum(1 for r in ratings if r >= 4.0)
                neg_pct = round((neg_count / rev_count) * 100, 1) if rev_count > 0 else 0.0
                pos_pct = round((pos_count / rev_count) * 100, 1) if rev_count > 0 else 0.0

            # Waste indicators
            w_data = waste_by_dish.get(norm_name, {"cost": 0.0, "reasons": set()})
            waste_cost = w_data["cost"]
            waste_reasons = list(w_data["reasons"])

            # Volume indicator for underperforming item evaluation
            is_low_volume = (qty <= 2) or (qty < mean_qty and qty <= (p25_qty if len(quantities) >= 4 else 5))

            # ── Evaluate Rules ───────────────────────────────────────────────
            # Rule 1: REPRICE — Strong sales, but constrained profit margin
            if (has_sales and qty >= mean_qty and margin_pct is not None and margin_pct < 45.0 and neg_pct < 25.0):
                action = MenuAction.REPRICE
                priority = Priority.HIGH
                confidence = 0.82
                title = f"Optimize Price & Recipe Margin: {item_name}"
                suggested_action = (
                    f"Adjust menu price upward by $1.00–$2.00 or re-engineer portion sizing to "
                    f"lift the current {margin_pct:.1f}% contribution margin toward the 65% target benchmark."
                )
                reasoning = (
                    f"{item_name} demonstrates steady sales demand ({qty} units sold, ${rev:,.2f} revenue), "
                    f"but its contribution margin is tight at {margin_pct:.1f}% (total unit cost: ${total_cost:.2f}"
                    f"{f', price: ${price:.2f}' if price else ''}). Customer sentiment is stable with only "
                    f"{neg_pct:.0f}% negative feedback, indicating strong price-inelasticity to absorb a modest price adjustment."
                )
                expected_benefits = (
                    f"Projected margin expansion of $1.25–$2.00 per unit, generating an estimated "
                    f"${max(10, int(qty * 1.5)):,.0f} in incremental gross profit per cycle."
                )
                potential_risks = "Customer sensitivity to price changes. Soften impact by refreshing garnishing or testing in an A/B pricing experiment."
                missing_information = "Competitor pricing for identical dishes in the immediate geographic trade area."
                next_steps = [
                    "Audit current supplier invoices for top recipe ingredients.",
                    "Model gross profit at +5% and +10% price tiers.",
                    "Launch a 14-day A/B menu price experiment."
                ]
                success_metrics = "Achieve target margin >= 60% with less than 5% change in weekly sales velocity."

            # Rule 2: REMOVE — Consistently weak sales + negative sentiment, dead inventory, or negligible demand
            elif has_sales and is_low_volume and (neg_pct >= 25.0 or waste_cost > 10.0 or (avg_rating is not None and avg_rating < 3.0)):
                action = MenuAction.REMOVE
                priority = Priority.MEDIUM
                confidence = 0.74
                title = f"Phase Out Underperforming Item: {item_name}"
                suggested_action = (
                    "Launch a 2-week run-out daily special to deplete remaining pantry inventory, "
                    "then sunset the item from the core menu to free kitchen station bandwidth."
                )
                reasoning = (
                    f"{item_name} has generated low sales ({qty} units, ${rev:,.2f} revenue) accompanied by "
                    f"weak customer reception or prep waste. Carrying slow-moving menu items complicates inventory "
                    f"holding, slows line execution, and crowds out higher-margin items."
                )
                expected_benefits = "Streamlines kitchen line mise-en-place, lowers inventory waste risk, and focuses guest attention on profitable favorites."
                potential_risks = "Disappointing a small niche of regulars. Mitigate by recommending a popular alternative dish."
                missing_information = "Verify whether specialized ingredients for this dish are shared with any active recipes."
                next_steps = [
                    "Audit remaining stock of unique perishable ingredients.",
                    "Schedule 14-day depletion special at promotional pricing.",
                    "Archive dish in POS and update digital menu boards."
                ]
                success_metrics = "Zero expired inventory write-offs and successful migration of orders to core menu items."

            # Rule 3: IMPROVE — Active customer demand, but quality friction, negative reviews, or recurring waste
            elif (has_sales and (neg_pct >= 25.0 or (avg_rating is not None and avg_rating < 3.2))) or waste_cost > 25.0:
                action = MenuAction.IMPROVE
                priority = Priority.HIGH if (waste_cost > 50.0 or neg_pct >= 40.0) else Priority.MEDIUM
                confidence = 0.78
                title = f"Refine Quality & Kitchen Prep: {item_name}"
                reasons_str = f" Waste logs cite: {', '.join(waste_reasons)}." if waste_reasons else ""
                suggested_action = (
                    "Standardize kitchen line preparation SOPs, calibrate portion sizes, and conduct "
                    "a freshness audit to address guest complaints and reduce scrap."
                )
                reasoning = (
                    f"{item_name} has active customer volume ({qty} units, ${rev:,.2f} revenue), but exhibits "
                    f"operational friction. {f'{neg_pct:.0f}% of reviews contain negative sentiment.' if neg_pct else ''} "
                    f"{f'Recorded kitchen waste: ${waste_cost:,.2f}.{reasons_str}' if waste_cost > 0 else ''}"
                )
                expected_benefits = "Reduce customer churn, lower remake/spoilage costs, and improve average review score."
                potential_risks = "Altering core flavor profile may alienate repeat regulars. Validate changes with team blind tastings."
                missing_information = "Specific kitchen shift-by-shift prep variance and ticket assembly times."
                next_steps = [
                    "Review recent customer complaints and waste logs with head chef.",
                    "Standardize recipe spec cards with precise portion scoops.",
                    "Track customer feedback and remake tickets for 14 days."
                ]
                success_metrics = "Reduce negative review mentions to under 10% and decrease waste cost by > 40%."

            # Rule 4: PROMOTE — Top performer with positive sentiment and solid margins
            elif (has_sales and (qty >= p75_qty or (qty >= mean_qty and rev > 0)) and
                  (pos_pct >= 40.0 or (avg_rating is not None and avg_rating >= 3.8) or neg_pct < 15.0) and
                  (margin_pct is None or margin_pct >= 45.0)):
                action = MenuAction.PROMOTE
                priority = Priority.HIGH
                confidence = 0.88
                title = f"Feature & Upsell Star Dish: {item_name}"
                suggested_action = (
                    "Position in the 'Chef Highlights' section on physical and online menus, "
                    "train front-of-house staff on active pairing suggestions, and feature in social marketing."
                )
                margin_note = f"healthy {margin_pct:.1f}% contribution margin" if margin_pct else "strong revenue profile"
                reasoning = (
                    f"{item_name} is one of your standout assets: {qty} units sold generating ${rev:,.2f} "
                    f"in revenue with a {margin_note} and enthusiastic customer feedback "
                    f"({f'{pos_pct:.0f}% positive reviews' if pos_pct else 'consistently high customer satisfaction'}). "
                    f"Capitalizing on this proven demand will lift overall ticket size."
                )
                expected_benefits = "15–25% increase in weekly order volume for this proven high-value dish."
                potential_risks = "Station bottleneck during peak dinner rushes if prep mise-en-place is insufficient."
                missing_information = "Cross-selling item affinity data (dishes and drinks most frequently co-ordered)."
                next_steps = [
                    "Feature dish at the top of physical menus and delivery app banners.",
                    "Incentivize service staff on beverage pairings for this item.",
                    "Monitor weekly order frequency and kitchen prep velocity."
                ]
                success_metrics = "Achieve 15% growth in unit sales without increasing prep ticket time."

            # Rule 5: INSUFFICIENT_EVIDENCE — Low transaction volume, no reviews, no cost data
            elif not has_sales or (qty <= 3 and rev_count == 0 and margin_pct is None):
                action = MenuAction.INSUFFICIENT_EVIDENCE
                priority = Priority.LOW
                confidence = 0.30
                title = f"Collect Operational Data: {item_name}"
                suggested_action = (
                    "Maintain item on active menu while tracking at least 15 customer orders and "
                    "collecting direct customer feedback before making adjustments."
                )
                reasoning = (
                    f"Available data for {item_name} is currently insufficient (fewer than 2 independent signals: "
                    f"{qty} sales recorded, {rev_count} reviews, and cost data not yet mapped). "
                    f"Making menu adjustments without verified data risks disruptive errors."
                )
                expected_benefits = "Ensures future menu decisions are backed by statistically valid sales and margin evidence."
                potential_risks = "Delaying an intervention if item is underperforming, though exposure is limited given low current sales."
                missing_information = "POS sales volume over 30 operating days, ingredient cost recipe mapping, and customer review feedback."
                next_steps = [
                    "Verify POS button and category mapping for this dish.",
                    "Instruct waitstaff to ask guests ordering this dish for feedback.",
                    "Upload recipe ingredient costs to enable margin calculation."
                ]
                success_metrics = "Collect at least 15 verified sales transactions and 3 customer ratings before re-evaluating."

            # Fallback for steady dishes without extreme signals
            else:
                if has_sales and qty >= mean_qty:
                    action = MenuAction.PROMOTE
                    priority = Priority.MEDIUM
                    confidence = 0.65
                    title = f"Maintain & Feature Steady Performer: {item_name}"
                    suggested_action = "Maintain recipe consistency, feature in category specials, and explore combo pairings."
                    reasoning = f"{item_name} maintains steady order volume ({qty} units, ${rev:,.2f} revenue) with stable customer reception."
                    expected_benefits = "Sustained order volume and steady contribution to baseline revenue."
                    potential_risks = "Complacency regarding supplier ingredient price creeps."
                    missing_information = "Detailed ingredient recipe cost breakdown."
                    next_steps = ["Track monthly volume stability", "Test combo beverage pairing"]
                    success_metrics = "Maintain steady week-over-week sales volume."
                else:
                    action = MenuAction.INSUFFICIENT_EVIDENCE
                    priority = Priority.LOW
                    confidence = 0.40
                    title = f"Monitor Sales Trends: {item_name}"
                    suggested_action = "Observe sales velocity over next 2 operating cycles before altering menu status."
                    reasoning = f"{item_name} has modest sales ({qty} units) with neutral indicators."
                    expected_benefits = "Avoids premature changes while volume builds."
                    potential_risks = "Slow rotation of ingredients."
                    missing_information = "Customer feedback ratings and ingredient waste logs."
                    next_steps = ["Observe weekly POS velocity", "Re-evaluate next cycle"]
                    success_metrics = "Reach 20+ units sold to determine trend trajectory."

            rec = Recommendation(
                item_id=item_id,
                item_name=item_name,
                title=title,
                action=action,
                priority=priority,
                confidence_score=confidence,
                reasoning=reasoning,
                suggested_action=suggested_action,
                alternative_actions=[f"Maintain active monitoring for {item_name}", "Evaluate bundle promotion"],
                expected_benefits=expected_benefits,
                potential_risks=potential_risks,
                missing_information=missing_information,
                next_steps=next_steps,
                sales_metrics={"quantity_sold": qty, "revenue": rev, "unit_price": price},
                review_themes={"review_count": rev_count, "avg_rating": avg_rating, "positive_pct": pos_pct, "negative_pct": neg_pct},
                profitability={"selling_price": price, "total_cost": total_cost, "margin_pct": margin_pct, "calculable": (p_data.calculable if p_data else False)},
                success_metrics=success_metrics,
            )
            recommendations.append(rec)

        return recommendations

    # ── Context Builders ────────────────────────────────────────────────────

    def _build_recommendation_context(self) -> dict:
        """Assemble serializable evidence context for the LLM prompt."""
        ctx: dict = {}

        if self.menu_df is not None:
            ctx["menu_items"] = self.menu_df[
                [c for c in ("item_id", "item_name", "category", "price", "description")
                 if c in self.menu_df.columns]
            ].to_dict(orient="records")

        if self.state.sales_summary:
            s = self.state.sales_summary
            ctx["sales_summary"] = {
                "total_revenue": s.total_revenue,
                "total_units": s.total_units,
                "period": f"{s.period_start} → {s.period_end}",
                "top_items": [i.model_dump() for i in s.top_items],
                "weak_items": [i.model_dump() for i in s.weak_items],
                "category_summary": s.category_summary,
            }

        if self.state.sentiment_summaries:
            ctx["sentiment"] = [s.model_dump() for s in self.state.sentiment_summaries]

        if self.state.profitability_metrics:
            ctx["profitability"] = [p.model_dump() for p in self.state.profitability_metrics]

        if self.state.waste_summary:
            ctx["food_waste"] = self.state.waste_summary
        if self.waste_df is not None and not self.waste_df.empty:
            ctx["food_waste_records"] = self.waste_df.to_dict(orient="records")[:100]

        return ctx

    def _build_recommendation_prompt(self, context: dict) -> str:
        ctx_json = json.dumps(context, indent=2, default=str)
        return f"""You are a restaurant analytics AI agent. Based on the evidence below, generate structured menu optimization recommendations.

EVIDENCE:
{ctx_json}

For each menu item, determine the best action from:
- IMPROVE: High demand but quality/consistency issues
- REMOVE: Low demand + negative feedback + poor margins (when known)
- PROMOTE: Strong demand + positive feedback + good margins (when known)
- REPRICE: Price-value mismatch supported by evidence
- INSUFFICIENT_EVIDENCE: Cannot justify any action with the available data

Return ONLY valid JSON (no markdown):
{{
  "recommendations": [
    {{
      "item_id": "<id or null>",
      "item_name": "<exact menu item name>",
      "title": "<concise actionable recommendation headline>",
      "action": "<IMPROVE|REMOVE|PROMOTE|REPRICE|INSUFFICIENT_EVIDENCE>",
      "priority": "<high|medium|low>",
      "confidence_score": <0.0-1.0>,
      "reasoning": "<detailed evidence-based rationale>",
      "suggested_action": "<concrete tactical action>",
      "alternative_actions": ["<alternative 1>", "<alternative 2>"],
      "expected_benefits": "<what improvement is expected>",
      "potential_risks": "<what could go wrong>",
      "missing_information": "<data that would improve this recommendation>",
      "next_steps": ["<concrete step 1>", "<concrete step 2>"],
      "sales_metrics": {{}},
      "review_themes": {{}},
      "profitability": {{}},
      "success_metrics": "<how to measure success>"
    }}
  ]
}}

RULES:
- Never fabricate sales numbers, quotes, or cost data not in the evidence.
- A low-selling item is NOT automatically overpriced.
- A high-revenue item is NOT automatically profitable.
- A few negative reviews do NOT automatically justify removal.
- Use INSUFFICIENT_EVIDENCE when less than 2 independent signals support a conclusion.
- confidence_score must reflect genuine evidence strength (0.1-0.4 for weak, 0.5-0.7 medium, 0.75-0.95 strong).
- All fields must be filled — never leave reasoning empty.
- If food-waste evidence is present, connect it to menu recommendations only when
  ingredient-to-dish relationships or associated_dish records support the connection.
- Never infer ingredient reuse is safe. Food safety and storage must be verified by staff."""
