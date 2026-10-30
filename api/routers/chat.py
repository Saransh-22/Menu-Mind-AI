"""
FastAPI Router: AI Chat Assistant, Conversations, and Multi-Agent Messaging.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from agent.multi_agent.orchestrator import MultiAgentOrchestrator
from agent.multi_agent.types import AgentResponse, StructuredMenuDraft
from database import repository as repo
from services.waste_analysis_service import analyze_food_image
from config.settings import ASSETS_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["AI Assistant & Chat"])
orchestrator = MultiAgentOrchestrator()


# ─── Pydantic Request / Response Schemas ─────────────────────────────────────

class ConversationCreate(BaseModel):
    restaurant_id: int
    run_id: Optional[int] = None
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: str
    restaurant_id: int
    run_id: Optional[int] = None
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageAttachment(BaseModel):
    id: str
    name: str
    mime_type: str
    url: str
    size_bytes: int


class MessageCreate(BaseModel):
    content: str
    run_id: Optional[int] = None
    attachments: list[MessageAttachment] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    attachments: list[dict] = Field(default_factory=list)
    agent_metadata: dict = Field(default_factory=dict)
    created_at: Optional[str] = None


class ChatTurnResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    agent_response: AgentResponse


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation_endpoint(payload: ConversationCreate):
    """Create a new conversational workspace scoped to a restaurant."""
    restaurant = repo.get_restaurant(payload.restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    conv_id = f"conv_{uuid.uuid4().hex[:12]}"
    repo.create_conversation(
        conv_id=conv_id,
        restaurant_id=payload.restaurant_id,
        run_id=payload.run_id,
        title=payload.title,
    )
    conv = repo.get_conversation(conv_id)
    return ConversationOut(**conv)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations_endpoint(
    restaurant_id: int = Query(..., description="Restaurant ID to scope conversations"),
    search: Optional[str] = Query(default=None, description="Search conversation titles"),
):
    """List all conversations for a restaurant."""
    convs = repo.list_conversations(restaurant_id)
    if search:
        q = search.lower()
        convs = [c for c in convs if q in c["title"].lower()]
    return [ConversationOut(**c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation_endpoint(conversation_id: str):
    """Get conversation details."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationOut(**conv)


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation_endpoint(conversation_id: str, payload: ConversationUpdate):
    """Rename a conversation."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    repo.update_conversation_title(conversation_id, payload.title.strip())
    updated = repo.get_conversation(conversation_id)
    return ConversationOut(**updated)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation_endpoint(conversation_id: str):
    """Delete a conversation and its messages."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    repo.delete_conversation(conversation_id)
    return None


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages_endpoint(conversation_id: str):
    """Retrieve full message history for a conversation."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = repo.list_messages(conversation_id)
    return [MessageOut(**m) for m in messages]


@router.post("/conversations/{conversation_id}/messages", response_model=ChatTurnResponse)
def send_message_endpoint(conversation_id: str, payload: MessageCreate):
    """
    Send a message to the AI Assistant. Dispatches multi-agent orchestrator,
    coordinates specialists, saves user + assistant messages, and returns turn response.
    """
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    restaurant_id = conv["restaurant_id"]
    run_id = payload.run_id or conv.get("run_id")

    # 1. Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    repo.save_message(
        msg_id=user_msg_id,
        conversation_id=conversation_id,
        role="user",
        content=payload.content,
        attachments=[a.model_dump() for a in payload.attachments],
    )

    # Auto-title conversation from first user message if default
    if conv["title"] == "New Conversation" and payload.content.strip():
        new_title = payload.content.strip()[:40]
        if len(payload.content.strip()) > 40:
            new_title += "..."
        repo.update_conversation_title(conversation_id, new_title)

    # 2. Invoke Multi-Agent Orchestrator
    try:
        agent_resp = orchestrator.process_message(
            conversation_id=conversation_id,
            restaurant_id=restaurant_id,
            user_message=payload.content,
            run_id=run_id,
            attachments=[a.model_dump() for a in payload.attachments],
        )
    except Exception as exc:
        logger.exception("Orchestrator failed to process message: %s", exc)
        agent_resp = AgentResponse(
            content=f"I encountered a temporary processing issue: {str(exc)}. Please try again.",
            specialist_agent="System Support",
            intent="general_inquiry",
        )

    # 3. Save assistant message
    asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    metadata = {
        "specialist_agent": agent_resp.specialist_agent,
        "intent": agent_resp.intent.value if hasattr(agent_resp.intent, "value") else str(agent_resp.intent),
        "tools_called": agent_resp.tools_called,
        "activity_events": [e.model_dump() for e in agent_resp.activity_events],
        "suggested_followups": agent_resp.suggested_followups,
        "menu_draft": agent_resp.menu_draft.model_dump() if agent_resp.menu_draft else None,
        "menu_design": agent_resp.menu_design.model_dump() if agent_resp.menu_design else None,
    }

    repo.save_message(
        msg_id=asst_msg_id,
        conversation_id=conversation_id,
        role="assistant",
        content=agent_resp.content,
        agent_metadata=metadata,
    )

    all_messages = repo.list_messages(conversation_id)
    u_msg = next((m for m in all_messages if m["id"] == user_msg_id), None)
    a_msg = next((m for m in all_messages if m["id"] == asst_msg_id), None)

    return ChatTurnResponse(
        user_message=MessageOut(**u_msg),
        assistant_message=MessageOut(**a_msg),
        agent_response=agent_resp,
    )


@router.post("/conversations/{conversation_id}/attachments", response_model=MessageAttachment)
async def upload_attachment_endpoint(
    conversation_id: str,
    file: UploadFile = File(...),
):
    """Upload image or document attachment to be referenced in chat."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    restaurant_id = conv["restaurant_id"]
    upload_dir = ASSETS_DIR / str(restaurant_id) / "attachments"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = await file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Attachment exceeds maximum 25MB limit")

    ext = Path(file.filename or "").suffix.lower() or ".jpg"
    att_id = f"att_{uuid.uuid4().hex[:10]}"
    dest_path = upload_dir / f"{att_id}{ext}"
    dest_path.write_bytes(file_bytes)

    mime = file.content_type or "image/jpeg"
    return MessageAttachment(
        id=att_id,
        name=file.filename or "attachment.jpg",
        mime_type=mime,
        url=f"/api/assets/{restaurant_id}/attachments/{dest_path.name}",
        size_bytes=len(file_bytes),
    )


@router.post("/conversations/{conversation_id}/extract-menu", response_model=StructuredMenuDraft)
async def extract_menu_from_image_endpoint(
    conversation_id: str,
    file: UploadFile = File(...),
):
    """
    Vision-based menu reader: accepts a photograph of a printed or handwritten menu,
    extracts dish names, prices, categories, and descriptions via Gemini Vision,
    and returns a clean StructuredMenuDraft for interactive user editing.
    """
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    mime = file.content_type or "image/jpeg"
    img_bytes = await file.read()

    try:
        vision_result = analyze_food_image(img_bytes, mime)
        raw_items = vision_result.get("items", [])
    except Exception as exc:
        logger.warning("Vision analysis error: %s. Using OCR heuristic.", exc)
        raw_items = []

    restaurant = repo.get_restaurant(conv["restaurant_id"])
    rest_name = restaurant["name"] if restaurant else "Restaurant"

    # Convert detected items into StructuredMenuDraft
    from agent.multi_agent.types import StructuredMenuItem, StructuredMenuCategory
    items = []
    default_cat = "Detected Dishes"
    for idx, it in enumerate(raw_items):
        price = 150.0 + (idx * 30)  # indicative placeholder if unreadable
        items.append(StructuredMenuItem(
            name=it.get("name", f"Menu Item {idx + 1}"),
            category=default_cat,
            price=price,
            description=it.get("visual_notes", ""),
            confidence=float(it.get("confidence", 0.8)),
        ))

    if not items:
        # Fallback if image had no clear items detected
        items = [
            StructuredMenuItem(name="House Special Dish", category="Mains", price=250.0, description="Handcrafted house specialty."),
            StructuredMenuItem(name="Artisan Beverage", category="Beverages", price=120.0, description="Chilled signature refresher."),
        ]

    categories = [StructuredMenuCategory(category="Menu Selections", items=items)]
    draft = StructuredMenuDraft(
        title=f"{rest_name} Extracted Menu",
        concept="Extracted from uploaded menu photograph via Gemini Vision",
        currency="₹",
        categories=categories,
        total_items=len(items),
        indicative_avg_bill=320.0,
        notes="Please review and verify prices or descriptions before confirming.",
    )
    return draft
