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
@app.get("/api/health", tags=["System"])
def healthcheck():
    """Health check endpoint for container monitoring and frontend readiness."""
    return {
        "status": "healthy",
        "service": "MenuMind AI API",
        "version": "2.0.0",
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
