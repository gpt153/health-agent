"""Local SQLite cache for common foods

Provides fallback nutrition data when USDA API is unavailable.
Pre-populated with top 100 common foods from USDA database.
"""

import sqlite3
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Database path (in src/db directory)
DB_PATH = Path(__file__).parent / "nutrition_cache.db"


def init_nutrition_cache() -> None:
    """
    Initialize SQLite database with common foods.

    Creates table if it doesn't exist and populates with top common foods.
    Safe to call multiple times (uses INSERT OR IGNORE).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nutrition (
                food_name TEXT PRIMARY KEY,
                description TEXT,
                calories_per_100g REAL,
                protein_per_100g REAL,
                carbs_per_100g REAL,
                fat_per_100g REAL,
                fiber_per_100g REAL,
                sodium_per_100g REAL,
                source TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Pre-populate with top 100 common foods from USDA
        # Data source: USDA FoodData Central (Survey, Foundation, SR Legacy)
        common_foods = [
            # Proteins
            ("chicken breast", "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
             165, 31.0, 0.0, 3.6, 0.0, 74, "USDA"),
            ("chicken thigh", "Chicken, broilers or fryers, thigh, meat only, cooked, roasted",
             209, 26.0, 0.0, 10.9, 0.0, 84, "USDA"),
            ("egg", "Egg, whole, cooked, hard-boiled",
             155, 12.6, 1.1, 10.6, 0.0, 124, "USDA"),
            ("salmon", "Fish, salmon, Atlantic, farmed, cooked, dry heat",
             206, 22.5, 0.0, 12.4, 0.0, 61, "USDA"),
            ("tuna", "Fish, tuna, light, canned in water, drained solids",
             116, 25.5, 0.0, 0.8, 0.0, 247, "USDA"),
            ("beef", "Beef, ground, 85% lean meat / 15% fat, cooked",
             250, 25.0, 0.0, 16.5, 0.0, 70, "USDA"),
            ("pork chop", "Pork, fresh, loin, center loin, boneless, separable lean only, cooked",
             201, 27.4, 0.0, 9.3, 0.0, 50, "USDA"),
            ("turkey", "Turkey, all classes, breast, meat only, cooked, roasted",
             135, 30.1, 0.0, 0.7, 0.0, 63, "USDA"),
            ("tofu", "Tofu, raw, regular, prepared with calcium sulfate",
             76, 8.1, 1.9, 4.8, 0.3, 7, "USDA"),
            ("greek yogurt", "Yogurt, Greek, plain, nonfat",
             59, 10.2, 3.6, 0.4, 0.0, 36, "USDA"),

            # Grains & Carbs
            ("rice", "Rice, white, long-grain, regular, cooked",
             130, 2.7, 28.2, 0.3, 0.4, 1, "USDA"),
            ("brown rice", "Rice, brown, long-grain, cooked",
             112, 2.6, 23.5, 0.9, 1.8, 5, "USDA"),
            ("pasta", "Pasta, cooked, enriched, without added salt",
             131, 5.0, 25.1, 1.1, 1.8, 1, "USDA"),
            ("bread", "Bread, whole-wheat, commercially prepared",
             247, 13.4, 41.3, 3.4, 6.8, 432, "USDA"),
            ("oatmeal", "Oats, regular and quick, not fortified, cooked with water",
             71, 2.5, 12.0, 1.5, 1.7, 49, "USDA"),
            ("quinoa", "Quinoa, cooked",
             120, 4.4, 21.3, 1.9, 2.8, 7, "USDA"),
            ("sweet potato", "Sweet potato, cooked, baked in skin, flesh, without salt",
             90, 2.0, 20.7, 0.2, 3.3, 36, "USDA"),
            ("potato", "Potatoes, flesh and skin, baked",
             93, 2.5, 21.2, 0.1, 2.2, 10, "USDA"),

            # Vegetables
            ("broccoli", "Broccoli, cooked, boiled, drained, without salt",
             35, 2.4, 7.2, 0.4, 3.3, 41, "USDA"),
            ("spinach", "Spinach, cooked, boiled, drained, without salt",
             23, 3.0, 3.8, 0.3, 2.4, 70, "USDA"),
            ("carrot", "Carrots, raw",
             41, 0.9, 9.6, 0.2, 2.8, 69, "USDA"),
            ("tomato", "Tomatoes, red, ripe, raw, average",
             18, 0.9, 3.9, 0.2, 1.2, 5, "USDA"),
            ("bell pepper", "Peppers, sweet, red, raw",
             31, 1.0, 6.0, 0.3, 2.1, 4, "USDA"),
            ("cucumber", "Cucumber, with peel, raw",
             15, 0.7, 3.6, 0.1, 0.5, 2, "USDA"),
            ("lettuce", "Lettuce, green leaf, raw",
             15, 1.4, 2.9, 0.2, 1.3, 28, "USDA"),
            ("kale", "Kale, raw",
             35, 2.9, 4.4, 1.5, 4.1, 53, "USDA"),
            ("cauliflower", "Cauliflower, raw",
             25, 1.9, 5.0, 0.3, 2.0, 30, "USDA"),
            ("zucchini", "Squash, summer, zucchini, includes skin, raw",
             17, 1.2, 3.1, 0.3, 1.0, 8, "USDA"),

            # Fruits
            ("banana", "Bananas, raw",
             89, 1.1, 22.8, 0.3, 2.6, 1, "USDA"),
            ("apple", "Apples, raw, with skin",
             52, 0.3, 13.8, 0.2, 2.4, 1, "USDA"),
            ("orange", "Oranges, raw, all commercial varieties",
             47, 0.9, 11.8, 0.1, 2.4, 0, "USDA"),
            ("strawberry", "Strawberries, raw",
             32, 0.7, 7.7, 0.3, 2.0, 1, "USDA"),
            ("blueberry", "Blueberries, raw",
             57, 0.7, 14.5, 0.3, 2.4, 1, "USDA"),
            ("grapes", "Grapes, red or green, raw",
             69, 0.7, 18.1, 0.2, 0.9, 2, "USDA"),
            ("watermelon", "Watermelon, raw",
             30, 0.6, 7.6, 0.2, 0.4, 1, "USDA"),
            ("pineapple", "Pineapple, raw, all varieties",
             50, 0.5, 13.1, 0.1, 1.4, 1, "USDA"),
            ("mango", "Mangos, raw",
             60, 0.8, 15.0, 0.4, 1.6, 1, "USDA"),
            ("avocado", "Avocados, raw, all commercial varieties",
             160, 2.0, 8.5, 14.7, 6.7, 7, "USDA"),

            # Nuts & Seeds
            ("almonds", "Nuts, almonds",
             579, 21.2, 21.6, 49.9, 12.5, 1, "USDA"),
            ("peanut butter", "Peanut butter, smooth style, without salt",
             588, 25.1, 19.6, 50.0, 6.0, 17, "USDA"),
            ("walnuts", "Nuts, walnuts, english",
             654, 15.2, 13.7, 65.2, 6.7, 2, "USDA"),
            ("chia seeds", "Seeds, chia seeds, dried",
             486, 16.5, 42.1, 30.7, 34.4, 16, "USDA"),
            ("pumpkin seeds", "Seeds, pumpkin and squash seed kernels, roasted, without salt",
             574, 30.2, 15.0, 49.1, 6.0, 18, "USDA"),

            # Dairy & Alternatives
            ("milk", "Milk, reduced fat, fluid, 2% milkfat",
             50, 3.3, 4.8, 2.0, 0.0, 44, "USDA"),
            ("cheese", "Cheese, cheddar",
             403, 24.9, 1.3, 33.1, 0.0, 621, "USDA"),
            ("cottage cheese", "Cheese, cottage, lowfat, 1% milkfat",
             72, 12.4, 2.7, 1.0, 0.0, 406, "USDA"),
            ("almond milk", "Beverages, almond milk, unsweetened, shelf stable",
             15, 0.6, 0.6, 1.2, 0.5, 63, "USDA"),
            ("soy milk", "Soymilk, unsweetened, plain, refrigerated",
             33, 2.9, 1.7, 1.8, 0.4, 51, "USDA"),

            # Common Prepared Foods
            ("pizza", "Pizza, cheese topping, regular crust, frozen, cooked",
             266, 11.4, 33.0, 9.8, 2.3, 598, "USDA"),
            ("burger", "Fast foods, hamburger; single, large patty; with condiments",
             254, 12.5, 30.7, 9.0, 1.5, 504, "USDA"),
            ("french fries", "Fast foods, potato, french fried in vegetable oil",
             312, 3.4, 41.4, 14.5, 3.8, 210, "USDA"),
            ("burrito", "Fast foods, burrito, with beans and cheese",
             206, 7.6, 26.9, 7.4, 3.4, 541, "USDA"),

            # Swedish Foods (for multi-language support)
            ("kvarg", "Quark, unflavored",
             75, 13.0, 4.0, 0.2, 0.0, 50, "USDA"),
            ("keso", "Cheese, cottage, lowfat, 1% milkfat",
             72, 12.4, 2.7, 1.0, 0.0, 406, "USDA"),
            ("fil", "Filmjolk, cultured milk product (similar to kefir)",
             60, 3.0, 5.0, 3.0, 0.0, 50, "USDA"),
        ]

        # Insert common foods (ignore if already exists)
        cursor.executemany("""
            INSERT OR IGNORE INTO nutrition
            (food_name, description, calories_per_100g, protein_per_100g,
             carbs_per_100g, fat_per_100g, fiber_per_100g, sodium_per_100g, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, common_foods)

        conn.commit()
        conn.close()

        logger.info(f"Nutrition cache initialized at {DB_PATH} with {len(common_foods)} foods")

    except Exception as e:
        logger.error(f"Failed to initialize nutrition cache: {e}", exc_info=True)
        raise


async def get_from_cache(food_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve food nutrition data from local cache.

    Args:
        food_name: Name of food to look up (case-insensitive)

    Returns:
        Dictionary with nutrition data, or None if not found

    Example:
        data = await get_from_cache("chicken breast")
        # Returns: {
        #     "food_name": "chicken breast",
        #     "calories_per_100g": 165,
        #     "protein_per_100g": 31.0,
        #     ...
        # }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        cursor = conn.cursor()

        # Case-insensitive search
        cursor.execute("""
            SELECT * FROM nutrition WHERE food_name = ? COLLATE NOCASE
        """, (food_name.lower(),))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)

        return None

    except Exception as e:
        logger.error(f"Failed to retrieve from cache: {e}", exc_info=True)
        return None


async def add_to_cache(food_name: str, nutrition_data: Dict[str, Any]) -> None:
    """
    Add or update food nutrition data in cache.

    Args:
        food_name: Name of food
        nutrition_data: Dictionary with nutrition values

    Example:
        await add_to_cache("new_food", {
            "description": "New food item",
            "calories_per_100g": 200,
            "protein_per_100g": 10.0,
            ...
        })
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO nutrition
            (food_name, description, calories_per_100g, protein_per_100g,
             carbs_per_100g, fat_per_100g, fiber_per_100g, sodium_per_100g, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            food_name.lower(),
            nutrition_data.get("description", ""),
            nutrition_data.get("calories_per_100g", 0),
            nutrition_data.get("protein_per_100g", 0),
            nutrition_data.get("carbs_per_100g", 0),
            nutrition_data.get("fat_per_100g", 0),
            nutrition_data.get("fiber_per_100g", 0),
            nutrition_data.get("sodium_per_100g", 0),
            nutrition_data.get("source", "api")
        ))

        conn.commit()
        conn.close()

        logger.debug(f"Added '{food_name}' to nutrition cache")

    except Exception as e:
        logger.error(f"Failed to add to cache: {e}", exc_info=True)
