"""
MenuMind AI — Application Configuration
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "menumind.db"))

# ─── API Keys ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "")

# ─── Agent Settings ───────────────────────────────────────────────────────────
AGENT_MAX_TOOL_CALLS = int(os.getenv("AGENT_MAX_TOOL_CALLS", "15"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.4"))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "4096"))

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ─── Upload Limits ────────────────────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

# ─── Fuzzy Matching ───────────────────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = 80       # 0-100 — below this score flag as ambiguous
FUZZY_AUTO_ACCEPT = 95           # auto-accept matches above this score

# ─── Review Retrieval ─────────────────────────────────────────────────────────
MIN_REVIEWS_THRESHOLD = 5        # fetch web reviews if uploaded count is below
REVIEW_RETRIEVAL_TIMEOUT = 15    # seconds per HTTP request
SERPAPI_BASE_URL = "https://serpapi.com/search.json"  # SerpApi Google Search endpoint

# ─── Confidence Levels ────────────────────────────────────────────────────────
CONFIDENCE_HIGH = 0.75
CONFIDENCE_MEDIUM = 0.50
CONFIDENCE_LOW = 0.25

# ─── Multi-Agent & Chat Settings ──────────────────────────────────────────────
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", GEMINI_MODEL)
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", GEMINI_MODEL)
IMAGE_GENERATION_PROVIDER = os.getenv("IMAGE_GENERATION_PROVIDER", "auto").lower()
IMAGE_GENERATION_API_KEY = os.getenv("IMAGE_GENERATION_API_KEY", "")
IMAGE_GENERATION_MODEL = os.getenv("IMAGE_GENERATION_MODEL", "imagen-3.0-generate-002")

ASSETS_DIR = BASE_DIR / "data" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

