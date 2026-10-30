"""
MenuMind AI — FastAPI Main Application Entry Point
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.connection import initialize_database
from api.routers import (
    restaurants,
    runs,
    ingestion,
    analytics,
    reviews,
    agent,
    recommendations,
    experiments,
    waste,
    reports,
    chat,
    menu_design,
)

logger = logging.getLogger("menumind.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Initializing SQLite database tables...")
    initialize_database()
    logger.info("MenuMind AI Backend API initialized.")
    yield
    logger.info("MenuMind AI Backend API shutting down.")


app = FastAPI(
    title="MenuMind AI API",
    description="Backend REST API for MenuMind AI Restaurant Review and Optimization Agent.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS Middleware ─────────────────────────────────────────────────────────
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allow any additional custom origins from environment
env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Exception Handler ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


# ─── System & Health Endpoints ───────────────────────────────────────────────
def _mask_key(key: str) -> str:
    """Safely mask secret keys so no plaintext is leaked."""
    if not key or not key.strip():
        return ""
    stripped = key.strip()
    if len(stripped) <= 8:
        return "configured (****)"
    return f"{stripped[:4]}...{stripped[-4:]}"


@app.get("/api/health", tags=["System"])
def healthcheck():
    """Health check endpoint for container monitoring and frontend readiness."""
    return {
        "status": "healthy",
        "service": "MenuMind AI API",
        "version": "2.0.0",
    }


@app.get("/api/health/integrations", tags=["System"])
def integration_healthcheck():
    """
    Validate external integrations, credentials, models, and persistence.
    Returns sanitized status without ever exposing plaintext secrets.
    """
    from config.settings import (
        GEMINI_API_KEY,
        SEARCH_API_KEY,
        SEARCH_ENGINE_ID,
        DATABASE_PATH,
        GEMINI_MODEL,
        GEMINI_CHAT_MODEL,
        GEMINI_VISION_MODEL,
        IMAGE_GENERATION_PROVIDER,
        IMAGE_GENERATION_API_KEY,
        IMAGE_GENERATION_MODEL,
    )
    from database.connection import get_connection

    # 1. Database check
    db_status = "error"
    db_tables_count = 0
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
        row = cursor.fetchone()
        db_tables_count = row[0] if row else 0
        conn.close()
        db_status = "connected"
    except Exception as exc:
        logger.warning("Database healthcheck issue: %s", exc)

    # 2. Gemini status
    gemini_configured = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())
    gemini_info = {
        "configured": gemini_configured,
        "masked_key": _mask_key(GEMINI_API_KEY),
        "primary_model": GEMINI_MODEL,
        "chat_model": GEMINI_CHAT_MODEL,
        "vision_model": GEMINI_VISION_MODEL,
        "mode": "live_llm" if gemini_configured else "rule_based_fallback",
    }

    # 3. Search / Review Retrieval
    search_configured = bool(SEARCH_API_KEY and SEARCH_API_KEY.strip())
    search_provider = "unconfigured"
    if search_configured:
        if SEARCH_ENGINE_ID and SEARCH_ENGINE_ID.strip():
            search_provider = "google_custom_search"
        else:
            search_provider = "serpapi"
    else:
        search_provider = "synthetic_fallback"

    search_info = {
        "configured": search_configured,
        "provider": search_provider,
        "masked_key": _mask_key(SEARCH_API_KEY),
        "has_custom_engine_id": bool(SEARCH_ENGINE_ID and SEARCH_ENGINE_ID.strip()),
    }

    # 4. Image Generation
    img_key = IMAGE_GENERATION_API_KEY or GEMINI_API_KEY
    img_configured = bool(img_key and img_key.strip())
    image_info = {
        "configured": img_configured,
        "provider_setting": IMAGE_GENERATION_PROVIDER,
        "effective_model": IMAGE_GENERATION_MODEL,
        "thematic_svg_generator": "available",
        "masked_key": _mask_key(img_key),
    }

    return {
        "status": "operational",
        "service": "MenuMind AI API",
        "version": "2.0.0",
        "database": {
            "status": db_status,
            "path": str(DATABASE_PATH),
            "table_count": db_tables_count,
        },
        "integrations": {
            "gemini": gemini_info,
            "external_search": search_info,
            "image_generation": image_info,
        },
    }


# ─── Register Routers ────────────────────────────────────────────────────────
app.include_router(restaurants.router)
app.include_router(runs.router)
app.include_router(ingestion.router)
app.include_router(analytics.router)
app.include_router(reviews.router)
app.include_router(agent.router)
app.include_router(recommendations.router)
app.include_router(experiments.router)
app.include_router(waste.router)
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(menu_design.router)
