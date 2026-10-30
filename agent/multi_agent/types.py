"""
Data structures, schemas, and events for the Multi-Agent System.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentIntent(str, Enum):
    MENU_CONSULTING = "menu_consulting"
    MENU_DESIGN = "menu_design"
    BUSINESS_INTELLIGENCE = "business_intelligence"
    CUSTOMER_VOICE = "customer_voice"
    OPERATIONS_WASTE = "operations_waste"
    GENERAL_INQUIRY = "general_inquiry"
    MULTI_SPECIALIST = "multi_specialist"


class AgentActivityEvent(BaseModel):
    step: str
    agent_name: str
    message: str
    status: str = "running"  # running, completed, error
    timestamp: Optional[str] = None


class StructuredMenuItem(BaseModel):
    id: Optional[str] = None
    name: str
    category: str
    price: float
    description: Optional[str] = ""
    cost: Optional[float] = None
    margin_pct: Optional[float] = None
    dietary_tags: list[str] = Field(default_factory=list)  # e.g. ["Vegetarian", "Gluten-Free", "Chef Special"]
    confidence: float = 1.0
    notes: Optional[str] = None


class StructuredMenuCategory(BaseModel):
    category: str
    items: list[StructuredMenuItem] = Field(default_factory=list)


class StructuredMenuDraft(BaseModel):
    title: str
    concept: Optional[str] = None
    currency: str = "₹"
    categories: list[StructuredMenuCategory] = Field(default_factory=list)
    total_items: int = 0
    indicative_avg_bill: Optional[float] = None
    pricing_rationale: Optional[str] = None
    notes: Optional[str] = None


class DesignSpecification(BaseModel):
    style: str = "Modern Minimalist"  # Premium Fine Dining, Modern Minimalist, Traditional Indian, Cafe & Bakery, Street Food, Luxury Black & Gold, Fresh & Organic, Contemporary Fusion
    palette: list[str] = Field(default_factory=lambda: ["#183B32", "#F7F5EF", "#D97757", "#D6A64F"])
    font_family: str = "serif"  # serif, sans, display
    layout: str = "two_column"  # single_column, two_column, magazine, grid
    page_size: str = "A4"       # A4, US_Letter, Square, Digital_Menu
    orientation: str = "portrait" # portrait, landscape
    background_theme: str = "warm_cream_texture"
    include_descriptions: bool = True
    include_prices: bool = True


class GeneratedMenuDesign(BaseModel):
    design_id: str
    title: str
    style: str
    preview_url: Optional[str] = None
    html_preview: Optional[str] = None
    svg_artwork_url: Optional[str] = None
    status: str = "completed"
    spec: DesignSpecification
    menu_draft: StructuredMenuDraft
    created_at: Optional[str] = None


class AgentResponse(BaseModel):
    content: str
    specialist_agent: str
    intent: AgentIntent
    tools_called: list[str] = Field(default_factory=list)
    activity_events: list[AgentActivityEvent] = Field(default_factory=list)
    menu_draft: Optional[StructuredMenuDraft] = None
    menu_design: Optional[GeneratedMenuDesign] = None
    suggested_followups: list[str] = Field(default_factory=list)
    attachments: list[dict] = Field(default_factory=list)
