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
    "kycklingfilé": ["kyckling", "kycklingfile", "kycklingbröst", "kycklingfilé"],
    "nötfärs": ["nötfärs", "köttfärs", "blandfärs", "färs"],
    "fläskfärs": ["fläskfärs"],
    "falukorv": ["falukorv", "korv"],
    "laxfilé": ["lax", "laxfile", "laxfilé"],
    "fläskfilé": ["fläskfile", "fläskfilé", "fläsk filé"],
    "fläskkarré": ["fläskkarré", "fläsk karré"],
    "pasta": ["spaghetti", "penne", "fusilli", "tagliatelle", "makaroner"],
    "grädde": ["vispgrädde", "matlagningsgrädde", "matgrädde", "grädde"],
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

# Ingredients that should NOT match offers — sauces, condiments, and items
# where partial word overlap causes false positives
NON_MATCHABLE_INGREDIENTS = {
    "ostronsås", "sojasås", "worcestershiresås", "hoisinsås", "tabasco",
    "sesamolja", "rapsolja", "olivolja", "kokosmjölk",
    "hasselnötter", "rostade hasselnötter", "valnötter", "cashewnötter",
    "jordnötter", "mandel", "pistage",
    "kycklinglever", "kycklingfond",
}


# Offers that should NEVER match recipe ingredients
# These are non-cooking items that cause false positives
NON_COOKING_OFFERS = {
    "läsk", "coca-cola", "pepsi", "fanta", "sprite", "7up",
    "godis", "chips", "snacks", "tuggummi",
    "toapapper", "hushållspapper", "diskmedel", "tvättmedel",
    "schampo", "tandkräm", "tvål", "blöja", "servett",
    "saft", "juice", "smoothie", "energidryck",
    "kaffe", "te ",
    "glass",
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
    # Remove leading amounts like "1 gul lök", "2 - 2 1/2 dl riven ost"
    name = re.sub(r'^[\d\s/½¼¾\-,\.]+(?:dl|cl|ml|l|g|kg|msk|tsk|st|krm|port)\s+', '', name)
    name = re.sub(r'^[\d/½¼¾\-]+\s+', '', name)
    name = re.sub(r'^\d+\s*', '', name)
    # Remove parenthetical info like "(à 500 g)", "(ca 1 kg)"
    name = re.sub(r'\(.*?\)', '', name)
    # Remove "att steka i", "till servering", etc.
    name = re.sub(r'\s+att\s+.*$', '', name)
    name = re.sub(r'\s+till\s+.*$', '', name)
    name = re.sub(r'\s+för\s+.*$', '', name)
    # Split on "eller" and take first option
    if " eller " in name:
        name = name.split(" eller ")[0].strip()
    # Remove "à X g" type packaging info
    name = re.sub(r'\bà\s*\d+.*$', '', name)
    # Remove "gärna ..." qualifiers
    name = re.sub(r'\s*gärna\s+.*$', '', name)
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


# Pre-indexed offers for fast lookup
_offer_index: dict[str, list[Offer]] = {}
_offer_index_hash: str = ""


def _build_offer_index(offers: list[Offer]) -> dict[str, list[Offer]]:
    """Build keyword index for fast offer lookup."""
    global _offer_index, _offer_index_hash
    h = f"{len(offers)}:{offers[0].id if offers else ''}"
    if h == _offer_index_hash:
        return _offer_index

    index: dict[str, list[Offer]] = {"__all__": offers}
    for offer in offers:
        name = normalize(offer.product_name)
        for word in name.split():
            if len(word) >= 3:
                if word not in index:
                    index[word] = []
                index[word].append(offer)
        # Also index by category
        cat = offer.category
        cat_key = f"__cat_{cat}"
        if cat_key not in index:
            index[cat_key] = []
        index[cat_key].append(offer)

    _offer_index = index
    _offer_index_hash = h
    return index


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

    # Skip ingredients known to cause false positives
    cleaned = clean_ingredient_name(ingredient.name)
    if cleaned in NON_MATCHABLE_INGREDIENTS:
        return None

    candidate_names = get_canonical_names(ingredient.name)
    best_match: Offer | None = None
    best_score: float = 0.0

    # Use index to narrow search when there are many offers
    if len(offers) > 20:
        index = _build_offer_index(offers)
        candidate_offer_ids = set()
        for name in candidate_names:
            for word in normalize(name).split():
                if len(word) >= 3 and word in index:
                    candidate_offer_ids.update(id(o) for o in index[word])
        # Also include same-category offers
        cat_key = f"__cat_{ingredient.category}"
        if cat_key in index:
            candidate_offer_ids.update(id(o) for o in index[cat_key])
        # If candidates found, use them; otherwise all offers
        search_offers = [o for o in offers if id(o) in candidate_offer_ids] if candidate_offer_ids else offers
    else:
        search_offers = offers

    for offer in search_offers:
        offer_name = normalize(offer.product_name)
        offer_words = set(offer_name.split())

        # Skip non-cooking offers (läsk, godis, toapapper, etc.)
        # Use word-boundary check to avoid blocking "fläsk" when blocking "läsk"
        if any(
            offer_name == block or
            offer_name.startswith(block + " ") or
            " " + block in offer_name
            for block in NON_COOKING_OFFERS
        ):
            continue

        for name in candidate_names:
            name_norm = normalize(name)
            if len(name_norm) < 3:
                continue

            name_words = set(name_norm.split())

            # Strategy 1: Word overlap
            word_score = _word_match(name_words, offer_words)

            # Strategy 2: Substring containment (whole canonical name in offer or vice versa)
            # Require minimum 5 chars to avoid "läsk" matching "fläsk" etc.
            if len(name_norm) >= 5 and name_norm in offer_name:
                word_score = max(word_score, 0.9)
            elif len(offer_name) >= 5 and offer_name in name_norm:
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


# Global match cache — cleared when offers change
_match_cache: dict[str, Offer | None] = {}
_match_cache_offer_hash: str = ""


def _get_offer_hash(offers: list[Offer]) -> str:
    return f"{len(offers)}:{offers[0].id if offers else ''}"


def _get_cached_match(ingredient: Ingredient, offers: list[Offer]) -> tuple[bool, Offer | None]:
    """Check cache. Returns (found_in_cache, result)."""
    global _match_cache, _match_cache_offer_hash
    offer_hash = _get_offer_hash(offers)
    if offer_hash != _match_cache_offer_hash:
        _match_cache = {}
        _match_cache_offer_hash = offer_hash

    cache_key = f"{ingredient.name}:{ingredient.category}"
    if cache_key in _match_cache:
        return True, _match_cache[cache_key]
    return False, None


def _set_cached_match(ingredient: Ingredient, result: Offer | None):
    cache_key = f"{ingredient.name}:{ingredient.category}"
    _match_cache[cache_key] = result


def match_ingredient_to_offers_cached(
    ingredient: Ingredient,
    offers: list[Offer],
    threshold: float = 0.55,
) -> Offer | None:
    """Cached version of match_ingredient_to_offers."""
    found, cached = _get_cached_match(ingredient, offers)
    if found:
        return cached
    result = match_ingredient_to_offers(ingredient, offers, threshold)
    _set_cached_match(ingredient, result)
    return result


def match_recipe_to_offers(
    ingredients: list[Ingredient],
    offers: list[Offer],
) -> list[tuple[Ingredient, Offer | None]]:
    """Match all ingredients in a recipe to available offers."""
    return [
        (ing, match_ingredient_to_offers_cached(ing, offers))
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
        if not ing.is_pantry_staple and match_ingredient_to_offers_cached(ing, offers) is not None
    )
