"""
Create realistic, statistically distinct multi-restaurant seed datasets in data/seed/.
Four distinct restaurant profiles:
1. Chiku Da Dhaba (North Indian Casual)
2. Urban Brew Cafe (Artisan Cafe & Bakery)
3. Napoli Kitchen (Fine Casual Italian)
4. Green Bowl Kitchen (Healthy Salads & Bowls)
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "data" / "seed"

# ── 1. Chiku Da Dhaba ────────────────────────────────────────────────────────
CHIKU_DIR = SEED_DIR / "chiku_da_dhaba"
CHIKU_DIR.mkdir(parents=True, exist_ok=True)

(CHIKU_DIR / "menu.csv").write_text("""item_id,item_name,category,description,price
CDD01,Paneer Tikka Angara,Starters,Charcoal grilled cottage cheese in fiery Kashmiri marinade,260
CDD02,Murgh Malai Tikka,Starters,Tender chicken skewers marinated in cardamom cream and cheese,340
CDD03,Crispy Corn Salt & Pepper,Starters,Golden fried corn tossed with scallions and crushed pepper,210
CDD04,Butter Chicken Deluxe,Mains,Tandoori chicken simmered in rich satin tomato and makhani gravy,380
CDD05,Paneer Butter Masala,Mains,Soft cottage cheese cubes in rich spiced onion-tomato gravy,290
CDD06,Dal Makhani Royal,Mains,Slow-simmered black lentils with churned butter and cream,250
CDD07,Dum Chicken Biryani,Rice & Breads,Aromatic basmati rice slow-cooked with spiced chicken and saffron,360
CDD08,Butter Garlic Naan,Rice & Breads,Clay oven leavened bread brushed with garlic butter,75
CDD09,Tandoori Roti,Rice & Breads,Whole wheat stone-ground flatbread baked in tandoor,35
CDD10,Gulab Jamun Flambé,Desserts,Warm milk dumplings soaked in saffron-rose syrup,120
CDD11,Royal Kulfi Falooda,Desserts,Traditional pistachio kulfi with vermicelli and rose essence,160
CDD12,Spiced Masala Chaas,Beverages,Churned yoghurt refresher with roasted cumin and mint,80
""", encoding="utf-8")

(CHIKU_DIR / "costs.csv").write_text("""item_id,item_name,ingredient_cost,packaging_cost
CDD01,Paneer Tikka Angara,85.00,10.00
CDD02,Murgh Malai Tikka,110.00,12.00
CDD03,Crispy Corn Salt & Pepper,45.00,8.00
CDD04,Butter Chicken Deluxe,135.00,15.00
CDD05,Paneer Butter Masala,92.00,12.00
CDD06,Dal Makhani Royal,58.00,10.00
CDD07,Dum Chicken Biryani,120.00,18.00
CDD08,Butter Garlic Naan,18.00,4.00
CDD09,Tandoori Roti,8.00,2.00
CDD10,Gulab Jamun Flambé,35.00,8.00
CDD11,Royal Kulfi Falooda,48.00,10.00
CDD12,Spiced Masala Chaas,20.00,5.00
""", encoding="utf-8")

(CHIKU_DIR / "sales.csv").write_text("""date,item_name,quantity,revenue
2026-09-01,Butter Chicken Deluxe,18,6840
2026-09-01,Dum Chicken Biryani,22,7920
2026-09-01,Paneer Tikka Angara,14,3640
2026-09-01,Butter Garlic Naan,45,3375
2026-09-01,Dal Makhani Royal,12,3000
2026-09-02,Butter Chicken Deluxe,20,7600
2026-09-02,Dum Chicken Biryani,25,9000
2026-09-02,Crispy Corn Salt & Pepper,16,3360
2026-09-02,Paneer Butter Masala,15,4350
2026-09-02,Butter Garlic Naan,50,3750
2026-09-03,Dum Chicken Biryani,28,10080
2026-09-03,Butter Chicken Deluxe,22,8360
2026-09-03,Murgh Malai Tikka,12,4080
2026-09-03,Gulab Jamun Flambé,15,1800
2026-09-03,Spiced Masala Chaas,30,2400
2026-09-04,Butter Chicken Deluxe,19,7220
2026-09-04,Dum Chicken Biryani,24,8640
2026-09-04,Paneer Tikka Angara,16,4160
2026-09-04,Dal Makhani Royal,14,3500
2026-09-04,Butter Garlic Naan,48,3600
2026-09-05,Dum Chicken Biryani,35,12600
2026-09-05,Butter Chicken Deluxe,30,11400
2026-09-05,Paneer Butter Masala,20,5800
2026-09-05,Murgh Malai Tikka,18,6120
2026-09-05,Royal Kulfi Falooda,22,3520
2026-09-05,Butter Garlic Naan,70,5250
2026-09-06,Dum Chicken Biryani,38,13680
2026-09-06,Butter Chicken Deluxe,32,12160
2026-09-06,Paneer Tikka Angara,24,6240
2026-09-06,Dal Makhani Royal,18,4500
2026-09-06,Butter Garlic Naan,75,5625
2026-09-06,Spiced Masala Chaas,40,3200
2026-09-07,Dum Chicken Biryani,20,7200
2026-09-07,Butter Chicken Deluxe,16,6080
2026-09-07,Crispy Corn Salt & Pepper,12,2520
2026-09-07,Butter Garlic Naan,38,2850
""", encoding="utf-8")

(CHIKU_DIR / "reviews.csv").write_text("""review_date,rating,review_text,item_name,source
2026-09-02,5,"The Butter Chicken Deluxe is the absolute best in town! Rich gravy and tender tandoori chicken.",Butter Chicken Deluxe,Google
2026-09-03,5,"Outstanding Dum Biryani! The aroma of saffron and spices was incredible.",Dum Chicken Biryani,Zomato
2026-09-03,4,"Paneer Tikka was smoky and fresh. Garlic naan was warm and crispy.",Paneer Tikka Angara,Google
2026-09-04,2,"Food is tasty but had to wait 45 minutes for a table on Friday evening. Slow service.",,Zomato
2026-09-05,5,"Dal Makhani Royal has that authentic slow-cooked flavor. Highly recommended!",Dal Makhani Royal,Google
2026-09-05,4,"Great dinner with family. Biryani portion is generous. Kulfi falooda was delicious.",Dum Chicken Biryani,Google
2026-09-06,3,"Butter Chicken was slightly sweeter than I prefer. Naan was great though.",Butter Chicken Deluxe,Zomato
2026-09-07,5,"Consistently good North Indian food. Spiced chaas is refreshing.",Spiced Masala Chaas,Google
""", encoding="utf-8")


# ── 2. Urban Brew Cafe ────────────────────────────────────────────────────────
CAFE_DIR = SEED_DIR / "urban_brew_cafe"
CAFE_DIR.mkdir(parents=True, exist_ok=True)

(CAFE_DIR / "menu.csv").write_text("""item_id,item_name,category,description,price
UBC01,Single Origin Espresso,Coffee & Brews,Double shot extracted from light-roast Ethiopian Yirgacheffe,140
UBC02,Vanilla Bean Cold Brew,Coffee & Brews,18-hour cold steeped coffee with natural Madagascar vanilla,190
UBC03,Oat Milk Cortado,Coffee & Brews,Equal parts espresso and warm steamed organic oat milk,175
UBC04,Iced Spanish Latte,Coffee & Brews,Chilled espresso with condensed milk and cinnamon dust,210
UBC05,Almond Frangipane Croissant,Bakery,Twice-baked flaky croissant filled with rich almond cream,180
UBC06,Pain au Chocolat,Bakery,French butter pastry layered with Valrhona dark chocolate batons,165
UBC07,Classic Sourdough Croissant,Bakery,Hand-laminated all-butter golden croissant,140
UBC08,Avocado & Poached Egg Toast,All-Day Brunch,Smashed Hass avocado and organic poached egg on toasted levain,280
UBC09,Truffle Mushroom Melt,All-Day Brunch,Wild sautéed mushrooms and gruyère cheese on sourdough,310
UBC10,Smoked Chicken Panini,Sandwiches,Herb roasted chicken with aged cheddar and basil emulsion,330
UBC11,Hummus & Roasted Veggie Wrap,Sandwiches,Sun-dried tomato tortilla with beetroot hummus and grilled peppers,260
UBC12,Basque Burnt Cheesecake,Desserts,Caramelized crust with velvety molten cream cheese center,240
UBC13,Dark Chocolate Sea Salt Cookie,Desserts,Chewy baked cookie with 70% cacao chunks and Maldon salt flakes,95
UBC14,Berry Hibiscus Iced Tea,Beverages,Sparkling floral infusion brewed with dried hibiscus and wild berries,160
""", encoding="utf-8")

(CAFE_DIR / "costs.csv").write_text("""item_id,item_name,ingredient_cost,packaging_cost
UBC01,Single Origin Espresso,28.00,4.00
UBC02,Vanilla Bean Cold Brew,36.00,8.00
UBC03,Oat Milk Cortado,42.00,6.00
UBC04,Iced Spanish Latte,48.00,8.00
UBC05,Almond Frangipane Croissant,52.00,6.00
UBC06,Pain au Chocolat,44.00,5.00
UBC07,Classic Sourdough Croissant,32.00,4.00
UBC08,Avocado & Poached Egg Toast,85.00,10.00
UBC09,Truffle Mushroom Melt,92.00,10.00
UBC10,Smoked Chicken Panini,98.00,12.00
UBC11,Hummus & Roasted Veggie Wrap,64.00,8.00
UBC12,Basque Burnt Cheesecake,68.00,8.00
UBC13,Dark Chocolate Sea Salt Cookie,24.00,3.00
UBC14,Berry Hibiscus Iced Tea,30.00,6.00
""", encoding="utf-8")

(CAFE_DIR / "sales.csv").write_text("""date,item_name,quantity,revenue
2026-10-01,Vanilla Bean Cold Brew,28,5320
2026-10-01,Almond Frangipane Croissant,22,3960
2026-10-01,Avocado & Poached Egg Toast,16,4480
2026-10-01,Single Origin Espresso,20,2800
2026-10-01,Dark Chocolate Sea Salt Cookie,30,2850
2026-10-02,Iced Spanish Latte,24,5040
2026-10-02,Vanilla Bean Cold Brew,26,4940
2026-10-02,Pain au Chocolat,18,2970
2026-10-02,Smoked Chicken Panini,14,4620
2026-10-03,Vanilla Bean Cold Brew,32,6080
2026-10-03,Avocado & Poached Egg Toast,25,7000
2026-10-03,Almond Frangipane Croissant,28,5040
2026-10-03,Basque Burnt Cheesecake,18,4320
2026-10-03,Truffle Mushroom Melt,12,3720
2026-10-04,Vanilla Bean Cold Brew,35,6650
2026-10-04,Avocado & Poached Egg Toast,28,7840
2026-10-04,Oat Milk Cortado,22,3850
2026-10-04,Smoked Chicken Panini,16,5280
2026-10-04,Dark Chocolate Sea Salt Cookie,35,3325
2026-10-05,Single Origin Espresso,24,3360
2026-10-05,Vanilla Bean Cold Brew,22,4180
2026-10-05,Classic Sourdough Croissant,16,2240
2026-10-05,Berry Hibiscus Iced Tea,18,2880
""", encoding="utf-8")

(CAFE_DIR / "reviews.csv").write_text("""review_date,rating,review_text,item_name,source
2026-10-01,5,"Best cold brew in Mumbai! Smooth, aromatic and not bitter at all.",Vanilla Bean Cold Brew,Google
2026-10-02,5,"The Almond Croissant is divine. Flaky perfection with generous frangipane.",Almond Frangipane Croissant,Zomato
2026-10-03,4,"Lovely aesthetic vibe and great coffee. Wi-Fi was dropping occasionally though.",Vanilla Bean Cold Brew,Google
2026-10-03,5,"Avocado toast on artisan sourdough with poached egg is the ultimate brunch.",Avocado & Poached Egg Toast,Instagram
2026-10-04,3,"Loved the Spanish latte but the cafe was packed and seating was cramped on Sunday morning.",Iced Spanish Latte,Google
2026-10-05,5,"Basque cheesecake is so creamy inside. Cookies are top tier.",Basque Burnt Cheesecake,Zomato
""", encoding="utf-8")


# ── 3. Napoli Kitchen ─────────────────────────────────────────────────────────
NAPOLI_DIR = SEED_DIR / "napoli_kitchen"
NAPOLI_DIR.mkdir(parents=True, exist_ok=True)

(NAPOLI_DIR / "menu.csv").write_text('''item_id,item_name,category,description,price
NK01,Burrata Pugliese,Antipasti,"Imported burrata heart with heirloom cherry tomatoes and basil oil",490
NK02,Bruschetta al Pomodoro,Antipasti,"Wood-toasted rustic bread with garlic rubbed San Marzano tomatoes",280
NK03,Calamari Fritti,Antipasti,"Crisp flash-fried baby squid with lemon caper aioli",460
NK04,Margherita D.O.P.,Woodfired Pizza,"San Marzano tomatoes, buffalo mozzarella, fresh basil, EVOO",540
NK05,Diavola Piccante,Woodfired Pizza,"Spicy Calabrian spianata salami, tomato sauce, mozzarella, chili",620
NK06,Quattro Formaggi,Woodfired Pizza,"Fior di latte, gorgonzola dolce, fontina, parmigiano reggiano",640
NK07,Truffle Tagliatelle,Pasta,"Handmade egg pasta ribbons in black truffle and aged parmesan reduction",680
NK08,Spaghetti alla Carbonara,Pasta,"Classic Roman preparation with cured guanciale, egg yolk, pecorino",590
NK09,Penne Arrabbiata,Pasta,"Bronze-die penne in fiery garlic and San Marzano tomato sauce",440
NK10,Tiramisu Tradizionale,Dolci,"Espresso-dipped savoiardi ladyfingers layered with whipped mascarpone",360
NK11,Panna Cotta al Limone,Dolci,"Silky vanilla bean cream infused with Sorrento lemon coulis",320
NK12,San Pellegrino Sparkling,Bevande,"Natural Italian sparkling mineral water with fresh lemon slice",180
''', encoding="utf-8")

(NAPOLI_DIR / "costs.csv").write_text("""item_id,item_name,ingredient_cost,packaging_cost
NK01,Burrata Pugliese,175.00,15.00
NK02,Bruschetta al Pomodoro,65.00,8.00
NK03,Calamari Fritti,155.00,12.00
NK04,Margherita D.O.P.,145.00,15.00
NK05,Diavola Piccante,185.00,18.00
NK06,Quattro Formaggi,195.00,18.00
NK07,Truffle Tagliatelle,210.00,18.00
NK08,Spaghetti alla Carbonara,165.00,15.00
NK09,Penne Arrabbiata,95.00,10.00
NK10,Tiramisu Tradizionale,105.00,12.00
NK11,Panna Cotta al Limone,85.00,10.00
NK12,San Pellegrino Sparkling,50.00,5.00
""", encoding="utf-8")

(NAPOLI_DIR / "sales.csv").write_text("""date,item_name,quantity,revenue
2026-08-01,Margherita D.O.P.,24,12960
2026-08-01,Truffle Tagliatelle,18,12240
2026-08-01,Diavola Piccante,16,9920
2026-08-01,Burrata Pugliese,14,6860
2026-08-01,Tiramisu Tradizionale,20,7200
2026-08-02,Margherita D.O.P.,28,15120
2026-08-02,Truffle Tagliatelle,22,14960
2026-08-02,Quattro Formaggi,15,9600
2026-08-02,Spaghetti alla Carbonara,16,9440
2026-08-02,Tiramisu Tradizionale,24,8640
2026-08-03,Margherita D.O.P.,18,9720
2026-08-03,Burrata Pugliese,12,5880
2026-08-03,Penne Arrabbiata,15,6600
2026-08-04,Truffle Tagliatelle,25,17000
2026-08-04,Margherita D.O.P.,30,16200
2026-08-04,Diavola Piccante,20,12400
2026-08-04,Calamari Fritti,16,7360
2026-08-04,Tiramisu Tradizionale,28,10080
2026-08-05,Margherita D.O.P.,32,17280
2026-08-05,Truffle Tagliatelle,26,17680
2026-08-05,Burrata Pugliese,18,8820
2026-08-05,Spaghetti alla Carbonara,20,11800
2026-08-05,San Pellegrino Sparkling,35,6300
""", encoding="utf-8")

(NAPOLI_DIR / "reviews.csv").write_text("""review_date,rating,review_text,item_name,source
2026-08-01,5,"Authentic Neapolitan crust! Leopard-spotted and light as air. Best pizza in South Delhi.",Margherita D.O.P.,Google
2026-08-02,5,"The Truffle Tagliatelle is mind-blowing. Rich truffle aroma without being overpowering.",Truffle Tagliatelle,TripAdvisor
2026-08-03,3,"Food is delicious but prices are quite steep for pasta portions. Table was not ready on arrival.",,Zomato
2026-08-04,5,"Burrata was so fresh, melted in the mouth. Classic Carbonara made properly without heavy cream.",Burrata Pugliese,Google
2026-08-05,4,"Tiramisu is textbook Italian perfection. Beautiful wine list and rustic Italian ambiance.",Tiramisu Tradizionale,Google
""", encoding="utf-8")


# ── 4. Green Bowl Kitchen ────────────────────────────────────────────────────
GREEN_DIR = SEED_DIR / "green_bowl_kitchen"
GREEN_DIR.mkdir(parents=True, exist_ok=True)

(GREEN_DIR / "menu.csv").write_text('''item_id,item_name,category,description,price
GB01,Quinoa Harvest Power Bowl,Warm Grain Bowls,"Tri-color quinoa, roasted butternut squash, kale, pumpkin seeds, tahini",340
GB02,Chipotle Black Bean Bowl,Warm Grain Bowls,"Brown rice, black beans, charred corn salsa, avocado, lime crema",310
GB03,Mediterranean Falafel Bowl,Warm Grain Bowls,"Herbed quinoa, baked falafel, cucumber, Kalamata olives, creamy hummus",320
GB04,Kale Tahini Caesar,Superfood Salads,"Massaged curly kale, crispy chickpea croutons, cashew parmesan, Caesar dressing",290
GB05,Roasted Beet & Goat Cheese,Superfood Salads,"Organic baby spinach, slow roasted beets, goat cheese, candied walnuts",310
GB06,Thai Peanut Crunch Salad,Superfood Salads,"Red cabbage, edamame, shredded carrots, bell peppers, spicy peanut drizzle",280
GB07,Avocado Green Goddess Wrap,Wraps,"Spinach tortilla with mashed avocado, cucumber ribbons, alfalfa sprouts",260
GB08,Spiced Tofu Teriyaki Wrap,Wraps,"Gluten-free wrap, pan-seared non-GMO tofu, sesame cabbage slaw",270
GB09,Berry Antioxidant Acai Bowl,Smoothie Bowls,"Pure frozen acai puree topped with chia seeds, banana, house granola",320
GB10,Green Detox Cold Pressed Juice,Beverages,"Celery, green apple, cucumber, spinach, ginger, cold pressed fresh daily",180
''', encoding="utf-8")

(GREEN_DIR / "costs.csv").write_text("""item_id,item_name,ingredient_cost,packaging_cost
GB01,Quinoa Harvest Power Bowl,130.00,16.00
GB02,Chipotle Black Bean Bowl,105.00,16.00
GB03,Mediterranean Falafel Bowl,115.00,16.00
GB04,Kale Tahini Caesar,118.00,14.00
GB05,Roasted Beet & Goat Cheese,125.00,14.00
GB06,Thai Peanut Crunch Salad,98.00,14.00
GB07,Avocado Green Goddess Wrap,88.00,12.00
GB08,Spiced Tofu Teriyaki Wrap,92.00,12.00
GB09,Berry Antioxidant Acai Bowl,135.00,15.00
GB10,Green Detox Cold Pressed Juice,60.00,10.00
""", encoding="utf-8")

(GREEN_DIR / "sales.csv").write_text("""date,item_name,quantity,revenue
2026-10-10,Quinoa Harvest Power Bowl,26,8840
2026-10-10,Chipotle Black Bean Bowl,20,6200
2026-10-10,Kale Tahini Caesar,18,5220
2026-10-10,Green Detox Cold Pressed Juice,25,4500
2026-10-10,Berry Antioxidant Acai Bowl,15,4800
2026-10-11,Quinoa Harvest Power Bowl,30,10200
2026-10-11,Mediterranean Falafel Bowl,22,7040
2026-10-11,Avocado Green Goddess Wrap,18,4680
2026-10-11,Green Detox Cold Pressed Juice,28,5040
2026-10-12,Chipotle Black Bean Bowl,24,7440
2026-10-12,Kale Tahini Caesar,20,5800
2026-10-12,Spiced Tofu Teriyaki Wrap,16,4320
2026-10-12,Berry Antioxidant Acai Bowl,18,5760
2026-10-13,Quinoa Harvest Power Bowl,32,10880
2026-10-13,Green Detox Cold Pressed Juice,30,5400
2026-10-13,Mediterranean Falafel Bowl,24,7680
2026-10-13,Roasted Beet & Goat Cheese,14,4340
2026-10-14,Quinoa Harvest Power Bowl,35,11900
2026-10-14,Kale Tahini Caesar,22,6380
2026-10-14,Chipotle Black Bean Bowl,25,7750
2026-10-14,Green Detox Cold Pressed Juice,32,5760
""", encoding="utf-8")

(GREEN_DIR / "reviews.csv").write_text("""review_date,rating,review_text,item_name,source
2026-10-10,5,"The Quinoa Harvest Bowl is so filling, nutritious and flavorful! Clean eating at its best.",Quinoa Harvest Power Bowl,Google
2026-10-11,4,"Great fresh ingredients. Kale Caesar is tasty but wish there was slightly more dressing.",Kale Tahini Caesar,Zomato
2026-10-12,5,"Best cold-pressed juices in Hyderabad. The Green Detox gives me so much energy.",Green Detox Cold Pressed Juice,Swiggy
2026-10-13,3,"Acai bowl melted a bit during delivery. Tasted fine though.",Berry Antioxidant Acai Bowl,Zomato
2026-10-14,5,"Love the Mediterranean Falafel bowl. Warm quinoa and house hummus are amazing.",Mediterranean Falafel Bowl,Google
""", encoding="utf-8")

print("Created distinct seed datasets for 4 restaurant profiles.")
