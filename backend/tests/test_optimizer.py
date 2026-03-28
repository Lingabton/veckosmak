"""Tests for menu optimizer filtering and scoring."""

from backend.planner.optimizer import (
    filter_recipes_by_preferences,
    _is_incomplete_recipe,
    _is_pork_ingredient,
    _is_lactose_safe,
    _is_processed,
    _score_recipe,
    generate_fallback_menu,
)
from backend.models.recipe import Ingredient, Recipe
from backend.models.user_prefs import UserPreferences


def _make_recipe(title="Test", ingredients=None, tags=None, diet_labels=None,
                 cook_time=30, rating=None, rating_count=None, **kwargs):
    if ingredients is None:
        ingredients = [
            Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
            Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
            Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="grädde", amount=2, unit="dl", category="dairy", is_pantry_staple=False),
            Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        ]
    return Recipe(
        id=f"test-{title.lower().replace(' ','-')}", title=title,
        source_url=None, source="test", servings=4,
        cook_time_minutes=cook_time, difficulty="easy",
        tags=tags or ["vardag"], diet_labels=diet_labels or [],
        ingredients=ingredients,
        instructions=["Gör mat."],
        image_url=None, rating=rating, rating_count=rating_count,
        **kwargs,
    )


def test_filter_incomplete_recipe():
    """A recipe titled 'Grundrecept sås' with 2 ingredients should be filtered."""
    r = _make_recipe(
        title="Grundrecept sås",
        ingredients=[
            Ingredient(name="smör", amount=50, unit="g", category="dairy", is_pantry_staple=False),
            Ingredient(name="mjöl", amount=3, unit="msk", category="pantry", is_pantry_staple=False),
        ],
    )
    assert _is_incomplete_recipe(r) is True


def test_filter_porkfree():
    """Pork ingredients should be filtered when porkfree is set."""
    r = _make_recipe(ingredients=[
        Ingredient(name="fläskfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="potatis", amount=800, unit="g", category="produce", is_pantry_staple=False),
        Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
        Ingredient(name="grädde", amount=2, unit="dl", category="dairy", is_pantry_staple=False),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
    ])
    prefs = UserPreferences(dietary_restrictions=["porkfree"])
    result = filter_recipes_by_preferences([r], prefs)
    assert len(result) == 0


def test_filter_vegetarian():
    """Meat recipes should be filtered when vegetarian is set."""
    r = _make_recipe()  # Has kycklingfilé
    prefs = UserPreferences(dietary_restrictions=["vegetarian"])
    result = filter_recipes_by_preferences([r], prefs)
    assert len(result) == 0


def test_filter_lactosefree():
    """Dairy ingredients should be filtered unless they are in LACTOSE_SAFE_DAIRY."""
    r_unsafe = _make_recipe(
        title="Gräddsås",
        ingredients=[
            Ingredient(name="grädde", amount=2, unit="dl", category="dairy", is_pantry_staple=False),
            Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
            Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
            Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        ],
    )
    r_safe = _make_recipe(
        title="Smörpasta",
        ingredients=[
            Ingredient(name="smör", amount=50, unit="g", category="dairy", is_pantry_staple=False),
            Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
            Ingredient(name="parmesan", amount=50, unit="g", category="dairy", is_pantry_staple=False),
            Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        ],
    )
    prefs = UserPreferences(dietary_restrictions=["lactosefree"])
    result = filter_recipes_by_preferences([r_unsafe, r_safe], prefs)
    assert len(result) == 1
    assert result[0].title == "Smörpasta"


def test_filter_disliked_ingredients():
    """Recipes with disliked ingredients should be filtered."""
    r = _make_recipe()
    prefs = UserPreferences(disliked_ingredients=["kyckling"])
    result = filter_recipes_by_preferences([r], prefs)
    assert len(result) == 0


def test_filter_poorly_rated():
    """Poorly rated recipes should be filtered."""
    r = _make_recipe(rating=2.5, rating_count=50)
    prefs = UserPreferences()
    result = filter_recipes_by_preferences([r], prefs)
    assert len(result) == 0


def test_well_rated_passes():
    """Well-rated recipes should pass filter."""
    r = _make_recipe(rating=4.5, rating_count=100)
    prefs = UserPreferences()
    result = filter_recipes_by_preferences([r], prefs)
    assert len(result) == 1


def test_is_pork_ingredient():
    assert _is_pork_ingredient("fläskfilé") is True
    assert _is_pork_ingredient("bacon") is True
    assert _is_pork_ingredient("kycklingfilé") is False


def test_is_lactose_safe():
    assert _is_lactose_safe("smör") is True
    assert _is_lactose_safe("parmesan") is True
    assert _is_lactose_safe("grädde") is False


def test_is_processed():
    r = _make_recipe(ingredients=[
        Ingredient(name="falukorv", amount=400, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="potatis", amount=800, unit="g", category="produce", is_pantry_staple=False),
        Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
    ])
    assert _is_processed(r) is True


def test_score_recipe_offer_bonus():
    """More offer matches = higher score."""
    r = _make_recipe(rating=4.0, rating_count=100)
    score_0 = _score_recipe(r, 0)
    score_3 = _score_recipe(r, 3)
    assert score_3 > score_0


def test_score_recipe_rating_bonus():
    """Highly rated recipe with many reviews gets bonus."""
    r_good = _make_recipe(rating=4.5, rating_count=200)
    r_no_rating = _make_recipe(title="No Rating")
    assert _score_recipe(r_good, 0) > _score_recipe(r_no_rating, 0)


def test_fallback_menu_no_duplicates(sample_offers):
    """Fallback generator should not pick the same recipe twice."""
    recipes = [_make_recipe(title=f"Recipe {i}") for i in range(10)]
    prefs = UserPreferences(num_dinners=5)
    menu_data, is_fallback = generate_fallback_menu(sample_offers, recipes, prefs)
    ids = [m["recipe_id"] for m in menu_data["meals"]]
    assert len(ids) == len(set(ids))
    assert is_fallback is True


def test_fallback_menu_respects_num_dinners(sample_offers):
    """Fallback should return exactly num_dinners meals."""
    recipes = [_make_recipe(title=f"Recipe {i}") for i in range(10)]
    for n in [3, 5, 7]:
        prefs = UserPreferences(num_dinners=n)
        menu_data, _ = generate_fallback_menu(sample_offers, recipes, prefs)
        assert len(menu_data["meals"]) == n
