"""Tests for cost calculation and savings estimation."""

from backend.planner.savings import (
    estimate_ingredient_cost,
    calculate_meal_cost,
    _calculate_offer_cost,
    _estimate_default_cost,
)
from backend.models.recipe import Ingredient
from backend.models.offer import Offer
from datetime import date, timedelta


def _make_offer(**kwargs):
    defaults = dict(
        id="test", store_id="test", product_name="Test",
        brand=None, category="meat", offer_price=100.0,
        original_price=None, unit="kr/kg", quantity_deal=None,
        max_per_household=None, valid_from=date.today(),
        valid_to=date.today() + timedelta(days=6),
        requires_membership=False, image_url=None, raw_text="",
    )
    defaults.update(kwargs)
    return Offer(**defaults)


def test_calculate_offer_cost_per_kg():
    """500g at 89 kr/kg = ~44.5 kr."""
    offer = _make_offer(offer_price=89.0, unit="kr/kg")
    cost = _calculate_offer_cost(500, "g", offer)
    assert abs(cost - 44.5) < 1.0


def test_calculate_offer_cost_per_st():
    """Per-piece pricing should return offer_price * count."""
    offer = _make_offer(offer_price=25.0, unit="kr/st")
    cost = _calculate_offer_cost(2, "st", offer)
    assert cost == 50.0


def test_calculate_offer_cost_small_amount():
    """1 msk at kr/st should cost 1 package."""
    offer = _make_offer(offer_price=30.0, unit="kr/st")
    cost = _calculate_offer_cost(1, "msk", offer)
    assert cost == 30.0  # 1 package


def test_premium_ingredient_pricing():
    """laxfilé should use PREMIUM_PRICES (250 kr/kg), not default meat (130 kr/kg)."""
    ing = Ingredient(name="laxfilé", amount=500, unit="g", category="fish", is_pantry_staple=False)
    cost_with, cost_without = estimate_ingredient_cost(ing, None)
    # 500g = 0.5kg at 250 kr/kg = 125 kr (not 0.5 * 180 = 90 from default fish)
    assert cost_with > 100  # Premium priced
    assert cost_with == cost_without  # No offer = same price


def test_pantry_staple_zero_cost():
    """Pantry staples should have zero cost."""
    ing = Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True)
    cost_with, cost_without = estimate_ingredient_cost(ing, None)
    assert cost_with == 0.0
    assert cost_without == 0.0


def test_max_ingredient_cost_cap():
    """Single ingredient should not exceed 400 kr."""
    ing = Ingredient(name="oxfilé", amount=3000, unit="g", category="meat", is_pantry_staple=False)
    cost_with, cost_without = estimate_ingredient_cost(ing, None)
    assert cost_with <= 400.0


def test_small_unit_package_cost():
    """Small units should cost a whole package, not negligible amounts."""
    # msk/tsk = buy a whole package
    cost_dairy = _estimate_default_cost(1, "msk", 100.0, "dairy")
    assert cost_dairy == 22.0  # Dairy package (crème fraiche etc)
    cost_pantry = _estimate_default_cost(1, "tsk", 100.0, "pantry")
    assert cost_pantry == 15.0  # Pantry package (soja etc)
    # krm/nypa = truly negligible
    cost_krm = _estimate_default_cost(1, "krm", 100.0)
    assert cost_krm == 1.0


def test_calculate_meal_cost_aggregation(sample_offers):
    """Total cost should be sum of ingredient costs."""
    ingredients = [
        Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
    ]
    cost_with, cost_without, matches = calculate_meal_cost(ingredients, sample_offers)
    assert cost_with > 0
    assert cost_without > 0
    assert len(matches) == 3


def test_offer_gives_savings(sample_offers):
    """Ingredients matched to offers should cost less than regular price."""
    ing = Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False)
    # Find the chicken offer
    chicken_offer = next(o for o in sample_offers if "Kyckling" in o.product_name)
    cost_with, cost_without = estimate_ingredient_cost(ing, chicken_offer)
    assert cost_with < cost_without
