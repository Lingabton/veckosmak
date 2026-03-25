from pydantic import BaseModel
from typing import Optional

from backend.models.offer import Offer


class ShoppingItem(BaseModel):
    ingredient_name: str
    total_amount: float
    unit: str
    category: str
    matched_offer: Optional[Offer] = None
    estimated_price: float
    is_on_offer: bool = False


class ShoppingList(BaseModel):
    items: list[ShoppingItem] = []
    total_estimated_cost: float = 0.0
    items_on_offer: int = 0
    items_not_on_offer: int = 0
