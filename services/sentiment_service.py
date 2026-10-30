"""
Sentiment analysis service.
Uses Gemini for nuanced interpretation; Python for all counts and deterministic analytics.
Clearly distinguishes verified customer reviews from search snippets and external web mentions.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import pandas as pd

from agent.schemas import SentimentSummary, ReviewTheme

logger = logging.getLogger(__name__)

# Sentiment lexicons for fallback text analysis when rating is missing
_POSITIVE_WORDS = frozenset({
    "delicious", "crispy", "fresh", "authentic", "generous", "amazing", "friendly",
    "great", "loved", "love", "excellent", "quick", "perfect", "clean", "tasty",
    "tender", "juicy", "wonderful", "best", "good", "superb", "highlight", "cozy",
    "satisfying", "rich", "creamy", "flavourful", "flavorful", "hospitable", "warm",
    "yum", "yummy", "enjoyed", "recommend", "recommended", "stellar", "nice", "top-notch"
})

_NEGATIVE_WORDS = frozenset({
    "salty", "soggy", "greasy", "cold", "undercooked", "overcooked", "slow", "rude",
    "overpriced", "disappointed", "disappointing", "stale", "bad", "terrible", "poor",
    "inconsistent", "dirty", "horrible", "small", "oily", "worst", "bland", "dry",
    "tough", "awful", "unwelcoming", "ignored", "burnt", "tasteless", "mediocre",
    "delayed", "long wait", "pricey", "expensive"
})

_THEME_RULES = [
    # Positive themes
    ("Crispy & Fresh Texture", "positive", re.compile(r"\b(crispy|fresh|crisp|freshly)\b", re.I)),
    ("Authentic & Delicious Flavor", "positive", re.compile(r"\b(authentic|delicious|tasty|flavor|flavour|yummy|rich|creamy)\b", re.I)),
    ("Friendly & Attentive Staff", "positive", re.compile(r"\b(friendly|staff|hospitality|courteous|polite|attentive|warm)\b", re.I)),
    ("Generous Portions & Value", "positive", re.compile(r"\b(generous|portion|filling|huge|large portion|good value)\b", re.I)),
    ("Quick & Prompt Service", "positive", re.compile(r"\b(fast|quick|prompt|speedy|on time)\b", re.I)),
    ("Cozy Ambience & Atmosphere", "positive", re.compile(r"\b(atmosphere|ambience|ambiance|cozy|vibe|decor|lovely)\b", re.I)),
    # Negative themes (Complaints)
    ("Over-Seasoned / Salty", "negative", re.compile(r"\b(salty|too salty|oversalted|seasoning)\b", re.I)),
    ("Greasy / Oily Texture", "negative", re.compile(r"\b(greasy|oily|too much oil|heavy)\b", re.I)),
    ("Soggy or Inconsistent Preparation", "negative", re.compile(r"\b(soggy|undercooked|overcooked|cold|inconsistent|raw)\b", re.I)),
    ("Slow Service / Long Wait", "negative", re.compile(r"\b(slow|waiting|waited|delayed|long wait)\b", re.I)),
    ("Small Portions / High Price", "negative", re.compile(r"\b(overpriced|expensive|small portion|tiny|not worth|pricey)\b", re.I)),
    ("Service or Staff Complaints", "negative", re.compile(r"\b(rude|unprofessional|ignored|poor service|careless)\b", re.I)),
]


def _score_text_sentiment(text: str) -> str:
    """Return 'positive', 'negative', or 'neutral' based on keyword matches."""
    tokens = re.findall(r"\b[a-z\-]+\b", (text or "").lower())
    pos_count = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg_count = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    if pos_count > neg_count:
        return "positive"
    if neg_count > pos_count:
        return "negative"
    return "neutral"


def _extract_quote(text: str, pattern: re.Pattern, max_len: int = 120) -> Optional[str]:
    """Find a clean, verbatim sentence or phrase from the review text containing the keyword."""
    if not text:
        return None
    sentences = re.split(r"[.!?\n]+", text)
    for s in sentences:
        s_clean = s.strip()
        if s_clean and pattern.search(s_clean):
            if len(s_clean) > max_len:
                match = pattern.search(s_clean)
                if match:
                    start = max(0, match.start() - 30)
                    end = min(len(s_clean), match.end() + 60)
                    return ("…" if start > 0 else "") + s_clean[start:end].strip() + ("…" if end < len(s_clean) else "")
            return s_clean
    return None


def analyze_sentiment_local(reviews_df: pd.DataFrame,
                             item_name: Optional[str] = None) -> SentimentSummary:
    """
    Deterministic rule-based sentiment calculation and theme extraction.
    Clearly distinguishes verified customer reviews from external search snippets.
    Never fabricates quotes or ratings.
    """
    if reviews_df is None or reviews_df.empty:
        return SentimentSummary(
            item_name=item_name,
            limitations=["No review data available."]
        )

    df = reviews_df.copy()
    if item_name and "item_name" in df.columns:
        df = df[df["item_name"].str.lower().str.contains(item_name.lower(), na=False)]

    if df.empty:
        return SentimentSummary(
            item_name=item_name,
            limitations=[f"No reviews found matching item '{item_name}'."]
        )

    # 1. Distinguish verified customer reviews vs search snippets
    if "is_snippet" in df.columns:
        is_snippet_mask = df["is_snippet"].astype(bool)
    elif "attribution" in df.columns:
        is_snippet_mask = df["attribution"].str.contains("snippet", case=False, na=False)
    elif "source" in df.columns:
        snippet_sources = {"SerpApi Google Search", "Google Custom Search API"}
        is_snippet_mask = df["source"].isin(snippet_sources)
    else:
        is_snippet_mask = pd.Series([False] * len(df), index=df.index)

    verified_df = df[~is_snippet_mask]
    snippet_df = df[is_snippet_mask]
    verified_count = len(verified_df)
    snippet_count = len(snippet_df)

    # 2. Ratings calculations
    avg_rating: Optional[float] = None
    verified_avg: Optional[float] = None
    snippet_avg: Optional[float] = None
    rating_distribution: dict[str, int] = {"1⭐": 0, "2⭐": 0, "3⭐": 0, "4⭐": 0, "5⭐": 0}

    if "rating" in df.columns:
        ratings = pd.to_numeric(df["rating"], errors="coerce")
        valid_ratings = ratings.dropna()
        if not valid_ratings.empty:
            avg_rating = round(float(valid_ratings.mean()), 2)
            # 5-star distribution
            for r in valid_ratings:
                val = round(float(r))
                if 1 <= val <= 5:
                    rating_distribution[f"{val}⭐"] += 1

        if not verified_df.empty and "rating" in verified_df.columns:
            v_ratings = pd.to_numeric(verified_df["rating"], errors="coerce").dropna()
            if not v_ratings.empty:
                verified_avg = round(float(v_ratings.mean()), 2)

        if not snippet_df.empty and "rating" in snippet_df.columns:
            s_ratings = pd.to_numeric(snippet_df["rating"], errors="coerce").dropna()
            if not s_ratings.empty:
                snippet_avg = round(float(s_ratings.mean()), 2)

    # 3. Sentiment classification per review
    pos = neg = neu = 0
    has_ratings = "rating" in df.columns and pd.to_numeric(df["rating"], errors="coerce").notna().any()

    for _, row in df.iterrows():
        r_val = None
        if "rating" in row and pd.notna(row["rating"]):
            try:
                r_val = float(row["rating"])
            except (ValueError, TypeError):
                r_val = None

        if r_val is not None:
            if r_val >= 3.8:
                pos += 1
            elif r_val <= 2.5:
                neg += 1
            else:
                neu += 1
        else:
            # Fallback to text scoring
            txt = str(row.get("review_text", ""))
            sentiment_tag = _score_text_sentiment(txt)
            if sentiment_tag == "positive":
                pos += 1
            elif sentiment_tag == "negative":
                neg += 1
            else:
                neu += 1

    n = len(df)
    pos_pct = round(pos / n * 100, 1) if n else 0.0
    neg_pct = round(neg / n * 100, 1) if n else 0.0
    neu_pct = round(100.0 - pos_pct - neg_pct, 1) if n else 0.0

    # 4. Extract verified themes, complaints, and appreciated features
    extracted_themes: list[ReviewTheme] = []
    complaints: list[dict] = []
    appreciated_features: list[dict] = []

    text_list = df["review_text"].dropna().astype(str).tolist() if "review_text" in df.columns else []
    for label, sent_type, pattern in _THEME_RULES:
        matches = [t for t in text_list if pattern.search(t)]
        if matches:
            freq = len(matches)
            quote = None
            for m in matches:
                q = _extract_quote(m, pattern)
                if q:
                    quote = q
                    break
            theme_obj = ReviewTheme(
                theme=label,
                sentiment=sent_type,
                frequency=freq,
                representative_quote=quote,
            )
            extracted_themes.append(theme_obj)
            theme_info = {
                "theme": label,
                "sentiment": sent_type,
                "frequency": freq,
                "representative_quote": quote,
            }
            if sent_type == "negative":
                complaints.append(theme_info)
            else:
                appreciated_features.append(theme_info)

    extracted_themes.sort(key=lambda t: t.frequency, reverse=True)
    complaints.sort(key=lambda x: x["frequency"], reverse=True)
    appreciated_features.sort(key=lambda x: x["frequency"], reverse=True)

    sources = []
    if "source" in df.columns:
        sources = df["source"].dropna().unique().tolist()

    limitations: list[str] = []
    if snippet_count > 0 and verified_count > 0:
        limitations.append(
            f"Dataset includes {verified_count} verified customer review(s) and {snippet_count} "
            "search snippet(s) retrieved via SerpApi. Snippets are short web excerpts and may have partial context."
        )
    elif snippet_count > 0 and verified_count == 0:
        limitations.append(
            f"All {snippet_count} reviews are external search snippets retrieved via SerpApi Google Search. "
            "No direct customer reviews were uploaded."
        )
    if not has_ratings:
        limitations.append("No numeric star ratings found; sentiment was estimated using natural language sentiment lexicons.")

    return SentimentSummary(
        item_name=item_name,
        positive_pct=pos_pct,
        negative_pct=neg_pct,
        neutral_pct=neu_pct,
        review_count=n,
        avg_rating=avg_rating,
        verified_count=verified_count,
        snippet_count=snippet_count,
        verified_avg_rating=verified_avg,
        snippet_avg_rating=snippet_avg,
        rating_distribution=rating_distribution,
        complaints=complaints,
        appreciated_features=appreciated_features,
        themes=extracted_themes[:6],
        source_coverage=sources,
        limitations=limitations,
    )


def extract_item_review_insights(
    reviews_df: pd.DataFrame,
    menu_df: Optional[pd.DataFrame] = None,
) -> list[dict]:
    """
    Compute item-level review statistics:
    mentions, average rating, positive/negative sentiment %,
    top complaint, top compliment, and source attribution.
    """
    if reviews_df is None or reviews_df.empty:
        return []

    df = reviews_df.copy()
    items_to_analyze: list[str] = []

    if "item_name" in df.columns:
        existing_items = df["item_name"].dropna().astype(str).str.strip()
        items_to_analyze = [i for i in existing_items.unique() if i and i.lower() != "nan" and len(i) > 1]

    # If menu_df is provided, also check for mentions in review_text
    if menu_df is not None and "item_name" in menu_df.columns:
        for m_name in menu_df["item_name"].dropna().astype(str).unique():
            if m_name and m_name not in items_to_analyze and len(m_name) > 2:
                items_to_analyze.append(m_name)

    results: list[dict] = []
    for item in items_to_analyze:
        mask = pd.Series([False] * len(df), index=df.index)
        if "item_name" in df.columns:
            mask = mask | df["item_name"].astype(str).str.lower().str.contains(re.escape(item.lower()), na=False)
        if "review_text" in df.columns:
            mask = mask | df["review_text"].astype(str).str.lower().str.contains(r"\b" + re.escape(item.lower()) + r"\b", na=False)

        sub_df = df[mask]
        if sub_df.empty:
            continue

        item_sentiment = analyze_sentiment_local(sub_df, item_name=item)
        top_complaint = item_sentiment.complaints[0]["theme"] if item_sentiment.complaints else None
        top_compliment = item_sentiment.appreciated_features[0]["theme"] if item_sentiment.appreciated_features else None

        results.append({
            "item_name": item,
            "mention_count": len(sub_df),
            "verified_count": item_sentiment.verified_count,
            "snippet_count": item_sentiment.snippet_count,
            "avg_rating": item_sentiment.avg_rating,
            "positive_pct": item_sentiment.positive_pct,
            "negative_pct": item_sentiment.negative_pct,
            "neutral_pct": item_sentiment.neutral_pct,
            "top_complaint": top_complaint,
            "top_compliment": top_compliment,
            "sample_reviews": (
                sub_df[[c for c in ("review_text", "rating", "source", "attribution") if c in sub_df.columns]]
                .head(3)
                .to_dict(orient="records")
                if "review_text" in sub_df.columns
                else []
            ),
        })

    results.sort(key=lambda x: x["mention_count"], reverse=True)
    return results


def extract_review_trends(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract time-series trend of review volume, average rating, and sentiment over time.
    """
    if reviews_df is None or reviews_df.empty or "review_date" not in reviews_df.columns:
        return pd.DataFrame()

    df = reviews_df.copy()
    df["_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    valid_dates = df.dropna(subset=["_date"])
    if valid_dates.empty:
        return pd.DataFrame()

    valid_dates["period"] = valid_dates["_date"].dt.to_period("M").astype(str)

    rows = []
    for period, group in valid_dates.groupby("period"):
        ratings = pd.to_numeric(group.get("rating"), errors="coerce").dropna()
        avg_r = round(float(ratings.mean()), 2) if not ratings.empty else None
        sent = analyze_sentiment_local(group)
        rows.append({
            "period": period,
            "total_reviews": len(group),
            "avg_rating": avg_r,
            "positive_pct": sent.positive_pct,
            "negative_pct": sent.negative_pct,
            "neutral_pct": sent.neutral_pct,
            "verified_count": sent.verified_count,
            "snippet_count": sent.snippet_count,
        })

    trend_df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True)
    return trend_df


def parse_gemini_sentiment(raw_text: str, item_name: Optional[str] = None) -> SentimentSummary:
    """Parse structured JSON returned by Gemini sentiment analysis tool."""
    try:
        data = json.loads(raw_text)
        themes = [
            ReviewTheme(
                theme=t.get("theme", ""),
                sentiment=t.get("sentiment", "neutral"),
                frequency=t.get("frequency", 1),
                representative_quote=t.get("representative_quote"),
            )
            for t in data.get("themes", [])
        ]
        return SentimentSummary(
            item_name=item_name or data.get("item_name"),
            positive_pct=data.get("positive_pct", 0.0),
            negative_pct=data.get("negative_pct", 0.0),
            neutral_pct=data.get("neutral_pct", 0.0),
            review_count=data.get("review_count", 0),
            avg_rating=data.get("avg_rating"),
            themes=themes,
            source_coverage=data.get("source_coverage", []),
            limitations=data.get("limitations", []),
        )
    except Exception as e:
        logger.warning("Failed to parse Gemini sentiment JSON: %s", e)
        return SentimentSummary(
            item_name=item_name,
            limitations=[f"Could not parse sentiment response: {e}"],
        )


def build_sentiment_prompt(reviews_df: pd.DataFrame, item_name: Optional[str] = None,
                            max_reviews: int = 40) -> str:
    """Build the LLM prompt for sentiment analysis."""
    df = reviews_df.copy()
    if item_name and "item_name" in df.columns:
        df = df[df["item_name"].str.lower().str.contains(item_name.lower(), na=False)]

    # Cap to avoid token overflow
    if len(df) > max_reviews:
        df = df.sample(max_reviews, random_state=42)

    review_texts = []
    for _, row in df.iterrows():
        txt = str(row.get("review_text", "")).strip()
        rating = row.get("rating", "")
        if txt:
            review_texts.append(f"[Rating: {rating}] {txt}")

    reviews_block = "\n".join(review_texts) or "No review text available."
    item_clause = f" about the menu item '{item_name}'" if item_name else ""

    return f"""You are a restaurant analytics assistant. Analyse the following customer reviews{item_clause}.

REVIEWS:
{reviews_block}

Return ONLY valid JSON in this exact format (no markdown):
{{
  "item_name": "{item_name or 'overall'}",
  "positive_pct": <number 0-100>,
  "negative_pct": <number 0-100>,
  "neutral_pct": <number 0-100>,
  "review_count": {len(df)},
  "avg_rating": <number or null>,
  "themes": [
    {{
      "theme": "<concise theme label>",
      "sentiment": "<positive|negative|neutral>",
      "frequency": <integer>,
      "representative_quote": "<verbatim short quote from above text, or null>"
    }}
  ],
  "source_coverage": [],
  "limitations": ["<any important caveats>"]
}}

Rules:
- positive_pct + negative_pct + neutral_pct must equal 100.
- Only use exact quotes from the review text provided. Never fabricate quotes.
- Identify at most 6 themes.
- If fewer than 3 reviews exist, note insufficient sample in limitations."""
