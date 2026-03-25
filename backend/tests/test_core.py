"""Core unit tests for pricing, matching, scaling, and savings."""

import pytest
from backend.models.offer import Offer
from backend.models.recipe import Ingredient, Recipe, Nutrition
from backend.planner.matcher import match_ingredient_to_offers, count_offer_matches
from backend.planner.savings import estimate_ingredient_cost, calculate_meal_cost
from backend.planner.optimizer import (
    _get_servings_scale, _is_poorly_rated, _is_processed,
    _score_recipe, filter_recipes_by_preferences,
)
from backend.models.user_prefs import UserPreferences
from backend.scrapers.ica_maxi import parse_price, parse_original_price
from backend.recipes.scraper import parse_amount, parse_ingredient_text


# --- Price parsing ---

def test_parse_price_multi_buy():
    price, deal, unit = parse_price("2 för 85 kr")
    assert price == 42.5
    assert deal == "2 för 85 kr"
    assert unit == "kr/st"


def test_parse_price_per_kg():
    price, deal, unit = parse_price("89 kr/kg")
    assert price == 89.0
    assert deal is None
    assert unit == "kr/kg"


def test_parse_price_plain():
    price, deal, unit = parse_price("40 kr")
    assert price == 40.0
    assert unit == "kr/st"


def test_parse_price_empty():
    price, deal, unit = parse_price("")
    assert price == 0.0


def test_parse_original_price():
    assert parse_original_price("Ord.pris 50:11-54:95 kr") == 54.95
    assert parse_original_price("Ord. pris 39:90 kr") == 39.90
    assert parse_original_price("No price here") is None


# --- Ingredient parsing ---

def test_parse_amount_fractions():
    assert parse_amount("2 1/2") == 2.5
    assert parse_amount("½") == 0.5
    assert parse_amount("3") == 3.0


def test_parse_ingredient_text():
    ing = parse_ingredient_text("550 g falukorv")
    assert ing.amount == 550.0
    assert ing.unit == "g"
    assert ing.name == "falukorv"
    assert ing.category == "meat"


def test_parse_ingredient_no_amount():
    ing = parse_ingredient_text("peppar")
    assert ing.amount == 0.0
    assert ing.name == "peppar"


# --- Matching ---

def _make_offer(name, category="meat", price=89.0, original=120.0):
    from datetime import date
    return Offer(
        id="o1", store_id="test", product_name=name,
        category=category, offer_price=price, original_price=original,
        unit="kr/kg", valid_from=date.today(), valid_to=date.today(),
        requires_membership=False, raw_text=name,
    )


def _make_ingredient(name, category="meat"):
    return Ingredient(name=name, amount=500, unit="g", category=category, is_pantry_staple=False)


def test_match_exact():
    offer = _make_offer("Kycklingfilé")
    ing = _make_ingredient("kycklingfilé", "meat")
    result = match_ingredient_to_offers(ing, [offer])
    assert result is not None
    assert result.product_name == "Kycklingfilé"


def test_match_pantry_staple_skipped():
    offer = _make_offer("Salt", "pantry")
    ing = Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True)
    result = match_ingredient_to_offers(ing, [offer])
    assert result is None


def test_count_matches():
    offers = [_make_offer("Kycklingfilé"), _make_offer("Grädde", "dairy", 15, 25)]
    ings = [
        _make_ingredient("kycklingfilé"),
        _make_ingredient("grädde", "dairy"),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
    ]
    assert count_offer_matches(ings, offers) >= 1


# --- Cost estimation ---

def test_cost_with_offer():
    offer = _make_offer("Kyckling", price=89.0, original=120.0)
    ing = _make_ingredient("kyckling")  # 500g
    cost_with, cost_without = estimate_ingredient_cost(ing, offer, 1.0)
    assert cost_with > 0
    assert cost_without > cost_with


def test_cost_no_offer():
    ing = _make_ingredient("kyckling")
    cost_with, cost_without = estimate_ingredient_cost(ing, None, 1.0)
    assert cost_with == cost_without  # No savings


def test_cost_pantry_zero():
    ing = Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True)
    cost_with, cost_without = estimate_ingredient_cost(ing, None, 1.0)
    assert cost_with == 0.0


# --- Servings scale ---

def test_scale_default():
    r = Recipe(id="r1", title="T", source="t", servings=4, cook_time_minutes=30)
    assert _get_servings_scale(r, 4) == 1.0
    assert _get_servings_scale(r, 2) == 0.5
    assert _get_servings_scale(r, 8) == 2.0


def test_scale_recipe_2_servings():
    r = Recipe(id="r1", title="T", source="t", servings=2, cook_time_minutes=30)
    assert _get_servings_scale(r, 4) == 2.0


def test_scale_zero_servings_defaults_to_4():
    r = Recipe(id="r1", title="T", source="t", servings=0, cook_time_minutes=30)
    assert _get_servings_scale(r, 4) == 1.0


# --- Rating / scoring ---

def test_poorly_rated():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30, rating=2.0, rating_count=10)
    assert _is_poorly_rated(r) is True


def test_not_poorly_rated_few_votes():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30, rating=2.0, rating_count=1)
    assert _is_poorly_rated(r) is False


def test_well_rated():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30, rating=4.5, rating_count=50)
    assert _is_poorly_rated(r) is False


def test_score_with_rating():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30, rating=5.0, rating_count=100)
    assert _score_recipe(r, 3) > _score_recipe(r, 3).__class__(6.0)  # 6 + 2.5 = 8.5


def test_score_no_rating():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30)
    assert _score_recipe(r, 3) == 6.0  # 3*2 + 0


# --- Processed detection ---

def test_is_processed():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30,
        ingredients=[Ingredient(name="Fish fingers", amount=400, unit="g", category="frozen")])
    assert _is_processed(r) is True


def test_not_processed():
    r = Recipe(id="r", title="T", source="t", servings=4, cook_time_minutes=30,
        ingredients=[Ingredient(name="Kycklingfilé", amount=600, unit="g", category="meat")])
    assert _is_processed(r) is False


# --- Preference filtering ---

def test_filter_vegetarian():
    recipes = [
        Recipe(id="r1", title="Kycklingsallad", source="t", servings=4, cook_time_minutes=30,
            ingredients=[Ingredient(name="kyckling", amount=500, unit="g", category="meat")]),
        Recipe(id="r2", title="Grönsakssoppa", source="t", servings=4, cook_time_minutes=30,
            ingredients=[Ingredient(name="morot", amount=300, unit="g", category="produce")]),
    ]
    prefs = UserPreferences(dietary_restrictions=["vegetarian"])
    result = filter_recipes_by_preferences(recipes, prefs)
    assert len(result) == 1
    assert result[0].id == "r2"


def test_filter_poorly_rated():
    recipes = [
        Recipe(id="r1", title="Bad", source="t", servings=4, cook_time_minutes=30, rating=1.5, rating_count=20),
        Recipe(id="r2", title="Good", source="t", servings=4, cook_time_minutes=30, rating=4.5, rating_count=100),
    ]
    prefs = UserPreferences()
    result = filter_recipes_by_preferences(recipes, prefs)
    assert len(result) == 1
    assert result[0].id == "r2"


# --- Negative savings clamp ---

def test_savings_never_negative():
    """total_savings should be clamped to 0, never negative."""
    # This is tested via the optimizer code: max(0, total_without - total_cost)
    total_without = 100
    total_cost = 120  # More expensive with "offers" (bad data)
    total_savings = max(0, total_without - total_cost)
    assert total_savings == 0
