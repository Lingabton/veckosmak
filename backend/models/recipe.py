from pydantic import BaseModel
from typing import Optional


class Nutrition(BaseModel):
    calories: Optional[int] = None       # kcal per serving
    protein: Optional[float] = None      # grams
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None


class Ingredient(BaseModel):
    name: str
    amount: float
    unit: str
    category: str
    is_pantry_staple: bool = False


class Recipe(BaseModel):
    id: str
    title: str
    source_url: Optional[str] = None
    source: str
    servings: int
    cook_time_minutes: int
    difficulty: str = "medium"
    tags: list[str] = []
    diet_labels: list[str] = []
    ingredients: list[Ingredient] = []
    instructions: list[str] = []
    image_url: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    nutrition: Optional[Nutrition] = None
    cooking_method: Optional[str] = None   # "ugn", "spis", "grill", "slowcooker"
