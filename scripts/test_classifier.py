import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.multi_agent.classifier import IntentClassifier

classifier = IntentClassifier()

test_queries = [
    ("What is our best-selling dish?", "best_selling_items"),
    ("Which dish generates the highest profit?", "profitability_analysis"),
    ("Tell me recipe optimization for butter chicken", "recipe_optimization"),
    ("How can I make my butter chicken more profitable?", "recipe_optimization"),
    ("Create a new menu for my restaurant", "menu_creation"),
    ("Extract dishes from this menu image", "menu_image_extraction"),
    ("Why are customers unhappy with our biryani?", "customer_review_analysis"),
    ("Which dishes are wasting the most ingredients?", "food_waste_analysis"),
    ("Which items should I remove from my menu?", "menu_optimization"),
    ("Suggest a price for paneer tikka", "pricing_strategy"),
    ("Compare my restaurant's performance", "restaurant_comparison"),
    ("How can I reduce the cost of my gravies?", "food_cost_analysis"),
]

print("=== HEURISTIC CLASSIFIER TEST ===")
all_pass = True
for q, expected in test_queries:
    res = classifier._heuristic_classify(q, [])
    status = "PASS" if res.intent == expected else f"FAIL (got {res.intent})"
    if status != "PASS":
        all_pass = False
    print(f"{status:8} | Q: {q:50} | Intent: {res.intent:25} | Agent: {res.target_agent}")

history = [
    {"role": "user", "content": "What is our best-selling dish?"},
    {"role": "assistant", "content": "Dum Chicken Biryani is your top dish."}
]
followup = classifier._heuristic_classify("Can you optimize it?", history)
print("\nPronoun resolution test for 'Can you optimize it?':")
print(f"Intent: {followup.intent} | Target Agent: {followup.target_agent} | Entities: {followup.entities}")
assert followup.intent == "recipe_optimization", f"Expected recipe_optimization, got {followup.intent}"
assert followup.entities.get("dish_name") == "dum chicken biryani", f"Expected dum chicken biryani, got {followup.entities}"
print("\nALL CLASSIFICATION TESTS PASSED!")
