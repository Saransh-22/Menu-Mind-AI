# MenuMind AI 🍽️

**An Agentic AI System for Restaurant Menu Review and Optimization**

MenuMind AI helps restaurant owners make data-driven decisions about their menus by combining sales analytics, customer sentiment analysis and AI-powered recommendations using Google Gemini.

---

## Features

- 📁 **Data Upload** — Upload menu, sales, reviews and cost CSV/Excel files with flexible column mapping
- 🔍 **Data Quality Engine** — Automatic cleaning, duplicate detection, fuzzy item matching
- 📈 **Sales Analytics** — Revenue trends, category performance, price distribution (Plotly charts)
- ⭐ **Review Insights** — Sentiment analysis, theme extraction (local fallback + Gemini-powered)
- 🤖 **AI Agent** — Gemini-powered tool-calling loop generates evidence-backed recommendations
- 💡 **Recommendations** — IMPROVE / REMOVE / PROMOTE / REPRICE / INSUFFICIENT_EVIDENCE per item
- ✅ **Approvals** — Approve, reject or save recommendations; persisted across restarts (SQLite)
- 🧪 **Experiments** — Create, approve, run and evaluate menu experiments with follow-up data
- ♻️ **Food Waste Intelligence** — Gemini Vision food identification, verified waste logging and deterministic waste-cost analytics
- 📄 **Reports** — Download HTML report and CSV exports

---

## Requirements

- Python 3.11 or 3.12
- A Google Gemini API key (for AI recommendations — analytics work without it)
- Optional: Google Custom Search API key (for web review retrieval)

---

## Installation

```bash
# 1. Clone or copy the project
cd "Menu review and optimization agent"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in:

```env
# Required for AI recommendations
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: web review retrieval via Google Custom Search
SEARCH_API_KEY=your_google_search_api_key_here
SEARCH_ENGINE_ID=your_custom_search_engine_id_here

# Database location (default: ./menumind.db)
DATABASE_PATH=./menumind.db
```

**API Keys:**

| Key | Required | Purpose |
|-----|----------|---------|
| `GEMINI_API_KEY` | Required for AI recommendations | Gemini Flash model for sentiment + recommendations |
| `SEARCH_API_KEY` | Optional | **SerpApi** (primary) or Google Custom Search for web review retrieval |
| `SEARCH_ENGINE_ID` | Optional — only needed for Google Custom Search fallback | Programmable Search Engine ID |

The application **works without any API keys** — you get sales analytics, data validation and manual waste logging. Add `GEMINI_API_KEY` to enable AI recommendations and food-image identification.

---

## SerpApi Setup (Web Review Retrieval)

MenuMind AI uses **SerpApi** as the primary web review retrieval source. SerpApi provides
a structured JSON response from Google Search — no direct page scraping.

### 1. Get a SerpApi key

1. Create a free account at [https://serpapi.com](https://serpapi.com).
2. Copy your API key from the dashboard.
3. Paste it into your `.env` file as `SEARCH_API_KEY`.

```env
# .env
SEARCH_API_KEY=your_serpapi_key_here
```

> **Note:** `SEARCH_ENGINE_ID` is **not** required for SerpApi. It is only needed if
> you want to use the Google Custom Search API fallback.

### 2. How it works

- On each analysis run, if the number of uploaded reviews is below `MIN_REVIEWS_THRESHOLD` (default: 5), the agent automatically searches for `"<restaurant name>" <city> restaurant reviews` via SerpApi.
- Organic search snippets and local place-panel descriptions are extracted.
- Star ratings and dates are parsed from rich-snippet metadata when present.
- All retrieved results carry a source attribution (`SerpApi Google Search snippet`) so they can be distinguished from uploaded full reviews in the UI.

### 3. SerpApi limitations

| Limitation | Detail |
|------------|--------|
| Snippet-only | Only search result snippets (~150 chars) are retrieved — not full review pages. |
| Coverage | Only publicly indexed pages are covered. Private or JS-rendered review platforms (Yelp, TripAdvisor) are not included. |
| Freshness | Snippets reflect the search index cache, which may lag by days or weeks. |
| Free tier quota | The SerpApi free plan allows 100 searches/month. Paid plans start at $50/month for 5 000 searches. |
| Rate limits | HTTP 429 responses are handled gracefully; the agent logs the error and continues without reviews. |
| No fabrication | Missing ratings, dates or source names are left as `null` — never filled with invented data. |

### 4. Fallback order

1. **SerpApi** (requires `SEARCH_API_KEY` only)
2. **Google Custom Search API** (requires `SEARCH_API_KEY` + `SEARCH_ENGINE_ID`)
3. **No source** — upload `reviews.csv` for offline analysis

---

## Running the Application

```bash
streamlit run app.py
```

The application will open at `http://localhost:8501`.

---

## Workflow

1. **Overview** — Create a restaurant and analysis run
2. **Data Upload** — Upload `menu.csv` and `sales.csv` (required); `reviews.csv` and `costs.csv` (optional)
3. **Sales Analytics** — Explore revenue, trends and category performance
4. **Review Insights** — View sentiment and themes from uploaded or retrieved reviews
5. **Food Waste Intelligence** — Optionally upload a kitchen image, verify visible items and record actual discarded quantities
6. **AI Recommendations** — Click "Run AI Analysis" to combine available evidence
6. **Experiments** — Create and track menu change experiments
7. **Reports** — Download HTML or CSV exports

---

## Supported CSV Schemas

### menu.csv
| Column | Required | Notes |
|--------|----------|-------|
| `item_name` | ✅ | Flexible aliases: name, dish, product |
| `price` | Recommended | selling_price, unit_price |
| `category` | Optional | section, group, type |
| `description` | Optional | desc, details |
| `item_id` | Optional | sku, product_id |
| `restaurant_id` | Optional | rest_id |

### sales.csv
| Column | Required | Notes |
|--------|----------|-------|
| `item_id` or `item_name` | ✅ | At least one identifier |
| `date` | ✅ | Most date formats supported |
| `quantity_sold` | ✅ | qty, units |
| `revenue` | ✅ | total, amount |
| `discount` | Optional | |
| `transaction_id` | Optional | Used for duplicate detection |

### reviews.csv
| Column | Required | Notes |
|--------|----------|-------|
| `review_text` | ✅ | text, comment, feedback |
| `source` | Recommended | Platform name |
| `source_url` | Recommended | URL of the review |
| `rating` | Optional | score, stars |
| `item_name` | Optional | For item-level analysis |
| `review_date` | Optional | |

### costs.csv
| Column | Required | Notes |
|--------|----------|-------|
| `item_id` | ✅ | Matched to menu item_id |
| `ingredient_cost` | ✅ | food_cost, cogs |
| `packaging_cost` | Optional | |

---

## Running Tests

```bash
pytest
```

Tests use temporary SQLite databases and mocked API calls — no API keys or internet required.

```bash
# Run specific test file
pytest tests/test_preprocessing.py -v
pytest tests/test_analytics.py -v
pytest tests/test_agent.py -v
pytest tests/test_recommendations.py -v
pytest tests/test_database.py -v
```

---

## Project Structure

```
menumind-ai/
├── app.py                  # Streamlit entry point
├── requirements.txt
├── .env.example
├── pytest.ini
├── config/
│   └── settings.py         # Environment-based configuration
├── agent/
│   ├── orchestrator.py     # Main agent loop
│   ├── tools.py            # Tool implementations (real Python code)
│   ├── state.py            # Agent state management
│   └── schemas.py          # Pydantic validated types
├── services/
│   ├── ingestion_service.py        # CSV/Excel loading + column mapping
│   ├── preprocessing_service.py    # Cleaning, validation, quality scoring
│   ├── analytics_service.py        # Deterministic sales + profitability
│   ├── sentiment_service.py        # Local + Gemini sentiment analysis
│   ├── review_retrieval_service.py # Pluggable review source adapters
│   └── report_service.py           # HTML + CSV report generation
├── database/
│   ├── connection.py       # SQLite connection + WAL mode
│   ├── models.py           # DDL CREATE TABLE statements
│   └── repository.py       # Typed data-access functions
├── ui/
│   ├── dashboard.py        # Overview page
│   ├── upload_page.py      # File upload + quality reports
│   ├── analytics_page.py   # Sales analytics + Plotly charts
│   ├── review_page.py      # Review insights + sentiment
│   ├── recommendations_page.py  # AI recommendations + approvals
│   ├── experiments_page.py # Experiment creation + outcome tracking
│   └── reports_page.py     # Download reports
├── sample_data/
│   ├── menu.csv
│   ├── sales.csv
│   ├── reviews.csv
│   └── costs.csv
└── tests/
    ├── test_preprocessing.py
    ├── test_analytics.py
    ├── test_agent.py
    ├── test_recommendations.py
    └── test_database.py
```

---

## Review Source Limitations

- Web review retrieval uses **SerpApi** (primary) or the **Google Custom Search API** (fallback) — no direct scraping of Google Maps, Yelp or other platforms.
- Only publicly indexed search result snippets are retrieved, not full review pages.
- For SerpApi: `SEARCH_API_KEY` alone is sufficient; `SEARCH_ENGINE_ID` is not required.
- For Google Custom Search: both `SEARCH_API_KEY` and `SEARCH_ENGINE_ID` are required.
- SerpApi free plan: 100 searches/month. Rate-limit errors (HTTP 429) are handled gracefully.
- Sentiment analysis on short snippets has lower accuracy than on full reviews — flagged in the UI.
- Without any API keys, upload a `reviews.csv` file for offline sentiment analysis.

---

## Known Constraints

- Review snippets retrieved via search are short and may be incomplete
- Sentiment analysis accuracy depends on review volume (flagged when < 3 reviews)
- Profitability cannot be calculated without cost data (clearly indicated in UI)
- The agent does not automatically apply any business changes — all actions require human approval
- Gemini API calls consume quota; the `AGENT_MAX_TOOL_CALLS` environment variable limits agent steps (default: 20)

---

## Security Notes

- API keys are loaded from `.env` only — never exposed in the UI
- Uploaded files are validated for type and content before processing
- Retrieved review content is treated as untrusted data — not executed as instructions
- Stack traces are caught and logged, not shown to users


## Food Waste Intelligence

- Upload a kitchen waste image (JPEG, PNG or WEBP; maximum 10 MB).
- Gemini Vision identifies candidate visible food items; staff must verify them.
- Staff enter the actual discarded quantity, unit and cost per unit.
- Waste cost is calculated deterministically as verified quantity × entered unit cost.
- The agent can include saved waste records in its recommendation context.
- Images cannot establish actual weight, freshness, discard status or food safety.
- If image analysis is unavailable, waste records can still be entered manually.

Waste records are associated with the active analysis run in SQLite. Uploaded image bytes are not stored in the database; only filename, MIME type and detection metadata are retained.
