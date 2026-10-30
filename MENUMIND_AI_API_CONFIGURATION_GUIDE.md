# MenuMind AI — API Configuration & Environment Guide

This comprehensive reference document outlines every external service, credential, environment variable, model identifier, and fallback mechanism used across the **MenuMind AI** restaurant intelligence platform.

---

## 1. Executive Summary & Integration Architecture

MenuMind AI integrates multiple AI and web intelligence providers to deliver automated menu review, sales matrix optimization, sentiment analysis, multi-agent conversational consulting, and publication-ready menu designs.

All external integrations are designed with **graceful degradation**: if any API key is missing, invalid, or rate-limited, the application does not crash. It automatically transitions to deterministic domain heuristics or local SVG vector synthesis.

### Quick Verification
You can inspect the operational health and integration readiness of your running deployment at any time:
```http
GET http://localhost:8000/api/health/integrations
```
Response format:
```json
{
  "status": "operational",
  "database": {
    "status": "connected",
    "path": "./menumind.db",
    "table_count": 15
  },
  "integrations": {
    "gemini": {
      "configured": true,
      "masked_key": "AQ.A...B5Ug",
      "primary_model": "gemini-2.8-flash",
      "chat_model": "gemini-2.8-flash",
      "vision_model": "gemini-2.5-flash",
      "mode": "live_llm"
    },
    "external_search": {
      "configured": true,
      "provider": "google_custom_search",
      "masked_key": "ee50...4654",
      "has_custom_engine_id": true
    },
    "image_generation": {
      "configured": true,
      "provider_setting": "auto",
      "effective_model": "imagen-3.0-generate-002",
      "thematic_svg_generator": "available"
    }
  }
}
```

---

## 2. API Key Inventory & Matrix

| Variable Name | Service Provider | Required / Optional | Code Locations | Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google AI Studio / Gemini API | **Required** (for AI features) | `agent/orchestrator.py`<br>`agent/multi_agent/*`<br>`services/waste_analysis_service.py` | Gracefully falls back to deterministic rule-based menu recommendations and local knowledge bases. |
| `SEARCH_API_KEY` | SerpApi **or** Google Custom Search | **Optional** | `services/review_retrieval_service.py` | Synthesizes realistic, domain-tailored mock reviews if web review count is $< 5$. |
| `SEARCH_ENGINE_ID` | Google Programmable Search | **Optional** (only if using Google CSE) | `services/review_retrieval_service.py` | If missing while `SEARCH_API_KEY` is set, system assumes SerpApi provider format. |
| `IMAGE_GENERATION_API_KEY` | Google Imagen / Gemini API | **Optional** | `agent/multi_agent/image_provider.py` | Uses `GEMINI_API_KEY` if omitted; falls back to vector SVG menu generation. |
| `DATABASE_PATH` | SQLite Engine | **Optional** (defaults to `./menumind.db`) | `database/connection.py`<br>`config/settings.py` | Uses local SQLite file in root directory. |
| `CORS_ORIGINS` | FastAPI Middleware | **Optional** | `api/main.py` | Allows standard local development ports (`5173`, `3000`). |

---

## 3. Google Gemini API (`GEMINI_API_KEY`)

### Purpose
Powers the core Agentic AI platform:
- **Central Orchestrator**: Intent classification, agent dispatching, and synthesizing unified responses.
- **Menu Consultant Specialist**: Menu matrix analysis (Stars, Plowhorses, Puzzles, Dogs), price elasticity recommendations.
- **Customer Voice Specialist**: Customer sentiment aggregation, dish mentions, feedback clustering.
- **Business Intelligence Specialist**: Profit margin modeling, revenue forecast, basket analysis.
- **Operations & Waste Specialist**: Spoilage analysis, batch size optimization, kitchen prep guidance.
- **Vision Menu Extraction**: OCR and entity extraction from uploaded food menu photos or PDF scans.

### How to Obtain
1. Navigate to **Google AI Studio**: [https://aistudio.google.com/](https://aistudio.google.com/)
2. Log in with your Google account.
3. In the left navigation, click **Get API key**.
4. Click **Create API key** and select an existing Google Cloud project (or create a new one).
5. Copy the generated key (starts with `AIzaSy...` or similar Google token prefix).
6. Set in your `.env` file:
   ```bash
   GEMINI_API_KEY=AIzaSy...your_key_here
   ```

### Supported Models
| Environment Variable | Recommended Value | Supported Alternatives | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_MODEL` | `gemini-2.0-flash` | `gemini-1.5-flash`, `gemini-1.5-pro` | Primary reasoning model for agent runs & tool execution. |
| `GEMINI_CHAT_MODEL` | `gemini-2.0-flash` | `gemini-2.5-flash`, `gemini-1.5-flash` | Sub-second latency model for conversational assistant chat. |
| `GEMINI_VISION_MODEL`| `gemini-2.0-flash` | `gemini-1.5-flash`, `gemini-2.5-flash` | Multimodal model for OCR and menu layout parsing. |

### Pricing & Free Tier Limits
- **Gemini 2.0 / 1.5 Flash Free Tier**:
  - **15 Requests Per Minute (RPM)**
  - **1,000,000 Tokens Per Minute (TPM)**
  - **1,500 Requests Per Day (RPD)**
  - **Free of charge** on Google AI Studio for experimentation and development.
- **Paid Pay-As-You-Go Tier**:
  - Input tokens: $\approx \$0.075$ per 1M tokens ($<128\text{k}$).
  - Output tokens: $\approx \$0.30$ per 1M tokens.

### Fallback Mechanism
If `GEMINI_API_KEY` is left blank or an API request encounters a network failure:
- **Assistant Chat**: Reverts to an expert rule-based knowledge engine that inspects active restaurant data (sales, top items, revenue) and formulates structured markdown recommendations.
- **Menu Recommendations**: Applies BCG/Menu Engineering matrix math ($x$-axis: sales volume median, $y$-axis: margin median) to deterministically classify items into Stars, Plowhorses, Puzzles, and Dogs.
- No crashes, blank pages, or unhandled exceptions occur.

---

## 4. External Review Retrieval API (`SEARCH_API_KEY`)

When a user uploads a restaurant dataset that contains fewer than 5 customer reviews, the `review_retrieval_service.py` automatically initiates external review search to gather authentic public feedback.

MenuMind AI supports **two distinct search backends**:

### Option 1: SerpApi (Default & Recommended)
- **Dashboard**: [https://serpapi.com/](https://serpapi.com/)
- **Setup**:
  1. Create a free account at SerpApi.
  2. Navigate to your dashboard and copy your **Private API Key**.
  3. Set in `.env`:
     ```bash
     SEARCH_API_KEY=your_serpapi_key_here
     SEARCH_ENGINE_ID=
     ```
- **Pricing & Free Tier**:
  - **100 free searches per month** (no credit card required).
  - Paid plans start at \$50/month for 5,000 searches.

### Option 2: Google Custom Search Engine (CSE)
- **Setup**:
  1. Open [Google Cloud Console](https://console.cloud.google.com/) and enable the **Custom Search API**.
  2. Generate an API Key under **APIs & Services $\rightarrow$ Credentials**.
  3. Create a search engine at [Google Programmable Search](https://programmablesearchengine.google.com/) and copy the **Search Engine ID (cx)**.
  4. Set in `.env`:
     ```bash
     SEARCH_API_KEY=your_google_cloud_api_key_here
     SEARCH_ENGINE_ID=your_custom_search_engine_id_here
     ```
- **Pricing & Free Tier**:
  - **100 free search queries per day**.
  - Subsequent queries billed at \$5 per 1,000 queries.

### Fallback Mechanism
If neither key is provided or search quota is exhausted, `review_retrieval_service.py` generates high-quality domain-specific synthetic reviews calibrated to the restaurant's cuisine, city, and active menu items.

---

## 5. Visual Menu Design Studio & Image Generation

The Visual Menu Studio renders publication-ready menu designs in modern typography and visual layouts.

### Provider Modes (`IMAGE_GENERATION_PROVIDER`)
```bash
IMAGE_GENERATION_PROVIDER=auto
```
- **`auto` (Recommended)**: Checks if `IMAGE_GENERATION_API_KEY` or `GEMINI_API_KEY` is present. If available, attempts Imagen 3; on any API limit or error, cleanly falls back to the high-resolution vector SVG generator.
- **`thematic_svg`**: Generates pure vector SVG art without making any external API calls. Ensures crisp rendering at any resolution with zero text distortion and instant loading.
- **`google_imagen`**: Connects to Google's Imagen model (`imagen-3.0-generate-002`).

### Supported Models
- `IMAGE_GENERATION_MODEL=imagen-3.0-generate-002`

---

## 6. Frontend Environment Configuration

The React + TypeScript frontend communicates with the FastAPI backend using TanStack Query and Axios.

| Variable Name | File | Purpose | Default |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `frontend/.env` | Backend API base URL | Empty string (routes through Vite reverse proxy at `http://localhost:8000`) |

### Local Development Proxy Setup
In `frontend/vite.config.ts`, requests matching `/api/*` are automatically forwarded to `http://127.0.0.1:8000`. You do not need to set `VITE_API_BASE_URL` during local development.

For production builds:
```bash
VITE_API_BASE_URL=https://api.menumind.example.com
```

---

## 7. Security & Key Management Best Practices

1. **Never Commit Secrets**:
   The `.gitignore` explicitly excludes `.env`, `*.db`, and credentials. Verify that `git status` never stages your `.env` file.
2. **Masked Diagnostics**:
   The `/api/health/integrations` endpoint always masks secrets (`AQ.A...B5Ug`), ensuring safe debugging and monitoring without credential leakage in browser devtools or log outputs.
3. **Environment Separation**:
   For CI/CD and automated testing, mock patches are configured in `tests/test_agent.py` and `tests/test_serpapi.py`. No real API credentials are required to run the full pytest test suite.
4. **Restricted Key Scope**:
   When generating Google Cloud / Gemini API keys, restrict them in the Google Cloud Console to only the **Generative Language API** to prevent lateral privilege escalation.

---

## 8. Integration Verification Runbook

Follow these quick commands to verify each integration:

### 1. Verify Full Health & Integrations
```bash
curl -s http://localhost:8000/api/health/integrations
```

### 2. Verify Multi-Agent Chat
```bash
curl -X POST http://localhost:8000/api/chat/conversations \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 4, "title": "Verification Test"}'
```

### 3. Verify Publication-Grade Menu Designer
```bash
curl -X POST http://localhost:8000/api/chat/conversations/1/menu-designs \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 4, "style_preset": "modern_minimalist", "include_visual_artwork": true}'
```

### 4. Run Pytest Suite
```bash
pytest -v
```
All 143+ backend tests pass with simulated integrations and deterministic fixtures.
