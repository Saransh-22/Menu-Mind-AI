"""
Idempotent Demo Data Seeding Script for MenuMind AI.
Populates four distinct restaurant profiles:
1. Chiku Da Dhaba (North Indian Casual Dining, Bengaluru)
2. Urban Brew Cafe (Artisan Cafe & Bakery, Mumbai)
3. Napoli Kitchen (Fine Casual Italian, New Delhi)
4. Green Bowl Kitchen (Healthy Salads & Bowls, Hyderabad)

Uses existing ingestion, preprocessing, and dataset_storage services.
Guaranteed idempotent: safe to run multiple times without duplicating restaurants or runs.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from database import repository as repo
from services.ingestion_service import (
    ingest_menu,
    ingest_sales,
    ingest_reviews,
    ingest_costs,
)
from services.preprocessing_service import (
    clean_menu,
    clean_sales,
    clean_reviews,
    clean_costs,
)
from services.dataset_storage import (
    save_run_dataset,
    save_run_quality_report,
    load_run_dataset,
)
from services.analytics_service import analyze_sales, calculate_profitability, impute_revenue, impute_category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_data")

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "data" / "seed"

DEMO_PROFILES = [
    {
        "name": "Chiku Da Dhaba",
        "city": "Bengaluru",
        "category": "North Indian",
        "folder": "chiku_da_dhaba",
        "period_start": "2026-09-01",
        "period_end": "2026-09-30",
        "waste": [
            {"ingredient_name": "Paneer Trim", "quantity": 2.5, "unit": "kg", "unit_cost": 85.0, "waste_reason": "prep_trim", "associated_dish": "Paneer Tikka Angara"},
            {"ingredient_name": "Tandoori Chicken Marinade", "quantity": 1.8, "unit": "kg", "unit_cost": 110.0, "waste_reason": "spoilage", "associated_dish": "Butter Chicken Deluxe"},
        ]
    },
    {
        "name": "Urban Brew Cafe",
        "city": "Mumbai",
        "category": "Cafe & Bakery",
        "folder": "urban_brew_cafe",
        "period_start": "2026-10-01",
        "period_end": "2026-10-28",
        "waste": [
            {"ingredient_name": "Almond Croissants (Day Old)", "quantity": 6.0, "unit": "units", "unit_cost": 52.0, "waste_reason": "spoilage", "associated_dish": "Almond Frangipane Croissant"},
            {"ingredient_name": "Oat Milk (Opened Expiry)", "quantity": 2.0, "unit": "liters", "unit_cost": 42.0, "waste_reason": "spoilage", "associated_dish": "Oat Milk Cortado"},
        ]
    },
    {
        "name": "Napoli Kitchen",
        "city": "New Delhi",
        "category": "Italian Dining",
        "folder": "napoli_kitchen",
        "period_start": "2026-08-01",
        "period_end": "2026-08-31",
        "waste": [
            {"ingredient_name": "Buffalo Mozzarella D.O.P.", "quantity": 1.2, "unit": "kg", "unit_cost": 145.0, "waste_reason": "spoilage", "associated_dish": "Margherita D.O.P."},
            {"ingredient_name": "Fresh Calamari Trimmings", "quantity": 0.8, "unit": "kg", "unit_cost": 155.0, "waste_reason": "prep_trim", "associated_dish": "Calamari Fritti"},
        ]
    },
    {
        "name": "Green Bowl Kitchen",
        "city": "Hyderabad",
        "category": "Healthy Bowls",
        "folder": "green_bowl_kitchen",
        "period_start": "2026-10-10",
        "period_end": "2026-10-25",
        "waste": [
            {"ingredient_name": "Curly Kale Leaves (Wilted)", "quantity": 3.0, "unit": "kg", "unit_cost": 118.0, "waste_reason": "spoilage", "associated_dish": "Kale Tahini Caesar"},
            {"ingredient_name": "Prepped Tri-Color Quinoa", "quantity": 2.0, "unit": "kg", "unit_cost": 130.0, "waste_reason": "spoilage", "associated_dish": "Quinoa Harvest Power Bowl"},
        ]
    },
]


def seed_restaurant_data():
    """Main seeding routine."""
    logger.info("Starting idempotent seeding of 4 demo restaurants...")

    for prof in DEMO_PROFILES:
        name = prof["name"]
        city = prof["city"]
        category = prof["category"]
        folder = SEED_DIR / prof["folder"]

        # 1. Get or create restaurant
        rest_id, created = repo.get_or_create_restaurant(
            name=name,
            city=city,
            location=f"Central {city}",
            website=f"https://www.{prof['folder'].replace('_', '')}.com",
            category=category,
        )
        logger.info("Restaurant '%s' in %s (ID: %s, newly_created: %s)", name, city, rest_id, created)

        # 2. Check for existing Demo Analysis Run
        runs = repo.list_runs_for_restaurant(rest_id)
        demo_run = next((r for r in runs if r.get("notes") == "Demo Analysis Run"), None)

        if not demo_run:
            run_id = repo.create_analysis_run(
                restaurant_id=rest_id,
                period_start=prof["period_start"],
                period_end=prof["period_end"],
                notes="Demo Analysis Run",
            )
            logger.info("  Created new analysis run #%s for '%s'", run_id, name)
        else:
            run_id = demo_run["id"]
            logger.info("  Reusing existing demo analysis run #%s for '%s'", run_id, name)

        # 3. Ingest and save datasets if CSVs exist
        menu_csv = folder / "menu.csv"
        sales_csv = folder / "sales.csv"
        reviews_csv = folder / "reviews.csv"
        costs_csv = folder / "costs.csv"

        scores = []

        # Menu
        if menu_csv.exists():
            df_raw, _, _ = ingest_menu(menu_csv.read_bytes(), "menu.csv")
            df_clean, report = clean_menu(df_raw)
            save_run_dataset(run_id, "menu", df_clean)
            save_run_quality_report(run_id, "menu", report)
            scores.append(report.quality_score)

        # Sales
        if sales_csv.exists():
            df_raw, _, _ = ingest_sales(sales_csv.read_bytes(), "sales.csv")
            menu_df = load_run_dataset(run_id, "menu")
            df_clean, report, _ = clean_sales(df_raw, menu_df)
            save_run_dataset(run_id, "sales", df_clean)
            save_run_quality_report(run_id, "sales", report)
            scores.append(report.quality_score)

        # Reviews
        if reviews_csv.exists():
            df_raw, _, _ = ingest_reviews(reviews_csv.read_bytes(), "reviews.csv")
            df_clean, report = clean_reviews(df_raw)
            save_run_dataset(run_id, "reviews", df_clean)
            save_run_quality_report(run_id, "reviews", report)
            scores.append(report.quality_score)

        # Costs
        if costs_csv.exists():
            df_raw, _, _ = ingest_costs(costs_csv.read_bytes(), "costs.csv")
            df_clean, report = clean_costs(df_raw)
            save_run_dataset(run_id, "costs", df_clean)
            save_run_quality_report(run_id, "costs", report)
            scores.append(report.quality_score)

        avg_score = sum(scores) / len(scores) if scores else 1.0
        repo.update_run_status(run_id, "completed", data_quality_score=avg_score)

        # 4. Seed initial recommendations if empty
        existing_recs = repo.list_recommendations(run_id)
        if not existing_recs:
            menu_df = load_run_dataset(run_id, "menu")
            sales_df = load_run_dataset(run_id, "sales")
            costs_df = load_run_dataset(run_id, "costs")

            if menu_df is not None and sales_df is not None:
                s_df = impute_revenue(sales_df, menu_df)
                s_df = impute_category(s_df, menu_df)
                summary = analyze_sales(s_df, menu_df)

                # Seed lead recommendation (PROMOTE)
                if summary.top_items:
                    lead = summary.top_items[0]
                    repo.save_recommendation(run_id, {
                        "item_name": lead.item_name,
                        "action": "PROMOTE",
                        "priority": "high",
                        "confidence_score": 0.88,
                        "reasoning": f"Anchor revenue driver generating ₹{lead.total_revenue:,.0f} with high sales velocity.",
                        "expected_benefits": "Increase customer capture rate and upsell attached beverages.",
                        "potential_risks": "Kitchen station bottleneck during dinner rush if volume spikes > 25%.",
                        "next_steps": ["Feature on prime menu real estate", "Train servers on beverage pairings"],
                        "sales_metrics": {"total_units": lead.total_quantity, "total_revenue": lead.total_revenue},
                    })

                # Seed underperformer recommendation (IMPROVE or REPRICE)
                if summary.weak_items:
                    weak = summary.weak_items[-1]
                    repo.save_recommendation(run_id, {
                        "item_name": weak.item_name,
                        "action": "IMPROVE",
                        "priority": "medium",
                        "confidence_score": 0.74,
                        "reasoning": f"Low volume ({weak.total_quantity} units). Customer reviews indicate pricing or recipe refinement needed.",
                        "expected_benefits": "Revitalize item sales velocity and reduce ingredient expiration risk.",
                        "potential_risks": "Minimal downside given current low sales contribution.",
                        "next_steps": ["Survey guests on flavor profile", "Test adjusted portion or bundle deal"],
                        "sales_metrics": {"total_units": weak.total_quantity, "total_revenue": weak.total_revenue},
                    })

                logger.info("  Seeded AI recommendations for '%s'", name)

        # 5. Seed initial waste records if empty
        existing_waste = repo.list_waste_records(run_id)
        if not existing_waste and prof.get("waste"):
            for w in prof["waste"]:
                repo.save_waste_record(run_id=run_id, data=w)
            logger.info("  Seeded %s physical waste records for '%s'", len(prof["waste"]), name)

    logger.info("Idempotent demo seeding completed successfully for all 4 profiles.")


if __name__ == "__main__":
    seed_restaurant_data()
