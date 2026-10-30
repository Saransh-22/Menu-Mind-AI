"""
Pydantic API request & response schemas for MenuMind AI.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent.schemas import (
    DataQualityReport,
    SalesAnalysisSummary,
    ProfitabilityMetrics,
    SentimentSummary,
    Recommendation,
    ExperimentPlan,
    AgentState,
    MenuAction,
    Priority,
    ExperimentStatus,
)


# ─── Restaurants ─────────────────────────────────────────────────────────────

class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Restaurant name")
    city: str = Field(default="", description="City location")
    location: str = Field(default="", description="Address / Neighborhood")
    website: str = Field(default="", description="Website URL")
    category: str = Field(default="", description="Cuisine / Category")


class RestaurantOut(BaseModel):
    id: int
    name: str
    city: Optional[str] = ""
    location: Optional[str] = ""
    website: Optional[str] = ""
    category: Optional[str] = ""
    created_at: Optional[str] = None
    is_new: Optional[bool] = False


class RestaurantSuggestion(BaseModel):
    name: str
    city: Optional[str] = ""
    source: str = "database"


# ─── Analysis Runs ───────────────────────────────────────────────────────────

class AnalysisRunCreate(BaseModel):
    period_start: str = ""
    period_end: str = ""
    notes: str = ""


class AnalysisRunOut(BaseModel):
    id: int
    restaurant_id: int
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    data_quality_score: Optional[float] = None
    notes: Optional[str] = None
    datasets: Optional[dict[str, bool]] = None


# ─── Ingestion & Previews ────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DatasetPreview(BaseModel):
    file_type: str
    columns: list[str]
    total_rows: int
    rows: list[dict[str, Any]]


class ColumnMappingRequest(BaseModel):
    mapping: dict[str, str]  # target_canonical: uploaded_column


# ─── Analytics ───────────────────────────────────────────────────────────────

class RevenueTrendPoint(BaseModel):
    date: str
    revenue: float
    rolling_7d: Optional[float] = None


class CategoryShare(BaseModel):
    category: str
    revenue: float
    units: int
    percentage: float


class AnalyticsSummaryOut(BaseModel):
    summary: SalesAnalysisSummary
    daily_trends: list[RevenueTrendPoint]
    category_shares: list[CategoryShare]


# ─── Reviews ─────────────────────────────────────────────────────────────────

class ItemReviewInsight(BaseModel):
    item_name: str
    mention_count: int
    verified_count: int
    snippet_count: int
    avg_rating: Optional[float] = None
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    top_complaint: Optional[str] = None
    top_compliment: Optional[str] = None
    sample_reviews: list[dict[str, Any]] = Field(default_factory=list)


class ReviewTrendRecord(BaseModel):
    period: str
    total_reviews: int
    avg_rating: Optional[float] = None
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    verified_count: int
    snippet_count: int


# ─── Approvals ───────────────────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected|saved_for_later)$")
    notes: str = ""
    decided_by: str = "user"


class ApprovalOut(BaseModel):
    id: int
    recommendation_id: int
    decision: str
    decided_by: str
    notes: Optional[str] = ""
    decided_at: str


class RecommendationWithApproval(BaseModel):
    id: int
    run_id: int
    item_id: Optional[str] = None
    item_name: str
    action: str
    priority: Optional[str] = None
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None
    alternative_actions: list[str] = Field(default_factory=list)
    expected_benefits: Optional[str] = None
    potential_risks: Optional[str] = None
    missing_information: Optional[str] = None
    next_steps: list[str] = Field(default_factory=list)
    sales_metrics: Optional[dict[str, Any]] = None
    review_themes: Optional[dict[str, Any]] = None
    profitability: Optional[dict[str, Any]] = None
    requires_approval: bool = True
    success_metrics: Optional[str] = None
    created_at: Optional[str] = None
    approval: Optional[ApprovalOut] = None


# ─── Experiments ─────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    recommendation_id: Optional[int] = None
    title: str = Field(..., min_length=2)
    hypothesis: str = ""
    intervention: str = ""
    baseline_start: str = ""
    baseline_end: str = ""
    test_start: str = ""
    test_end: str = ""
    success_criteria: str = ""
    guardrail_metrics: str = ""
    status: str = "proposed"


class ExperimentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(proposed|approved|active|completed|cancelled)$")


class ExperimentResultCreate(BaseModel):
    metric_name: str
    baseline_value: Optional[float] = None
    test_value: Optional[float] = None
    change_pct: Optional[float] = None
    notes: str = ""


# ─── Food Waste ──────────────────────────────────────────────────────────────

class WasteRecordCreate(BaseModel):
    ingredient_name: str = Field(..., min_length=1)
    quantity: float = Field(..., ge=0)
    unit: str = "kg"
    unit_cost: float = Field(..., ge=0)
    waste_reason: str = ""
    associated_dish: str = ""
    image_item_name: Optional[str] = None
    image_confidence: Optional[float] = None
    verified_by_user: bool = True


class WasteIntelligenceOut(BaseModel):
    measured: dict[str, Any]
    spoilage: dict[str, Any]
    records: list[dict[str, Any]]
