from pydantic import BaseModel
from datetime import date
from typing import Optional


class Offer(BaseModel):
    id: str
    store_id: str
    product_name: str
    brand: Optional[str] = None
    category: str
    offer_price: float
    original_price: Optional[float] = None
    unit: str
    quantity_deal: Optional[str] = None
    max_per_household: Optional[int] = None
    valid_from: date
    valid_to: date
    requires_membership: bool = False
    image_url: Optional[str] = None
    raw_text: str
