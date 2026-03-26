from pydantic import BaseModel

from backend.models.offer import Offer
from backend.models.recipe import Recipe
from backend.models.user_prefs import UserPreferences
from backend.models.shopping_list import ShoppingList


class PlannedMeal(BaseModel):
    day: str
    recipe: Recipe
    scaled_servings: int
    offer_matches: list[Offer] = []
    estimated_cost: float = 0.0
    estimated_cost_without_offers: float = 0.0
    reasoning: str = ""
    popularity_score: float = 0.0   # 0-5 estimated popularity
    is_fallback: bool = False       # True if generated without AI
    mealprep_tip: str = ""
    side_suggestion: str = ""       # "Servera med kokt potatis och lingon"


class WeeklyMenu(BaseModel):
    id: str
    week_number: int
    year: int
    store_id: str
    store_name: str = ""
    preferences: UserPreferences
    meals: list[PlannedMeal] = []
    shopping_list: ShoppingList = ShoppingList()
    total_cost: float = 0.0
    total_cost_without_offers: float = 0.0
    total_savings: float = 0.0
    savings_percentage: float = 0.0
    generated_at: str = ""
    pinned_offers: list[Offer] = []
    budget_exceeded: bool = False      # True if total_cost > budget
    budget_exceeded_by: float = 0.0    # How much over budget
    confirmed_savings: float = 0.0
    estimated_savings: float = 0.0
    date_range: str = ""               # "24 mar – 28 mar" for display
    active_filters: list[str] = []     # ["Laktosfri", "Fläskfri"] for display
