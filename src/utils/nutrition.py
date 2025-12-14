"""Nutrition calculation utilities"""
from src.models.food import FoodItem, FoodMacros


def calculate_totals(foods: list[FoodItem]) -> tuple[int, FoodMacros]:
    """Calculate total calories and macros from food items"""
    total_calories = sum(food.calories for food in foods)
    total_protein = sum(food.macros.protein for food in foods)
    total_carbs = sum(food.macros.carbs for food in foods)
    total_fat = sum(food.macros.fat for food in foods)

    total_macros = FoodMacros(
        protein=total_protein,
        carbs=total_carbs,
        fat=total_fat
    )

    return total_calories, total_macros
