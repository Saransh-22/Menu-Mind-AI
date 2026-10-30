"""
Customer reviews, sentiment analysis, item insights, and SerpApi retrieval endpoints.
"""
from __future__ import annotations

import logging
from dataclasses import asdict
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_verified_run, get_verified_restaurant, get_run_datasets
from api.schemas import (
    SentimentSummary,
    ItemReviewInsight,
    ReviewTrendRecord,
)
from database import repository as repo
from services.sentiment_service import (
    analyze_sentiment_local,
    extract_item_review_insights,
    extract_review_trends,
)
from services.review_retrieval_service import retrieve_reviews
from services.preprocessing_service import clean_reviews
from services.dataset_storage import save_run_dataset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["Reviews & Sentiment"])


@router.get("/{run_id}/reviews/sentiment", response_model=SentimentSummary)
def get_sentiment_summary(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch customer review sentiment distribution, 5-star ratings, and themes."""
    datasets = get_run_datasets(run_id)
    reviews_df = datasets.get("reviews")
    if reviews_df is None or reviews_df.empty:
        return SentimentSummary(
            limitations=["No reviews loaded. Upload reviews or fetch external web reviews."]
        )
    return analyze_sentiment_local(reviews_df)


@router.get("/{run_id}/reviews/items", response_model=list[ItemReviewInsight])
def get_item_review_insights(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch item-specific customer review mentions, sentiment, and quotes."""
    datasets = get_run_datasets(run_id)
    reviews_df = datasets.get("reviews")
    menu_df = datasets.get("menu")

    if reviews_df is None or reviews_df.empty:
        return []

    insights = extract_item_review_insights(reviews_df, menu_df)
    return [ItemReviewInsight(**item) for item in insights]


@router.get("/{run_id}/reviews/trends", response_model=list[ReviewTrendRecord])
def get_review_trends(run_id: int, run: dict = Depends(get_verified_run)):
    """Fetch historical monthly review volume and rating trends."""
    datasets = get_run_datasets(run_id)
    reviews_df = datasets.get("reviews")
    if reviews_df is None or reviews_df.empty:
        return []

    trend_df = extract_review_trends(reviews_df)
    if trend_df.empty:
        return []

    records = trend_df.where(pd.notna(trend_df), None).to_dict(orient="records")
    return [ReviewTrendRecord(**r) for r in records]


@router.post("/{run_id}/reviews/fetch-web")
def fetch_external_reviews(
    run_id: int,
    run: dict = Depends(get_verified_run),
):
    """
    Retrieve organic search snippets via SerpApi (with Google Custom Search fallback).
    Saves retrieved reviews to the run's dataset storage and logs provenance metadata.
    """
    restaurant = repo.get_restaurant(run["restaurant_id"])
    if not restaurant:
        raise HTTPException(status_code=404, detail="Associated restaurant not found")

    name = restaurant["name"]
    city = restaurant.get("city") or ""
    website = restaurant.get("website")

    retrieval = retrieve_reviews(restaurant_name=name, city=city, website=website, force_refresh=True)

    if not retrieval.reviews:
        return {
            "success": False,
            "reviews_retrieved": 0,
            "source": retrieval.source,
            "error": retrieval.error,
            "limitations": retrieval.limitations,
        }

    # Convert retrieved reviews into DataFrame
    rows = []
    for r in retrieval.reviews:
        rows.append({
            "review_text": r.review_text,
            "rating": r.rating,
            "review_date": r.review_date,
            "source": r.source,
            "source_url": r.source_url,
            "item_name": r.item_name,
            "attribution": r.attribution,
            "is_snippet": r.is_snippet,
            "review_type": r.review_type,
        })
    new_reviews_df = pd.DataFrame(rows)

    # Merge with existing reviews if present
    datasets = get_run_datasets(run_id)
    existing_df = datasets.get("reviews")
    if existing_df is not None and not existing_df.empty:
        combined_df = pd.concat([existing_df, new_reviews_df], ignore_index=True)
    else:
        combined_df = new_reviews_df

    cleaned_df, report = clean_reviews(combined_df)
    save_run_dataset(run_id, "reviews", cleaned_df)

    # Log in SQLite retrieval_metadata
    repo.save_retrieval_metadata(
        run_id=run_id,
        source=retrieval.source,
        source_url=retrieval.source_url,
        review_count=len(retrieval.reviews),
        attribution=retrieval.reviews[0].attribution if retrieval.reviews else "",
        limitations="; ".join(retrieval.limitations),
    )

    return {
        "success": True,
        "reviews_retrieved": len(retrieval.reviews),
        "total_reviews": len(cleaned_df),
        "source": retrieval.source,
        "attribution": retrieval.reviews[0].attribution if retrieval.reviews else "",
        "limitations": retrieval.limitations,
    }
