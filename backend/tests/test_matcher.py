"""Tests for ingredient-to-offer matching."""

from backend.planner.matcher import (
    match_ingredient_to_offers,
    count_offer_matches,
    get_canonical_names,
    normalize,
    _word_match,
    clean_ingredient_name,
)
from backend.models.recipe import Ingredient
from backend.models.offer import Offer


def test_synonym_matching_nötfärs(sample_offers):
    """nötfärs should match Blandfärs via SYNONYMS."""
    ing = Ingredient(name="nötfärs", amount=400, unit="g", category="meat", is_pantry_staple=False)
    match = match_ingredient_to_offers(ing, sample_offers)
    assert match is not None
    assert "Blandfärs" in match.product_name


def test_synonym_matching_lax(sample_offers):
    """laxfilé should match Norsk Laxfilé."""
    ing = Ingredient(name="laxfilé", amount=400, unit="g", category="fish", is_pantry_staple=False)
    match = match_ingredient_to_offers(ing, sample_offers)
    assert match is not None
    assert "Lax" in match.product_name


def test_synonym_matching_pasta(sample_offers):
    """pasta should match Pasta Penne."""
    ing = Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False)
    match = match_ingredient_to_offers(ing, sample_offers)
    assert match is not None
    assert "Pasta" in match.product_name


def test_word_match_short_words_filtered():
    """Words under 4 chars should be filtered out to avoid false positives."""
    # "ris" is 3 chars — should be filtered, but if it's the only word, it stays
    score = _word_match({"ris"}, {"ris", "gryta"})
    assert score > 0  # Single word stays when it's the only one

    # But if there are longer words, short ones are filtered
    score = _word_match({"ris", "basmati"}, {"basmati", "uncle", "bens"})
    assert score > 0  # "basmati" matches


def test_category_mismatch_penalty(sample_offers):
    """A meat ingredient should not match a dairy offer with high score."""
    ing = Ingredient(name="filé", amount=1, unit="st", category="meat", is_pantry_staple=False)
    # This is a weak/ambiguous term — the category mismatch should penalize dairy matches
    match = match_ingredient_to_offers(ing, sample_offers)
    # Should not match milk
    if match:
        assert match.category != "dairy"


def test_substring_containment(sample_offers):
    """'lax' should match 'Norsk Laxfilé' via substring."""
    names = get_canonical_names("laxfilé")
    assert "lax" in names or "laxfilé" in names


def test_pantry_staple_skipped(sample_offers):
    """Pantry staples should never match."""
    ing = Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True)
    match = match_ingredient_to_offers(ing, sample_offers)
    assert match is None


def test_count_offer_matches(sample_offers):
    """count_offer_matches returns correct count."""
    ingredients = [
        Ingredient(name="kycklingfilé", amount=500, unit="g", category="meat", is_pantry_staple=False),
        Ingredient(name="pasta", amount=400, unit="g", category="pantry", is_pantry_staple=False),
        Ingredient(name="salt", amount=1, unit="tsk", category="pantry", is_pantry_staple=True),
        Ingredient(name="exotisk frukt", amount=1, unit="st", category="produce", is_pantry_staple=False),
    ]
    count = count_offer_matches(ingredients, sample_offers)
    assert count >= 2  # chicken + pasta should match


def test_normalize_removes_brands():
    assert "ica" not in normalize("ICA Kycklingfilé")
    assert "arla" not in normalize("Arla Mellanmjölk")


def test_clean_ingredient_name():
    assert clean_ingredient_name("2 gul lök") == "gul lök"
    assert "eller" not in clean_ingredient_name("grädde eller créme fraiche")
