"""
FastAPI Router: Visual Menu Design Studio, Generation, and Asset Export.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from agent.multi_agent.specialists.menu_design import MenuDesignAgent
from agent.multi_agent.types import (
    DesignSpecification,
    GeneratedMenuDesign,
    StructuredMenuDraft,
)
from config.settings import ASSETS_DIR
from database import repository as repo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Menu Design Studio"])
menu_designer = MenuDesignAgent()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GenerateDesignRequest(BaseModel):
    menu_draft: StructuredMenuDraft
    spec: DesignSpecification = Field(default_factory=DesignSpecification)


class UpdateDesignRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    menu_draft: Optional[StructuredMenuDraft] = None
    spec: Optional[DesignSpecification] = None


class RegenerateDesignRequest(BaseModel):
    style: str
    palette: Optional[list[str]] = None
    layout: Optional[str] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/api/chat/conversations/{conversation_id}/menu-designs",
    response_model=GeneratedMenuDesign,
    status_code=status.HTTP_201_CREATED,
)
def generate_menu_design_endpoint(
    conversation_id: str,
    payload: GenerateDesignRequest,
):
    """Generate a publication-grade customer-facing visual menu design."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    restaurant_id = conv["restaurant_id"]
    restaurant = repo.get_restaurant(restaurant_id)
    rest_name = restaurant["name"] if restaurant else "Restaurant"
    cuisine = restaurant.get("category") or "Multi-cuisine"

    design = menu_designer.create_menu_design(
        restaurant_id=restaurant_id,
        restaurant_name=rest_name,
        cuisine=cuisine,
        menu_draft=payload.menu_draft,
        spec=payload.spec,
        conversation_id=conversation_id,
    )
    return design


@router.get(
    "/api/chat/conversations/{conversation_id}/menu-designs",
    response_model=list[GeneratedMenuDesign],
)
def list_conversation_menu_designs(conversation_id: str):
    """List all generated menu designs associated with a conversation."""
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    assets = repo.list_generated_assets(conv["restaurant_id"], asset_type="menu_design")
    # Filter by conversation if associated
    conv_assets = [a for a in assets if a.get("conversation_id") == conversation_id or not a.get("conversation_id")]

    results = []
    for a in conv_assets:
        cnt = a.get("content")
        if isinstance(cnt, dict):
            try:
                results.append(GeneratedMenuDesign(**cnt))
            except Exception:
                pass
    return results


@router.get("/api/chat/menu-designs/{design_id}", response_model=GeneratedMenuDesign)
def get_menu_design(design_id: str):
    """Retrieve full specification and preview of a menu design."""
    asset = repo.get_generated_asset(design_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Menu design not found")

    cnt = asset.get("content")
    if isinstance(cnt, dict):
        return GeneratedMenuDesign(**cnt)
    raise HTTPException(status_code=500, detail="Corrupted design content structure")


@router.patch("/api/chat/menu-designs/{design_id}", response_model=GeneratedMenuDesign)
def update_menu_design(design_id: str, payload: UpdateDesignRequest):
    """Update title, approval status, or menu draft in an existing design."""
    asset = repo.get_generated_asset(design_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Menu design not found")

    cnt = asset.get("content")
    if not isinstance(cnt, dict):
        raise HTTPException(status_code=500, detail="Corrupted design content")

    design = GeneratedMenuDesign(**cnt)
    if payload.title:
        design.title = payload.title
    if payload.status:
        design.status = payload.status
    if payload.menu_draft:
        design.menu_draft = payload.menu_draft
    if payload.spec:
        design.spec = payload.spec

    repo.update_asset_status(
        asset_id=design_id,
        status=design.status,
        content=design.model_dump(mode="json"),
    )
    return design


@router.post("/api/chat/menu-designs/{design_id}/regenerate", response_model=GeneratedMenuDesign)
def regenerate_menu_design(design_id: str, payload: RegenerateDesignRequest):
    """Regenerate visual artwork and layout with a new design style or palette."""
    asset = repo.get_generated_asset(design_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Menu design not found")

    cnt = asset.get("content")
    if not isinstance(cnt, dict):
        raise HTTPException(status_code=500, detail="Corrupted design content")

    old_design = GeneratedMenuDesign(**cnt)
    restaurant_id = asset["restaurant_id"]
    restaurant = repo.get_restaurant(restaurant_id)
    rest_name = restaurant["name"] if restaurant else "Restaurant"
    cuisine = restaurant.get("category") or "Multi-cuisine"

    new_spec = old_design.spec.model_copy()
    new_spec.style = payload.style
    if payload.palette:
        new_spec.palette = payload.palette
    if payload.layout:
        new_spec.layout = payload.layout

    new_design = menu_designer.create_menu_design(
        restaurant_id=restaurant_id,
        restaurant_name=rest_name,
        cuisine=cuisine,
        menu_draft=old_design.menu_draft,
        spec=new_spec,
        conversation_id=asset.get("conversation_id"),
    )
    return new_design


@router.get("/api/chat/menu-designs/{design_id}/export")
def export_menu_design(design_id: str, format: str = Query(default="html")):
    """Export self-contained print-ready HTML deliverable."""
    asset = repo.get_generated_asset(design_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Menu design not found")

    cnt = asset.get("content")
    if not isinstance(cnt, dict):
        raise HTTPException(status_code=500, detail="Invalid design content")

    design = GeneratedMenuDesign(**cnt)
    html_content = design.html_preview or "<p>No preview content.</p>"

    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f'attachment; filename="menumind_{design_id}.html"'
        },
    )


# ─── Static Asset Streaming Route ────────────────────────────────────────────

@router.get("/api/assets/{restaurant_id}/{subpath:path}")
def serve_asset_file(restaurant_id: int, subpath: str):
    """Safely stream generated artwork, designs, and attachments from disk."""
    file_path = (ASSETS_DIR / str(restaurant_id) / subpath).resolve()
    # Path traversal guard
    if not str(file_path).startswith(str(ASSETS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    mime = "application/octet-stream"
    ext = file_path.suffix.lower()
    if ext == ".svg":
        mime = "image/svg+xml"
    elif ext in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif ext == ".png":
        mime = "image/png"
    elif ext == ".html":
        mime = "text/html; charset=utf-8"

    return FileResponse(file_path, media_type=mime)
