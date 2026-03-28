"""Shared test fixtures for Veckosmak backend tests."""

import pytest
from datetime import date, timedelta

from backend.models.offer import Offer
from backend.models.recipe import Ingredient, Recipe


@pytest.fixture
def sample_offers():
    today = date.today()
    return [
        Offer(
            id="offer-chicken", store_id="ica-maxi-1004097",
            product_name="Kycklingfilé", brand="Kronfågel",
            category="meat", offer_price=89.0, original_price=129.0,
            unit="kr/kg", quantity_deal=None, max_per_household=None,
            valid_from=today, valid_to=today + timedelta(days=6),
            requires_membership=False, image_url=None, raw_text="Kycklingfilé Kronfågel 89 kr/kg",
        ),
        Offer(
            id="offer-salmon", store_id="ica-maxi-1004097",
            product_name="Norsk Laxfilé", brand="ICA",
            category="fish", offer_price=99.0, original_price=149.0,
            unit="kr/kg", quantity_deal=None, max_per_household=None,
            valid_from=today, valid_to=today + timedelta(days=6),
            requires_membership=False, image_url=None, raw_text="Norsk Laxfilé 99 kr/kg",
        ),
        Offer(
            id="offer-mince", store_id="ica-maxi-1004097",
            product_name="Blandfärs", brand="Scan",
            category="meat", offer_price=69.0, original_price=99.0,
            unit="kr/kg", quantity_deal=None, max_per_household=None,
            valid_from=today, valid_to=today + timedelta(days=6),
            requires_membership=False, image_url=None, raw_text="Blandfärs Scan 69 kr/kg",
        ),
        Offer(
            id="offer-milk", store_id="ica-maxi-1004097",
            product_name="Mellanmjölk", brand="Arla",
            category="dairy", offer_price=15.0, original_price=19.0,
            unit="kr/st", quantity_deal=None, max_per_household=None,
            valid_from=today, valid_to=today + timedelta(days=6),
            requires_membership=False, image_url=None, raw_text="Mellanmjölk Arla 15 kr/st",
        ),
        Offer(
            id="offer-pasta-deal", store_id="ica-maxi-1004097",
            product_name="Pasta Penne", brand="ICA",
            category="pantry", offer_price=12.5, original_price=25.0,
            unit="kr/st", quantity_deal="2 för 25 kr", max_per_household=None,
            valid_from=today, valid_to=today + timedelta(days=6),
            requires_membership=False, image_url=None, raw_text="Pasta Penne 2 för 25 kr",
        ),
    ]


@pytest.fixture
def sample_ingredients():
    return [
        Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="laxfilé", amount=400, unit="g", category="fish", is_pantry_staple=False),
        Ingredient(name="nötfärs", amount=400, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        Ingredient(name="olivolja", amount=2, unit="msk", category="pantry", is_pantry_staple=True),
    ]


@pytest.fixture
def sample_recipe():
    return Recipe(
        id="recipe-chicken-pasta",
        title="Kycklingpasta med gräddsås",
        source_url="https://www.ica.se/recept/kycklingpasta/",
        source="ica.se",
        servings=4,
        cook_time_minutes=30,
        difficulty="easy",
        tags=["vardag", "barnvänlig", "snabb"],
        diet_labels=[],
        ingredients=[
            Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
            Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
            Ingredient(name="grädde", amount=2, unit="dl", category="dairy", is_pantry_staple=False),
            Ingredient(name="lök", amount=1, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="vitlök", amount=2, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
            Ingredient(name="peppar", amount=1, unit="krm", category="pantry", is_pantry_staple=True),
        ],
        instructions=["Koka pastan.", "Stek kycklingen.", "Gör sås.", "Blanda."],
        image_url=None,
        rating=4.2,
        rating_count=150,
    )


@pytest.fixture
def vegetarian_recipe():
    return Recipe(
        id="recipe-veg-pasta",
        title="Vegetarisk pasta med svamp",
        source_url=None, source="ica.se",
        servings=4, cook_time_minutes=25, difficulty="easy",
        tags=["vardag", "vegetarisk"],
        diet_labels=["vegetarian"],
        ingredients=[
            Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
            Ingredient(name="champinjoner", amount=250, unit="g", category="produce", is_pantry_staple=False),
            Ingredient(name="grädde", amount=2, unit="dl", category="dairy", is_pantry_staple=False),
            Ingredient(name="parmesan", amount=50, unit="g", category="dairy", is_pantry_staple=False),
            Ingredient(name="vitlök", amount=2, unit="st", category="produce", is_pantry_staple=False),
            Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        ],
        instructions=["Koka pastan.", "Stek svamp.", "Blanda."],
        image_url=None,
    )
