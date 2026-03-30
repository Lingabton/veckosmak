"""Calculate meal costs and savings based on offer matches."""

import logging
from backend.models.offer import Offer
from backend.models.recipe import Ingredient
from backend.planner.matcher import match_ingredient_to_offers

logger = logging.getLogger(__name__)

# Default prices per category (kr per typical unit) when no offer/price is known
DEFAULT_PRICES = {
    "meat": 130.0,    # kr/kg — average (färs/korv)
    "fish": 180.0,    # kr/kg
    "dairy": 30.0,    # kr/st
    "produce": 25.0,  # kr/st
    "pantry": 20.0,   # kr/st
    "bakery": 30.0,   # kr/st
    "frozen": 35.0,   # kr/st
    "other": 25.0,    # kr/st
}

# Premium ingredients that cost much more than category average
PREMIUM_PRICES = {
    "oxfilé": 550.0,       # kr/kg
    "entrecôte": 400.0,
    "entrecote": 400.0,
    "ryggbiff": 350.0,
    "lammfilé": 400.0,
    "lammstek": 300.0,
    "lamm kotlett": 350.0,
    "lammlägg": 250.0,
    "lammfärs": 200.0,
    "lammkorv": 200.0,
    "lammbog": 200.0,
    "lamm": 280.0,          # Generic lamb — catch-all
    "kalvfilé": 450.0,
    "ankbröst": 350.0,
    "viltfilé": 400.0,
    "älgfilé": 400.0,
    "laxfilé": 250.0,
    "räkor": 300.0,
    "räka": 300.0,
    "pilgrimsmussla": 500.0,
    "hummer": 600.0,
    "sjötunga": 400.0,
    "parmesan": 200.0,     # kr/kg
    "parmesanost": 200.0,
    "mozzarella": 120.0,
    "gruyère": 250.0,
    "saffran": 60.0,       # kr/st (per förpackning)
    "tryffel": 200.0,
    "pinjenötter": 200.0,  # kr/kg
}

# Approximate weight per unit for weight-based pricing
WEIGHT_PER_UNIT = {
    "g": 0.001,   # grams to kg
    "kg": 1.0,
    "dl": 0.1,    # rough: 1 dl ~ 100g
    "l": 1.0,
    "ml": 0.001,
    "cl": 0.01,
    "st": 1.0,    # 1 piece
    "msk": 0.015, # ~15g
    "tsk": 0.005, # ~5g
    "krm": 0.001,
    "port": 1.0,
    "nypa": 0.001,
    "knippe": 1.0,
}


def estimate_ingredient_cost(
    ingredient: Ingredient,
    offer: Offer | None,
    servings_scale: float = 1.0,
) -> tuple[float, float]:
    """Estimate cost for an ingredient with and without offer.

    Returns (cost_with_offer, cost_without_offer).
    """
    if ingredient.is_pantry_staple:
        return 0.0, 0.0

    amount = ingredient.amount * servings_scale
    if amount == 0:
        amount = 1.0  # Default to 1 unit if no amount specified

    # Max reasonable cost per single ingredient for a family dinner
    MAX_INGREDIENT_COST = 400.0

    if offer:
        offer_cost = min(_calculate_offer_cost(amount, ingredient.unit, offer), MAX_INGREDIENT_COST)
        if offer.original_price:
            regular_cost = min(_calculate_regular_cost(
                amount, ingredient.unit, offer.original_price, offer.unit
            ), MAX_INGREDIENT_COST * 1.5)
        else:
            regular_cost = offer_cost * 1.3
        return offer_cost, regular_cost

    # No offer match — check premium price first, then category default
    name_lower = ingredient.name.lower()
    price = DEFAULT_PRICES.get(ingredient.category, 25.0)
    for premium_name, premium_price in PREMIUM_PRICES.items():
        if premium_name in name_lower:
            price = premium_price
            break
    cost = min(_estimate_default_cost(amount, ingredient.unit, price), MAX_INGREDIENT_COST)
    return cost, cost


def _calculate_offer_cost(amount: float, unit: str, offer: Offer) -> float:
    """Calculate cost using offer price."""
    if offer.unit == "kr/kg":
        kg = amount * WEIGHT_PER_UNIT.get(unit, 0.001)
        # "port" typically means per-person portions (~150-200g for protein)
        if unit == "port":
            kg = amount * 0.175  # ~175g per portion for meat/fish
        return offer.offer_price * kg
    elif offer.unit == "kr/st" or offer.unit == "kr/förp":
        # For per-piece pricing, estimate how many retail packages needed
        if unit in ("g", "kg"):
            # Assume ~500g per package for meat/fish
            kg = amount * WEIGHT_PER_UNIT.get(unit, 0.001)
            pieces = max(1, kg / 0.5)
            return offer.offer_price * pieces
        elif unit in ("dl", "l", "ml", "cl"):
            liters = amount * WEIGHT_PER_UNIT.get(unit, 0.1)
            pieces = max(1, liters / 0.5)
            return offer.offer_price * pieces
        elif unit == "port":
            # "4 port torskrygg (à 140g)" = ~4 × 150g = need ~1-2 packages
            pieces = max(1, (amount * 0.175) / 0.5)
            return offer.offer_price * pieces
        elif unit == "knippe":
            return offer.offer_price
        elif unit in ("msk", "tsk", "krm", "nypa"):
            return offer.offer_price  # 1 package covers any small amount
        else:
            # "st" — but cap at reasonable number (avoid 6 slices = 6 packages)
            return offer.offer_price * min(max(1, amount), 2)
    elif offer.unit == "kr/l":
        liters = amount * WEIGHT_PER_UNIT.get(unit, 0.1)
        return offer.offer_price * liters

    return offer.offer_price


def _calculate_regular_cost(
    amount: float, unit: str, original_price: float, offer_unit: str
) -> float:
    """Calculate cost using original/regular price."""
    if offer_unit == "kr/kg":
        kg = amount * WEIGHT_PER_UNIT.get(unit, 0.001)
        return original_price * kg
    elif offer_unit in ("kr/st", "kr/förp"):
        if unit in ("g", "kg"):
            pieces = max(1, (amount * WEIGHT_PER_UNIT.get(unit, 0.001)) / 0.5)
            return original_price * pieces
        elif unit in ("dl", "l", "ml", "cl"):
            liters = amount * WEIGHT_PER_UNIT.get(unit, 0.1)
            pieces = max(1, liters / 0.5)
            return original_price * pieces
        return original_price * max(1, amount)
    return original_price


def _estimate_default_cost(amount: float, unit: str, default_price: float) -> float:
    """Estimate cost when no offer exists."""
    if unit in ("g", "kg"):
        kg = amount * WEIGHT_PER_UNIT.get(unit, 0.001)
        return default_price * max(0.1, kg)
    elif unit in ("dl", "l", "ml", "cl"):
        liters = amount * WEIGHT_PER_UNIT.get(unit, 0.1)
        return default_price * max(0.1, liters)
    elif unit == "st":
        # 1 "st" = typically one retail item, cap at reasonable per-item price
        return min(default_price, 40.0) * max(1, amount)
    elif unit == "port":
        # "4 port torskrygg (à 140g)" → 4 × ~175g = 0.7 kg
        kg = amount * 0.175
        return default_price * max(0.1, kg)
    elif unit == "knippe":
        return min(default_price, 25.0)
    elif unit in ("msk", "tsk", "krm", "nypa"):
        # Small amounts — negligible cost
        return 1.0
    else:
        return 3.0


def calculate_meal_cost(
    ingredients: list[Ingredient],
    offers: list[Offer],
    servings_scale: float = 1.0,
) -> tuple[float, float, list[tuple[Ingredient, Offer | None]]]:
    """Calculate total meal cost with and without offers.

    Returns (cost_with_offers, cost_without_offers, ingredient_offer_matches).
    """
    total_offer = 0.0
    total_regular = 0.0
    matches = []

    for ing in ingredients:
        offer = match_ingredient_to_offers(ing, offers)
        cost_offer, cost_regular = estimate_ingredient_cost(ing, offer, servings_scale)
        total_offer += cost_offer
        total_regular += cost_regular
        matches.append((ing, offer))

    return round(total_offer, 2), round(total_regular, 2), matches
