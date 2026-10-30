"""
Food-waste image recognition and deterministic waste-cost analytics.
Images provide candidate identification only; quantities must be verified by a user.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import pandas as pd

from config.settings import GEMINI_API_KEY, GEMINI_MODEL


def analyze_food_image(image_bytes: bytes, mime_type: str) -> dict:
    """Identify visible food/ingredients using Gemini Vision; never infer exact weight."""
    if not image_bytes:
        raise ValueError("Uploaded image is empty.")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("Only JPEG, PNG and WEBP images are supported.")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise ValueError("Image must be 10 MB or smaller.")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = """
You are assisting a restaurant with kitchen food-waste logging.
Inspect the image and return ONLY valid JSON with this schema:
{
  "items": [
    {
      "name": "visible food or ingredient",
      "state": "raw|cooked|prepared|unclear",
      "confidence": 0.0,
      "visual_notes": "brief visible evidence"
    }
  ],
  "image_limitations": ["what cannot be determined from this image"]
}
Identify only visible items. Do not infer exact weight, freshness, food safety,
discard status, cost, or whether food is safe to reuse. Use confidence 0-1.
If no food is clearly visible, return an empty items list.
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    raw = (response.text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I)
    parsed = json.loads(raw)
    items = parsed.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Vision response did not contain a valid items list.")
    cleaned = []
    for item in items:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0.0
        cleaned.append({
            "name": str(item["name"])[:120],
            "state": str(item.get("state", "unclear"))[:40],
            "confidence": confidence,
            "visual_notes": str(item.get("visual_notes", ""))[:500],
        })
    return {
        "items": cleaned,
        "image_limitations": parsed.get("image_limitations", [
            "Image analysis cannot determine actual discarded quantity or food safety."
        ]),
        "model": GEMINI_MODEL,
    }


def calculate_waste_cost(records: list[dict]) -> dict:
    """Calculate cost only for rows with verified quantity and unit cost."""
    total_cost = 0.0
    calculable = 0
    uncalculable = 0
    by_ingredient: dict[str, float] = {}
    for row in records:
        try:
            quantity = float(row.get("quantity"))
            unit_cost = float(row.get("unit_cost"))
            if quantity < 0 or unit_cost < 0:
                raise ValueError
        except (TypeError, ValueError):
            uncalculable += 1
            continue
        cost = quantity * unit_cost
        total_cost += cost
        calculable += 1
        name = str(row.get("ingredient_name") or "Unknown")
        by_ingredient[name] = by_ingredient.get(name, 0.0) + cost
    return {
        "total_waste_cost": round(total_cost, 2),
        "calculable_records": calculable,
        "uncalculable_records": uncalculable,
        "by_ingredient": {
            key: round(value, 2)
            for key, value in sorted(by_ingredient.items(), key=lambda x: x[1], reverse=True)
        },
        "limitations": (
            ["Some records lack a valid quantity or unit cost and were excluded."]
            if uncalculable else []
        ),
    }


def analyze_spoilage_risk(
    sales_df: pd.DataFrame,
    menu_df: Optional[pd.DataFrame] = None,
    costs_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Calculate predictive spoilage exposure and demand velocity risks using real sales data.
    Never fabricates inventory data. Clearly distinguishes predicted spoilage risks from
    measured kitchen waste.
    """
    if sales_df is None or sales_df.empty:
        return {
            "slow_moving_items": [],
            "median_velocity": 0.0,
            "total_weekly_exposure": 0.0,
            "high_risk_count": 0,
            "action_items": [],
            "limitations": ["No sales data available to calculate spoilage risk."],
        }

    df = sales_df.copy()
    if "quantity_sold" not in df.columns:
        return {
            "slow_moving_items": [],
            "median_velocity": 0.0,
            "total_weekly_exposure": 0.0,
            "high_risk_count": 0,
            "action_items": [],
            "limitations": ["Sales dataset lacks 'quantity_sold' column."],
        }

    # Group by item name or item id
    name_col = "_matched_menu_name" if "_matched_menu_name" in df.columns else (
        "item_name" if "item_name" in df.columns else "item_id"
    )

    agg_dict = {"total_qty": ("quantity_sold", "sum")}
    if "date" in df.columns and pd.to_datetime(df["date"], errors="coerce").notna().any():
        agg_dict["active_days"] = ("date", "nunique")
    else:
        agg_dict["active_days"] = ("quantity_sold", "count")

    grouped = df.groupby(name_col).agg(**agg_dict).reset_index()
    grouped.columns = ["item_name", "units_sold", "active_days"]
    grouped["active_days"] = grouped["active_days"].clip(lower=1)
    grouped["daily_velocity"] = (grouped["units_sold"] / grouped["active_days"]).round(2)

    # Build cost lookup from costs_df or menu_df
    cost_lookup: dict[str, float] = {}
    if costs_df is not None and not costs_df.empty:
        if "item_name" in costs_df.columns and "ingredient_cost" in costs_df.columns:
            for _, r in costs_df.iterrows():
                try:
                    c = float(r["ingredient_cost"])
                    cost_lookup[str(r["item_name"]).strip().lower()] = c
                except (ValueError, TypeError):
                    pass
        elif "item_id" in costs_df.columns and "ingredient_cost" in costs_df.columns:
            for _, r in costs_df.iterrows():
                try:
                    c = float(r["ingredient_cost"])
                    cost_lookup[str(r["item_id"]).strip().lower()] = c
                except (ValueError, TypeError):
                    pass

    # Threshold for slow-moving: velocity <= max(0.8, median * 0.4) or units <= 5
    median_vel = float(grouped["daily_velocity"].median()) if not grouped.empty else 0.0
    vel_threshold = max(0.8, median_vel * 0.4)

    slow_items: list[dict] = []
    total_weekly_exposure = 0.0

    for _, row in grouped.iterrows():
        it_name = str(row["item_name"]).strip()
        u_sold = int(row["units_sold"])
        vel = float(row["daily_velocity"])

        is_slow = vel <= vel_threshold or u_sold <= 5

        unit_cost = cost_lookup.get(it_name.lower())
        cost_estimated = False
        if unit_cost is None:
            unit_cost = 25.0
            cost_estimated = True

        weekly_exposure = round(vel * unit_cost * 7.0, 2)
        risk_level = "High" if (vel <= vel_threshold * 0.6 or u_sold <= 3) else ("Medium" if is_slow else "Low")

        if is_slow:
            slow_items.append({
                "item_name": it_name,
                "units_sold": u_sold,
                "daily_velocity": vel,
                "unit_cost": round(unit_cost, 2),
                "cost_is_estimated": cost_estimated,
                "weekly_exposure": weekly_exposure,
                "risk_level": risk_level,
                "suggested_action": (
                    "Reduce daily prep batch by 40% and monitor 7-day demand."
                    if risk_level == "High"
                    else "Repurpose unsold ingredients into chef specials."
                ),
            })
            total_weekly_exposure += weekly_exposure

    slow_items.sort(key=lambda x: x["weekly_exposure"], reverse=True)

    action_items = [
        "Batch Size Optimization: Reduce daily morning prep quotas for high-risk dishes by 35%–50%.",
        "Ingredient Cross-Utilization: Pair ingredients from low-velocity recipes into high-volume dishes.",
        "Daily Flash Specials: Run lunch/dinner specials on dishes with declining demand to clear perishable stock.",
        "Menu Rationalization: Consider removing items with velocity < 0.5 units/day that account for under 1% of revenue.",
    ]

    limitations = [
        "Predictive spoilage risk is estimated from sales velocity and unit costs; it is not a direct inventory count.",
        "Measured kitchen waste is tracked separately in the Verified Waste Logs.",
    ]
    if any(i["cost_is_estimated"] for i in slow_items):
        limitations.append("Some ingredient costs were unmapped and used standard baseline estimates.")

    return {
        "slow_moving_items": slow_items,
        "median_velocity": round(median_vel, 2),
        "total_weekly_exposure": round(total_weekly_exposure, 2),
        "high_risk_count": sum(1 for i in slow_items if i["risk_level"] == "High"),
        "action_items": action_items,
        "limitations": limitations,
    }

