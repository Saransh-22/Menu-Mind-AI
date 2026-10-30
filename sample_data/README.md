# Sample Data for MenuMind AI

This directory contains realistic sample data for testing and demonstration.

## Files

| File | Contents |
|------|----------|
| `menu.csv` | 12 menu items across 5 categories (Pizza, Salad, Mains, Pasta, Dessert, Sides) |
| `sales.csv` | 30 sales transactions across Jan–Mar 2024 |
| `reviews.csv` | 15 customer reviews from an example review platform |
| `costs.csv` | Ingredient and packaging costs for all 12 items |

## How to Use

1. Start the application: `streamlit run app.py`
2. Go to **Overview** and create a new restaurant analysis run
3. Go to **Data Upload** and upload these four files
4. Run the AI analysis on the **AI Recommendations** page

## Notes

- All restaurant IDs use `REST001`
- All item IDs use `ITEM001`–`ITEM012`
- These are fictional example records — not real business data
- The sales data shows Margherita Pizza as the best seller with a growing trend
- Greek Salad and Bruschetta have lower/zero sales activity (good candidates for `INSUFFICIENT_EVIDENCE`)
- Caesar Salad has mixed reviews despite decent sales (good `IMPROVE` candidate)
