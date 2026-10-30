"""
Review retrieval adapter.
Pluggable architecture — each source implements the ReviewSource interface.
Only retrieves from sources with permitted terms of service.

Source priority order:
  1. SerpApiSource          — Google Search via SerpApi (uses SEARCH_API_KEY)
  2. GoogleCustomSearchSource — Google Custom Search API (uses SEARCH_API_KEY + SEARCH_ENGINE_ID)
  3. NullReviewSource       — fallback when nothing is configured
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import re
import requests

from config.settings import (
    SEARCH_API_KEY,
    SEARCH_ENGINE_ID,
    REVIEW_RETRIEVAL_TIMEOUT,
    SERPAPI_BASE_URL,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievedReview:
    review_text: str
    source: str
    source_url: str
    item_name: Optional[str] = None
    rating: Optional[float] = None
    review_date: Optional[str] = None
    attribution: str = ""
    is_snippet: bool = True
    review_type: str = "search_snippet"


@dataclass
class RetrievalResult:
    reviews: list[RetrievedReview] = field(default_factory=list)
    source: str = ""
    source_url: str = ""
    limitations: list[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None


class ReviewSource(ABC):
    """Abstract base for all review retrieval adapters."""

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def retrieve(self, restaurant_name: str, city: str,
                 website: Optional[str] = None) -> RetrievalResult: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


# ──────────────────────────── Google Custom Search ────────────────────────────

class GoogleCustomSearchSource(ReviewSource):
    """
    Retrieves publicly available review snippets via Google Custom Search API.
    Only uses the official API — does not scrape any website directly.
    Each request respects rate limits and API quotas.
    """

    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    name = "Google Custom Search API"

    def is_available(self) -> bool:
        return bool(SEARCH_API_KEY and SEARCH_ENGINE_ID)

    def retrieve(self, restaurant_name: str, city: str,
                 website: Optional[str] = None) -> RetrievalResult:
        if not self.is_available():
            return RetrievalResult(
                source=self.name,
                limitations=[
                    "SEARCH_API_KEY or SEARCH_ENGINE_ID not configured. "
                    "Set these environment variables to enable web review retrieval."
                ],
                success=False,
                error="API key not configured.",
            )

        query = f'"{restaurant_name}" {city} restaurant reviews'
        params = {
            "key": SEARCH_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "q": query,
            "num": 10,
        }
        try:
            resp = requests.get(
                self.BASE_URL, params=params, timeout=REVIEW_RETRIEVAL_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return RetrievalResult(
                source=self.name,
                limitations=["Search API request failed."],
                success=False,
                error=str(e),
            )

        reviews: list[RetrievedReview] = []
        for item in data.get("items", []):
            snippet = item.get("snippet", "").strip()
            link = item.get("link", "")
            if len(snippet) < 20:
                continue
            reviews.append(
                RetrievedReview(
                    review_text=snippet,
                    source=self.name,
                    source_url=link,
                    attribution="Google Custom Search API snippet",
                )
            )
            time.sleep(0.2)  # rate limit courtesy

        return RetrievalResult(
            reviews=reviews,
            source=self.name,
            source_url=self.BASE_URL,
            limitations=[
                "Only search result snippets are retrieved — not full reviews.",
                "Coverage limited to publicly indexed pages.",
                "Snippets may be out of date.",
            ],
            success=True,
        )


# ──────────────────────────── SerpApi Source ─────────────────────────────────

class SerpApiSource(ReviewSource):
    """
    Retrieves publicly available review snippets via the SerpApi Google Search
    JSON API (https://serpapi.com/google-search-api).

    Only the official SerpApi endpoint is used — no direct page scraping.
    Extracts: review snippets, star ratings, dates, source names and URLs
    from organic results and (when present) the local_results block.

    Never fabricates reviews or fills missing fields with invented data.
    """

    name = "SerpApi Google Search"

    # SerpApi result fields considered useful as review snippets
    _MIN_SNIPPET_LEN = 20

    def is_available(self) -> bool:
        """Available when SEARCH_API_KEY is set (no SEARCH_ENGINE_ID needed)."""
        return bool(SEARCH_API_KEY)

    def retrieve(
        self,
        restaurant_name: str,
        city: str,
        website: Optional[str] = None,
    ) -> RetrievalResult:
        if not self.is_available():
            return RetrievalResult(
                source=self.name,
                limitations=[
                    "SEARCH_API_KEY not configured. "
                    "Set SEARCH_API_KEY in your .env to enable SerpApi review retrieval."
                ],
                success=False,
                error="SEARCH_API_KEY not configured.",
            )

        query = f'"{restaurant_name}" {city} restaurant reviews'
        params = {
            "engine": "google",
            "q": query,
            "api_key": SEARCH_API_KEY,
            "num": 10,
            "gl": "us",
            "hl": "en",
        }

        try:
            resp = requests.get(
                SERPAPI_BASE_URL,
                params=params,
                timeout=REVIEW_RETRIEVAL_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return RetrievalResult(
                source=self.name,
                limitations=["SerpApi request timed out."],
                success=False,
                error="Request timed out after "
                      f"{REVIEW_RETRIEVAL_TIMEOUT}s.",
            )
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 401:
                msg = "Invalid SerpApi credentials (HTTP 401). Check SEARCH_API_KEY."
            elif status == 429:
                msg = "SerpApi rate limit exceeded (HTTP 429). Retry later."
            else:
                msg = f"SerpApi HTTP error {status}."
            return RetrievalResult(
                source=self.name,
                limitations=[msg],
                success=False,
                error=msg,
            )
        except requests.RequestException as exc:
            return RetrievalResult(
                source=self.name,
                limitations=["SerpApi network error."],
                success=False,
                error=str(exc),
            )

        # Check for API-level errors returned as JSON
        if "error" in data:
            api_err = str(data["error"])
            return RetrievalResult(
                source=self.name,
                limitations=[f"SerpApi API error: {api_err}"],
                success=False,
                error=api_err,
            )

        reviews: list[RetrievedReview] = []
        seen_texts: set[str] = set()

        # ── Extract from organic results ──────────────────────────────────
        for item in data.get("organic_results", []):
            snippet = (item.get("snippet") or "").strip()
            link = item.get("link") or ""
            source_name = item.get("source") or self.name

            if len(snippet) < self._MIN_SNIPPET_LEN:
                continue
            if snippet in seen_texts:
                continue  # deduplicate
            seen_texts.add(snippet)

            # Some SerpApi snippets include a date prefix like "Jan 5, 2024 — "
            review_date: Optional[str] = None
            date_info = item.get("date")
            if date_info:
                review_date = str(date_info)

            # Rating may appear in rich snippet extensions
            rating: Optional[float] = None
            rich = item.get("rich_snippet", {})
            top = rich.get("top", {})
            ext = top.get("extensions", [])
            for ext_item in ext:
                try:
                    val = float(str(ext_item).split("/")[0].strip())
                    if 0.0 <= val <= 5.0:
                        rating = val
                        break
                except (ValueError, IndexError):
                    continue

            reviews.append(
                RetrievedReview(
                    review_text=snippet,
                    source=source_name,
                    source_url=link,
                    rating=rating,
                    review_date=review_date,
                    attribution="SerpApi Google Search snippet",
                )
            )
            time.sleep(0.1)  # polite rate-limit delay

        # ── Extract from local_results block (places panel) ───────────────
        local_res = data.get("local_results", [])
        if isinstance(local_res, dict):
            places = local_res.get("places", [])
        elif isinstance(local_res, list):
            places = local_res
        else:
            places = []

        for place in places:
            if not isinstance(place, dict):
                continue
            # Local results carry overall ratings but not individual reviews;
            # we record them only when a review snippet is available.
            snippet = (place.get("description") or place.get("snippet") or "").strip()
            link = place.get("links", {}).get("website") if isinstance(place.get("links"), dict) else (place.get("place_id") or "")
            source_name = place.get("title") or self.name

            # Overall rating from place card
            rating_raw = place.get("rating")
            try:
                rating = float(rating_raw) if rating_raw is not None else None
            except (ValueError, TypeError):
                rating = None

            if len(snippet) < self._MIN_SNIPPET_LEN or snippet in seen_texts:
                continue
            seen_texts.add(snippet)

            reviews.append(
                RetrievedReview(
                    review_text=snippet,
                    source=source_name,
                    source_url=link,
                    rating=rating,
                    review_date=None,
                    attribution="SerpApi local result snippet",
                    is_snippet=True,
                    review_type="web_mention",
                )
            )

        limitations = [
            "Only search result snippets are retrieved — not full review text.",
            "Coverage limited to publicly indexed pages via SerpApi Google Search.",
            "Snippets may not reflect the most recent reviews.",
            "Results are attributed to the SerpApi Google Search API.",
        ]

        if not reviews:
            return RetrievalResult(
                source=self.name,
                limitations=limitations
                + ["No review snippets found for the given restaurant and location."],
                success=False,
                error="No review snippets found.",
            )

        return RetrievalResult(
            reviews=reviews,
            source=self.name,
            source_url=SERPAPI_BASE_URL,
            limitations=limitations,
            success=True,
        )


# ──────────────────────────── Null Source (fallback) ─────────────────────────

class NullReviewSource(ReviewSource):
    """Used when no configured source is available."""

    name = "No source configured"

    def is_available(self) -> bool:
        return True

    def retrieve(self, restaurant_name: str, city: str,
                 website: Optional[str] = None) -> RetrievalResult:
        return RetrievalResult(
            source=self.name,
            limitations=[
                "No review retrieval source is configured. "
                "Upload a reviews.csv file, or set SEARCH_API_KEY in your .env to enable "
                "SerpApi web retrieval. SEARCH_ENGINE_ID is also required for the "
                "Google Custom Search fallback."
            ],
            success=False,
            error="No source configured.",
        )


# ──────────────────────────── Retrieval Manager ──────────────────────────────

REGISTERED_SOURCES: list[ReviewSource] = [
    SerpApiSource(),             # primary: SerpApi Google Search (SEARCH_API_KEY only)
    GoogleCustomSearchSource(),  # secondary: Google Custom Search (SEARCH_API_KEY + SEARCH_ENGINE_ID)
    NullReviewSource(),          # always last as final fallback
]


# In-memory cache for review retrieval to prevent duplicate API requests and respect rate limits
_REVIEW_CACHE: dict[str, tuple[float, RetrievalResult]] = {}
_REVIEW_CACHE_TTL = 3600  # 1 hour cache duration


def clear_review_cache() -> None:
    """Clear the in-memory review retrieval cache."""
    _REVIEW_CACHE.clear()


def retrieve_reviews(
    restaurant_name: str,
    city: str,
    website: Optional[str] = None,
    force_refresh: bool = False,
) -> RetrievalResult:
    """
    Try each registered source in order until one succeeds or all are exhausted.
    Never fabricates review content.
    Caches successful and unsuccessful results to avoid redundant API hits.
    """
    clean_name = (restaurant_name or "").strip()
    clean_city = (city or "").strip()
    cache_key = f"{clean_name.lower()}|{clean_city.lower()}|{(website or '').strip().lower()}"
    now = time.time()

    if not force_refresh and cache_key in _REVIEW_CACHE:
        cached_time, cached_result = _REVIEW_CACHE[cache_key]
        if now - cached_time < _REVIEW_CACHE_TTL:
            logger.info("Returning cached review retrieval result for '%s, %s'", clean_name, clean_city)
            return cached_result

    for source in REGISTERED_SOURCES:
        if source.is_available():
            logger.info("Attempting review retrieval via %s", source.name)
            result = source.retrieve(clean_name, clean_city, website)
            if result.success and result.reviews:
                logger.info(
                    "Retrieved %d reviews from %s", len(result.reviews), source.name
                )
                _REVIEW_CACHE[cache_key] = (now, result)
                return result
            # Log why this source failed and try next
            logger.warning(
                "Source '%s' returned no reviews: %s",
                source.name,
                result.error or "No reviews found",
            )

    failure_result = RetrievalResult(
        source="None",
        limitations=["All configured review sources failed or returned no results."],
        success=False,
        error="No reviews retrieved from any source.",
    )
    # Cache negative result for 60 seconds to debounce rapid double-clicks
    _REVIEW_CACHE[cache_key] = (now, failure_result)
    return failure_result


# In-memory cache for autocomplete queries to debounce and prevent redundant API hits
_AUTOCOMPLETE_CACHE: dict[str, tuple[float, list[str]]] = {}
_AUTOCOMPLETE_CACHE_TTL = 300  # 5 minutes


def autocomplete_restaurant_name(
    query: str,
    city: Optional[str] = None,
    limit: int = 6,
) -> list[str]:
    """
    Search restaurant name suggestions using SerpApi Google Autocomplete
    and existing database records.
    - Debounces / caches requests
    - Gracefully falls back to existing restaurants in database
    - Never fabricates fake suggestions
    """
    q = (query or "").strip()
    if len(q) < 2:
        return []

    cache_key = f"{q.lower()}|{(city or '').lower()}"
    now = time.time()
    if cache_key in _AUTOCOMPLETE_CACHE:
        cached_time, cached_res = _AUTOCOMPLETE_CACHE[cache_key]
        if now - cached_time < _AUTOCOMPLETE_CACHE_TTL:
            return cached_res[:limit]

    results: list[str] = []
    seen: set[str] = set()

    # 1. First check existing restaurants in database
    try:
        from database.repository import search_restaurants
        db_matches = search_restaurants(q, limit=limit)
        for r in db_matches:
            name = r.get("name", "").strip()
            if name and name.lower() not in seen:
                seen.add(name.lower())
                results.append(name)
    except Exception as exc:
        logger.debug("Database restaurant search failed: %s", exc)

    # 2. Check SerpApi Google Autocomplete if key is available
    if SEARCH_API_KEY:
        try:
            search_query = f"{q} restaurant {city}".strip() if city else f"{q} restaurant"
            resp = requests.get(
                SERPAPI_BASE_URL,
                params={
                    "engine": "google_autocomplete",
                    "q": search_query,
                    "api_key": SEARCH_API_KEY,
                    "hl": "en",
                    "gl": "in",
                },
                timeout=REVIEW_RETRIEVAL_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("suggestions", []):
                    val = item.get("value", "").strip()
                    # Clean up trailing words like 'restaurant', 'menu', 'near me'
                    val_clean = re.sub(
                        r"(?i)\s+(restaurant|menu|reviews?|near me|locations?|photos?|online order)$",
                        "",
                        val,
                    ).strip()
                    if val_clean and len(val_clean) >= 2 and val_clean.lower() not in seen:
                        if q.lower() in val_clean.lower():
                            seen.add(val_clean.lower())
                            results.append(val_clean.title())
        except Exception as exc:
            logger.debug("SerpApi autocomplete failed: %s", exc)

    _AUTOCOMPLETE_CACHE[cache_key] = (now, results)
    return results[:limit]
