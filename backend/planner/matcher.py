"""Match recipe ingredients to store offers using fuzzy text matching."""

import logging
import re
from difflib import SequenceMatcher

from backend.models.offer import Offer
from backend.models.recipe import Ingredient

logger = logging.getLogger(__name__)

# Normalized names: map common ingredient terms to canonical forms
# These help bridge the gap between recipe language and offer language
SYNONYMS = {
    "kycklingfilé": ["kyckling", "kycklingfile", "kycklingbröst"],
    "nötfärs": ["färs", "blandfärs", "nötfärs", "köttfärs"],
    "falukorv": ["falukorv", "korv"],
    "laxfilé": ["lax", "laxfile"],
    "fläskfilé": ["fläskfile", "fläsk"],
    "fläskkarré": ["karré", "fläskkarré"],
    "pasta": ["spaghetti", "penne", "fusilli", "tagliatelle", "makaroner"],
    "grädde": ["vispgrädde", "matlagningsgrädde", "matgrädde"],
    "krossade tomater": ["krossade tomater", "tomater krossade"],
    "ris": ["ris", "jasminris", "basmatiris"],
    "potatis": ["potatis", "fast potatis", "mjölig potatis"],
    "lök": ["gul lök", "lök", "gullök"],
    "broccoli": ["broccoli"],
    "ost": ["riven ost", "hushållsost", "prästost", "herrgård"],
    "smör": ["smör", "bregott"],
    "mjölk": ["mjölk", "helmjölk", "mellanmjölk", "lättmjölk"],
    "gräddfil": ["gräddfil", "crème fraiche"],
    "bacon": ["bacon", "sidfläsk"],
    "ägg": ["ägg"],
    "tomatpuré": ["tomatpuré"],
    "yoghurt": ["yoghurt", "turkisk yoghurt", "naturell yoghurt"],
    "kvarg": ["kvarg"],
    "chorizo": ["chorizo"],
    "torsk": ["torsk", "torskfilé"],
}


def normalize(text: str) -> str:
    """Lowercase, strip, remove common filler words."""
    text = text.lower().strip()
    # Remove brand-like prefixes and packaging info
    text = re.sub(r'\b(ica|arla|scan|kronfågel|felix|findus)\b', '', text)
    # Remove weight/volume info
    text = re.sub(r'\d+\s*(g|kg|ml|cl|dl|l)\b', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_ingredient_name(name: str) -> str:
    """Clean ingredient name by removing amounts, alternatives, and filler."""
    name = name.lower().strip()
    # Remove leading amounts like "1 gul lök" -> "gul lök"
    name = re.sub(r'^\d+[\s/½¼¾]*\s*', '', name)
    # Remove parenthetical info
    name = re.sub(r'\(.*?\)', '', name)
    # Split on "eller" and take first option
    if " eller " in name:
        name = name.split(" eller ")[0].strip()
    # Remove "à X g" type packaging info
    name = re.sub(r'\bà\s*\d+.*$', '', name)
    # Remove "förp" prefix
    name = re.sub(r'^\d*\s*förp\s*', '', name)
    return name.strip()


def get_canonical_names(ingredient_name: str) -> list[str]:
    """Get all name variants for an ingredient."""
    name_lower = clean_ingredient_name(ingredient_name)
    names = [name_lower]

    for canonical, variants in SYNONYMS.items():
        if name_lower in variants or canonical in name_lower:
            names.extend(variants)
            names.append(canonical)
        for v in variants:
            if v in name_lower or name_lower in v:
                names.extend(variants)
                names.append(canonical)
                break

    return list(set(names))


def similarity(a: str, b: str) -> float:
    """Calculate string similarity between two normalized strings."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _word_match(ingredient_words: set[str], offer_words: set[str]) -> float:
    """Check if key words from the ingredient appear in the offer."""
    if not ingredient_words or not offer_words:
        return 0.0
    # Filter out very short words (< 4 chars) to avoid false matches
    sig_ingredient = {w for w in ingredient_words if len(w) >= 4}
    if not sig_ingredient:
        sig_ingredient = ingredient_words
    overlap = sig_ingredient & offer_words
    if overlap:
        return len(overlap) / len(sig_ingredient)
    return 0.0


def match_ingredient_to_offers(
    ingredient: Ingredient,
    offers: list[Offer],
    threshold: float = 0.55,
) -> Offer | None:
    """Find the best matching offer for an ingredient.

    Uses word-level matching to avoid false positives from fuzzy matching.
    Returns the best matching Offer or None if no good match found.
    """
    if ingredient.is_pantry_staple:
        return None

    candidate_names = get_canonical_names(ingredient.name)
    best_match: Offer | None = None
    best_score: float = 0.0

    for offer in offers:
        offer_name = normalize(offer.product_name)
        offer_words = set(offer_name.split())

        for name in candidate_names:
            name_norm = normalize(name)
            if len(name_norm) < 3:
                continue

            name_words = set(name_norm.split())

            # Strategy 1: Word overlap
            word_score = _word_match(name_words, offer_words)

            # Strategy 2: Substring containment (whole canonical name in offer or vice versa)
            if len(name_norm) >= 4 and name_norm in offer_name:
                word_score = max(word_score, 0.9)
            elif len(offer_name) >= 4 and offer_name in name_norm:
                word_score = max(word_score, 0.85)

            # Strategy 3: Exact match
            if name_norm == offer_name:
                word_score = 1.0

            # Category match bonus / mismatch penalty
            # Only apply penalty for weak matches (not substring/exact)
            if ingredient.category == offer.category and ingredient.category != "other":
                word_score += 0.1
            elif word_score < 0.85 and (
                ingredient.category != "other"
                and offer.category != "other"
                and ingredient.category != offer.category
            ):
                word_score *= 0.5

            if word_score > best_score:
                best_score = word_score
                best_match = offer

    if best_score >= threshold:
        logger.debug(
            f"Matched '{ingredient.name}' -> '{best_match.product_name}' "
            f"(score={best_score:.2f})"
        )
        return best_match

    return None


def match_recipe_to_offers(
    ingredients: list[Ingredient],
    offers: list[Offer],
) -> list[tuple[Ingredient, Offer | None]]:
    """Match all ingredients in a recipe to available offers."""
    return [
        (ing, match_ingredient_to_offers(ing, offers))
        for ing in ingredients
    ]


def count_offer_matches(
    ingredients: list[Ingredient],
    offers: list[Offer],
) -> int:
    """Count how many ingredients in a recipe match current offers."""
    return sum(
        1
        for ing in ingredients
        if not ing.is_pantry_staple and match_ingredient_to_offers(ing, offers) is not None
    )
