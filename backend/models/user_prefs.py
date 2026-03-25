from pydantic import BaseModel
from typing import Optional


class TimeMix(BaseModel):
    """How many quick vs slow dinners the user wants."""
    quick_count: int = 0       # ≤30 min
    medium_count: int = 0      # 31-45 min
    slow_count: int = 0        # 46+ min


class UserPreferences(BaseModel):
    household_size: int = 4
    num_dinners: int = 5
    budget_per_week: Optional[int] = None
    max_cook_time: Optional[int] = None
    time_mix: Optional[TimeMix] = None
    dietary_restrictions: list[str] = []
    lifestyle_preferences: list[str] = []  # avoid_processed, prefer_organic, prefer_healthy, prefer_sustainable
    disliked_ingredients: list[str] = []
    pinned_offer_ids: list[str] = []       # Offer IDs the user wants to build menu around
    store_id: str = "ica-maxi-1004097"
    has_children: bool = False
    selected_days: list[str] = []          # Empty = auto-assign, or specific days like ["monday", "wednesday"]
