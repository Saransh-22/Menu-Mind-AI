# LeftOverAI Integration Notes

## What was integrated
- Added Food Waste Intelligence to the existing Streamlit navigation.
- Added Gemini Vision food-item identification using the existing GEMINI_API_KEY and GEMINI_MODEL configuration.
- Added verified waste-record entry (actual quantity, unit, unit cost, reason, associated dish).
- Added SQLite tables for waste records and image-analysis metadata.
- Added deterministic waste-cost calculation.
- Added an `analyze_food_waste` agent tool and included verified waste evidence in recommendation context.
- Added execution-history entries for tool invocations.
- Added tests for waste-cost calculations and persistence.

## Safety and data integrity
- Image recognition identifies candidate visible items only.
- It does not estimate actual weight, freshness, discard status, or food safety.
- Staff must verify the ingredient and enter the actual quantity.
- Waste cost is calculated as entered quantity multiplied by entered cost per unit.
- Uploaded image bytes are not persisted; only metadata and detections are stored.
- If Gemini is unavailable, users can still create waste records manually.

## Run
1. Create a virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
3. Run `streamlit run app.py`.
4. Create/select an analysis run.
5. Open Food Waste Intelligence, optionally analyze an image, then save verified waste records.
6. Open AI Recommendations and run analysis to include waste evidence.

## Verification performed
- Python compileall completed successfully.
- Existing + new pytest suite: 65 passed.
- Live Gemini image recognition was not exercised because no API key was supplied in this environment.
