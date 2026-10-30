"""
Pydantic schemas for validated agent input/output.
All agent tools consume and produce these types.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ──────────────────────────── Enums ──────────────────────────────────────────

class MenuAction(str, Enum):
    IMPROVE = "IMPROVE"
    REMOVE = "REMOVE"
    PROMOTE = "PROMOTE"
    REPRICE = "REPRICE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExperimentStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ──────────────────────────── Data Quality ───────────────────────────────────

class DataQualityReport(BaseModel):
    file_type: str
    total_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    missing_values: dict[str, int] = Field(default_factory=dict)
    invalid_records: int = 0
    unmatched_items: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0, default=1.0)

    def summary(self) -> str:
        return (
            f"{self.file_type}: {self.accepted_records}/{self.total_records} accepted, "
            f"{self.duplicate_records} duplicates, "
            f"{len(self.unmatched_items)} unmatched items, "
            f"score={self.quality_score:.0%}"
        )


# ──────────────────────────── Sales Metrics ──────────────────────────────────

class ItemSalesMetrics(BaseModel):
    item_id: Optional[str] = None
    item_name: str
    category: Optional[str] = None
    total_quantity: int = 0
    total_revenue: float = 0.0
    avg_price: Optional[float] = None
    sales_rank: Optional[int] = None
    revenue_contribution_pct: Optional[float] = None
    period_trend: Optional[str] = None   # "growing" | "declining" | "stable"
    data_points: int = 0


class SalesAnalysisSummary(BaseModel):
    total_revenue: float
    total_units: int
    item_count: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    top_items: list[ItemSalesMetrics] = Field(default_factory=list)
    weak_items: list[ItemSalesMetrics] = Field(default_factory=list)
    category_summary: dict[str, dict] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# ──────────────────────────── Profitability ──────────────────────────────────

class ProfitabilityMetrics(BaseModel):
    item_id: Optional[str] = None
    item_name: str
    selling_price: Optional[float] = None
    ingredient_cost: Optional[float] = None
    packaging_cost: Optional[float] = None
    total_cost: Optional[float] = None
    contribution_margin: Optional[float] = None
    margin_pct: Optional[float] = None
    calculable: bool = False
    limitation_note: Optional[str] = None


# ──────────────────────────── Review/Sentiment ───────────────────────────────

class ReviewTheme(BaseModel):
    theme: str
    sentiment: str   # "positive" | "negative" | "neutral"
    frequency: int = 1
    representative_quote: Optional[str] = None   # only real review text


class SentimentSummary(BaseModel):
    item_name: Optional[str] = None
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    review_count: int = 0
    avg_rating: Optional[float] = None
    verified_count: int = 0
    snippet_count: int = 0
    verified_avg_rating: Optional[float] = None
    snippet_avg_rating: Optional[float] = None
    rating_distribution: dict[str, int] = Field(default_factory=dict)
    complaints: list[dict] = Field(default_factory=list)
    appreciated_features: list[dict] = Field(default_factory=list)
    themes: list[ReviewTheme] = Field(default_factory=list)
    source_coverage: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# ──────────────────────────── Recommendation ─────────────────────────────────

class Recommendation(BaseModel):
    item_id: Optional[str] = None
    item_name: str
    title: Optional[str] = None
    action: MenuAction
    priority: Priority
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    suggested_action: Optional[str] = None
    alternative_actions: list[str] = Field(default_factory=list)
    expected_benefits: str = ""
    potential_risks: str = ""
    missing_information: str = ""
    next_steps: list[str] = Field(default_factory=list)
    sales_metrics: Optional[dict] = None
    review_themes: Optional[dict] = None
    profitability: Optional[dict] = None
    requires_approval: bool = True
    success_metrics: str = ""

    @field_validator("confidence_score")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)

    def confidence_label(self) -> str:
        if self.confidence_score >= 0.75:
            return "High"
        if self.confidence_score >= 0.50:
            return "Medium"
        return "Low"


# ──────────────────────────── Experiment ─────────────────────────────────────

class ExperimentPlan(BaseModel):
    title: str
    hypothesis: str
    baseline_period: str
    intervention: str
    test_duration_days: int
    success_criteria: str
    guardrail_metrics: str
    requires_approval: bool = True
    evaluation_method: str
    recommendation_id: Optional[int] = None


# ──────────────────────────── Agent State ────────────────────────────────────

class AgentState(BaseModel):
    run_id: int
    restaurant_name: str
    available_data: list[str] = Field(default_factory=list)   # "menu","sales","reviews","costs"
    quality_reports: list[DataQualityReport] = Field(default_factory=list)
    sales_summary: Optional[SalesAnalysisSummary] = None
    sentiment_summaries: list[SentimentSummary] = Field(default_factory=list)
    profitability_metrics: list[ProfitabilityMetrics] = Field(default_factory=list)
    waste_summary: Optional[dict] = None
    execution_history: list[dict] = Field(default_factory=list)
    recovery_attempts: int = 0
    recommendations: list[Recommendation] = Field(default_factory=list)
    tool_calls_made: int = 0
    max_tool_calls: int = 20
    finished: bool = False
    error: Optional[str] = None
    log: list[str] = Field(default_factory=list)

    def add_log(self, msg: str) -> None:
        self.log.append(msg)

    def can_call_tool(self) -> bool:
        return self.tool_calls_made < self.max_tool_calls and not self.finished
