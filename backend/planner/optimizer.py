"""AI-driven menu optimization — uses free AI (Cloudflare) with Claude fallback."""

import hashlib
import json
import logging
import uuid
from datetime import datetime

# Cache: hash of (prefs + week + offers) → WeeklyMenu
_menu_generation_cache: dict[str, "WeeklyMenu"] = {}
_MENU_CACHE_MAX = 50

from backend.config import get_settings
from backend.planner.ai_provider import call_ai, parse_json_response
from backend.models.menu import PlannedMeal, WeeklyMenu
from backend.models.offer import Offer
from backend.models.recipe import Ingredient, Recipe
from backend.models.shopping_list import ShoppingItem, ShoppingList
from backend.models.user_prefs import UserPreferences
from backend.planner.matcher import count_offer_matches, match_ingredient_to_offers
from backend.planner.savings import calculate_meal_cost

logger = logging.getLogger(__name__)

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Pork-related ingredient keywords for filtering
PORK_KEYWORDS = [
    "fläsk", "bacon", "skinka", "sidfläsk", "kassler", "chorizo",
    "pancetta", "prosciutto", "salami", "fläskkarré", "fläskfilé",
    "revbensspjäll", "griskött", "kotlett",
]

# Lactose-free safe dairy (low/no lactose)
LACTOSE_SAFE_DAIRY = [
    "smör", "bregott", "parmesan", "parmesanost", "gruyère", "cheddar",
    "emmentaler", "grevé", "prästost", "herrgård", "hushållsost",
    "mozzarella", "cream cheese", "crème fraiche", "gräddfil",
    "laktosfri", "ägg",
]

# Processed food indicators
PROCESSED_KEYWORDS = [
    "färdigrätt", "pulver", "snabbmat", "korv", "falukorv", "nuggets",
    "fish fingers", "panerad", "halvfabrikat", "grillkorv", "chips",
]

# Minimum crowd rating — only serve top-tier recipes
MIN_RATING_THRESHOLD = 3.5
MIN_RATING_COUNT = 5


MENU_SYSTEM_PROMPT = """Du är en svensk menyplanerare. Din uppgift är att skapa en veckomeny
som maximerar användningen av butikens veckoerrbjudanden.

REGLER:
1. KAMPANJVAROR ÄR KÄRNAN — välj recept där huvudingrediensen (kött/fisk/protein) är på erbjudande
2. Prioritera recept med högt crowd-betyg OCH erbjudande-matchningar
3. Om användaren valt "bästa köp", MÅSTE minst hälften av recepten använda dessa ingredienser
4. Variera proteinkällor (inte kyckling varje dag)
5. DELA INGREDIENSER mellan recept för att minska svinn och sänka kostnad (t.ex. om 2 recept använder grädde köper man bara 1 förpackning)
6. Om ett erbjudande är "2 för X kr" — försök hitta 2 recept som BÅDA använder den ingrediensen, så inget slängs
7. Respektera tidsmixen (t.ex. 2 snabba + 3 längre)
8. Respektera kostval och livsstilspreferenser
9. Om hushållet har barn, prioritera barnvänliga rätter
10. Håll dig inom budget om angiven
11. Om receptet saknar tydliga tillbehör (bara kött/fisk utan potatis/ris/pasta), föreslå tillbehör i "side_suggestion"
12. ALDRIG föreslå ett recept som gör något från grunden om samma produkt finns som färdigvara på erbjudande

DAGKONTEXT (anpassa rätter till vardagar vs helg):
- Måndag-torsdag: Vardagsrätter, snabbare, enklare
- Fredag: Fredagsmys — tacos, pizza, hamburgare, fish & chips
- Lördag-söndag: Helgmiddagar — längre tillagning, festligare

Du MÅSTE välja recept-ID:n från listan. Hitta INTE på egna.

SVARSFORMAT (strikt JSON, ingen annan text):
{
  "meals": [
    {
      "day": "monday",
      "recipe_id": "ica-123456",
      "reasoning": "Kort motivering",
      "mealprep_tip": "Valfritt tips, t.ex. 'Gör dubbelsats och frys in halva'",
      "side_suggestion": "Valfritt tillbehörsförslag, t.ex. 'Servera med kokt potatis och lingon'"
    }
  ]
}"""

SWAP_SYSTEM_PROMPT = """Du är en svensk menyplanerare. Användaren vill byta ut ett recept.
Föreslå ETT alternativt recept som:
- Fortfarande utnyttjar veckans erbjudanden
- Är annorlunda i smak/stil jämfört med resten av menyn
- Passar användarens preferenser

SVARSFORMAT (strikt JSON, ingen annan text):
{
  "recipe_id": "ica-123456",
  "reasoning": "Kort motivering"
}"""


def _is_pork_ingredient(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in PORK_KEYWORDS)


def _is_lactose_safe(name: str) -> bool:
    name_lower = name.lower()
    return any(safe in name_lower for safe in LACTOSE_SAFE_DAIRY)


def _is_processed(recipe: Recipe) -> bool:
    """Check if a recipe likely contains processed food."""
    for ing in recipe.ingredients:
        if any(kw in ing.name.lower() for kw in PROCESSED_KEYWORDS):
            return True
    return False


def _is_poorly_rated(recipe: Recipe) -> bool:
    """Check if a recipe has enough ratings to be considered poorly rated."""
    if recipe.rating is not None and recipe.rating_count is not None:
        if recipe.rating_count >= MIN_RATING_COUNT and recipe.rating < MIN_RATING_THRESHOLD:
            return True
    return False


def _get_crowd_rating(recipe: Recipe) -> float:
    """Get the crowd rating, or 0 if not available."""
    return recipe.rating if recipe.rating is not None else 0.0


# Skip these — not complete dinners
INCOMPLETE_RECIPE_KEYWORDS = [
    "grundrecept", "bas ", "basen", "sås till", "dressing",
    "marinad", "smör till", "topping", "tillbehör",
]


CARB_SOURCES = [
    "potatis", "ris", "pasta", "spaghetti", "penne", "bulgur", "couscous",
    "bröd", "tortilla", "wrap", "nudlar", "gnocchi", "polenta", "quinoa",
    "tacos", "pizza", "pie", "paj", "gratäng", "lasagne", "risotto",
]

def _is_incomplete_recipe(recipe: Recipe) -> bool:
    """Check if a recipe is just a component, not a full dinner."""
    title_lower = recipe.title.lower()
    if any(kw in title_lower for kw in INCOMPLETE_RECIPE_KEYWORDS):
        return True
    # Skip single-serving recipes (sallader, mellanmål) — they scale badly
    if recipe.servings and recipe.servings <= 1:
        return True
    real_ingredients = [i for i in recipe.ingredients if not i.is_pantry_staple]
    if len(real_ingredients) < 3:
        return True
    # Check if it has a carb source or is self-contained (soup, stew, salad)
    all_text = f"{title_lower} {' '.join(i.name.lower() for i in recipe.ingredients)}"
    has_carb = any(c in all_text for c in CARB_SOURCES)
    is_selfcontained = any(kw in title_lower for kw in ['soppa', 'gryta', 'wok', 'sallad', 'bowl', 'burrito', 'kebab', 'pannkak', 'omelett', 'paj', 'gratäng', 'lasagne', 'risotto', 'curry'])
    if not has_carb and not is_selfcontained and len(real_ingredients) < 6:
        return True
    return False


# Ready-made products — if these are on offer, don't suggest recipes that MAKE them
# Instead, we want recipes that USE them (e.g. "köttbullar med potatismos", not "hemmagjorda köttbullar")
READY_MADE_KEYWORDS = [
    "köttbullar", "fiskpinnar", "fiskbullar", "nuggets", "falafel",
    "korv", "falukorv", "grillkorv", "prinskorv",
    "pizza", "piroger", "vårrullar", "kroppkakor",
    "pannkakor", "plättar", "blini",
]


def _recipe_makes_ready_made(recipe: Recipe, offers: list[Offer]) -> bool:
    """Check if a recipe makes something from scratch that's available ready-made.

    E.g., if "Frysta köttbullar" is on offer, skip "Klassiska köttbullar" (recipe
    that makes köttbullar from färs+ströbröd+ägg). Instead prefer recipes that
    SERVE köttbullar (like "köttbullar med potatismos").
    """
    title_lower = recipe.title.lower()

    for keyword in READY_MADE_KEYWORDS:
        if keyword not in title_lower:
            continue

        # Check if any offer IS this ready-made product
        offer_has_readymade = any(
            keyword in o.product_name.lower() and (
                "fryst" in o.product_name.lower() or
                "färdig" in o.product_name.lower() or
                o.category in ("frozen", "other") or
                # The offer is the product itself (not raw ingredient)
                not any(raw in o.product_name.lower() for raw in ["färs", "filé", "bröst", "lår", "bog"])
            )
            for o in offers
        )

        if not offer_has_readymade:
            continue

        # This recipe has the keyword AND the offer has the ready-made version
        # Check if the recipe MAKES it from scratch (has raw ingredients like färs, ägg, ströbröd)
        ingredient_names = " ".join(i.name.lower() for i in recipe.ingredients)
        makes_from_scratch = sum(1 for raw in ["färs", "ströbröd", "ägg", "mjöl", "deg", "jäst"]
                                  if raw in ingredient_names)
        if makes_from_scratch >= 2:
            return True

    return False


def filter_recipes_by_preferences(
    recipes: list[Recipe], prefs: UserPreferences
) -> list[Recipe]:
    """Filter recipes based on user preferences."""
    filtered = []
    for r in recipes:
        # Skip incomplete recipes (grundrecept, sauces, etc.)
        if _is_incomplete_recipe(r):
            continue
        # Dietary restrictions
        if "vegetarian" in prefs.dietary_restrictions:
            if any(i.category == "meat" for i in r.ingredients):
                continue
        if "vegan" in prefs.dietary_restrictions:
            if any(i.category in ("meat", "fish", "dairy") for i in r.ingredients):
                continue
        if "glutenfree" in prefs.dietary_restrictions:
            if "glutenfree" not in r.diet_labels and any(
                "mjöl" in i.name.lower() or "pasta" in i.name.lower() or "bröd" in i.name.lower()
                for i in r.ingredients
            ):
                continue
        if "dairyfree" in prefs.dietary_restrictions:
            if any(i.category == "dairy" and i.name.lower() not in ("ägg",) for i in r.ingredients):
                continue
        if "lactosefree" in prefs.dietary_restrictions:
            if any(
                i.category == "dairy" and not _is_lactose_safe(i.name)
                for i in r.ingredients
            ):
                continue
        if "porkfree" in prefs.dietary_restrictions:
            if any(_is_pork_ingredient(i.name) for i in r.ingredients):
                continue

        # Lifestyle: avoid processed
        if "avoid_processed" in prefs.lifestyle_preferences:
            if _is_processed(r):
                continue

        # Disliked ingredients
        if prefs.disliked_ingredients:
            disliked = {d.lower() for d in prefs.disliked_ingredients}
            if any(
                any(d in i.name.lower() for d in disliked)
                for i in r.ingredients
            ):
                continue

        # Max cook time (if no time_mix, use max_cook_time)
        if not prefs.time_mix and prefs.max_cook_time and r.cook_time_minutes > prefs.max_cook_time:
            continue

        # Skip poorly rated recipes (only if enough ratings exist)
        if _is_poorly_rated(r):
            continue

        filtered.append(r)

    return filtered


def format_offers_for_prompt(offers: list[Offer], pinned_ids: list[str] = None) -> str:
    lines = []
    for o in offers:
        savings = ""
        if o.original_price:
            pct = int((1 - o.offer_price / o.original_price) * 100)
            savings = f" (-{pct}%)"
        deal = f" [{o.quantity_deal}]" if o.quantity_deal else ""
        pinned = " ★ BÄSTA KÖP — användaren vill använda denna" if pinned_ids and o.id in pinned_ids else ""
        lines.append(
            f"- {o.product_name} ({o.brand or '-'}): {o.offer_price} {o.unit}{deal}{savings} [{o.category}]{pinned}"
        )
    return "\n".join(lines)


def _score_recipe(recipe: Recipe, offer_matches: int, lifestyle: list[str] = None) -> float:
    """Combined score: offer matches + crowd rating + nutrition bonus."""
    score = offer_matches * 2.0
    if recipe.rating and recipe.rating_count:
        confidence = min(1.0, recipe.rating_count / 100)
        score += recipe.rating * confidence
        if recipe.rating >= 4.0 and recipe.rating_count >= 50:
            score += 2.0  # "Familjefavorit" bonus
    # Nutrition bonus for lifestyle preferences
    if lifestyle and recipe.nutrition:
        if 'prefer_highprotein' in lifestyle and recipe.nutrition.protein and recipe.nutrition.protein > 30:
            score += 1.5
        if 'prefer_lowcarb' in lifestyle and recipe.nutrition.carbohydrates and recipe.nutrition.carbohydrates < 20:
            score += 1.5
        if 'prefer_healthy' in lifestyle and recipe.nutrition.calories and recipe.nutrition.calories < 500:
            score += 1.0
    return score


def build_match_cache(recipes: list[Recipe], offers: list[Offer]) -> dict[str, int]:
    """Cache offer match counts to avoid recomputation."""
    return {r.id: count_offer_matches(r.ingredients, offers) for r in recipes}


def format_recipes_for_prompt(recipes: list[Recipe], offers: list[Offer], match_cache: dict[str, int] = None) -> str:
    scored = []
    for r in recipes:
        matches = match_cache[r.id] if match_cache and r.id in match_cache else count_offer_matches(r.ingredients, offers)
        combined = _score_recipe(r, matches)
        scored.append((r, matches, combined))
    scored.sort(key=lambda x: -x[2])

    lines = []
    for r, matches, _ in scored[:60]:
        tags = ", ".join(r.tags) if r.tags else ""
        diet = ", ".join(r.diet_labels) if r.diet_labels else ""
        key_ings = [i.name for i in r.ingredients if not i.is_pantry_staple][:5]
        rating_str = f" | Betyg: {r.rating}/5 ({r.rating_count} röster)" if r.rating else ""
        nutr_str = ""
        if r.nutrition and r.nutrition.calories:
            nutr_str = f" | {r.nutrition.calories} kcal"
            if r.nutrition.protein:
                nutr_str += f", {r.nutrition.protein}g protein"
        lines.append(
            f"- ID: {r.id} | {r.title} | {r.cook_time_minutes} min | "
            f"{r.difficulty} | Erbjudande: {matches}{rating_str}{nutr_str} | "
            f"Ingredienser: {', '.join(key_ings)} | Tags: {tags} {diet}"
        )
    return "\n".join(lines)


def format_preferences_for_prompt(prefs: UserPreferences) -> str:
    lines = [
        f"Hushållsstorlek: {prefs.household_size} personer",
        f"Antal middagar: {prefs.num_dinners}",
    ]
    if prefs.has_children:
        lines.append("Hushållet har barn — prioritera barnvänliga rätter")
    if prefs.budget_per_week:
        lines.append(f"Veckobudget: {prefs.budget_per_week} kr")

    # Time mix
    if prefs.time_mix:
        tm = prefs.time_mix
        parts = []
        if tm.quick_count > 0:
            parts.append(f"{tm.quick_count} snabba (≤30 min)")
        if tm.medium_count > 0:
            parts.append(f"{tm.medium_count} medel (31-45 min)")
        if tm.slow_count > 0:
            parts.append(f"{tm.slow_count} längre (46+ min)")
        if parts:
            lines.append(f"Tidsmix: {', '.join(parts)}")
    elif prefs.max_cook_time:
        lines.append(f"Max tillagningstid: {prefs.max_cook_time} min")

    if prefs.dietary_restrictions:
        lines.append(f"Kostval: {', '.join(prefs.dietary_restrictions)}")
    if prefs.lifestyle_preferences:
        label_map = {
            "avoid_processed": "Undvik processad mat",
            "prefer_healthy": "Hälsosammare val (mer grönt, fullkorn, bra fetter)",
            "prefer_highprotein": "Proteinrikt (extra protein varje måltid)",
            "prefer_lowcarb": "Lågkolhydrat (mindre pasta, ris, bröd)",
            "prefer_sustainable": "Klimatsmart/hållbart (mer växtbaserat)",
            "prefer_seasonal": "Säsongsanpassat (ingredienser i säsong)",
            "prefer_organic": "Föredra ekologiskt",
            "reduce_waste": "Minska matsvinn (återanvänd ingredienser mellan dagar i veckan)",
        }
        labels = [label_map.get(p, p) for p in prefs.lifestyle_preferences]
        lines.append(f"Livsstil: {', '.join(labels)}")
    if prefs.disliked_ingredients:
        lines.append(f"Undvik: {', '.join(prefs.disliked_ingredients)}")
    if prefs.pinned_offer_ids:
        lines.append(f"Användaren har valt {len(prefs.pinned_offer_ids)} bästa köp — bygg menyn kring dessa!")
    if prefs.selected_days:
        day_names = {"monday": "mån", "tuesday": "tis", "wednesday": "ons", "thursday": "tor", "friday": "fre", "saturday": "lör", "sunday": "sön"}
        days = [day_names.get(d, d) for d in prefs.selected_days]
        lines.append(f"Specifika dagar: {', '.join(days)}")
    return "\n".join(lines)


def generate_fallback_menu(
    offers: list[Offer],
    recipes: list[Recipe],
    preferences: UserPreferences,
) -> tuple[dict, bool]:
    """Pick top recipes by combined score with randomization.
    Returns (menu_data, is_fallback)."""
    import random
    scored = []
    for r in recipes:
        matches = count_offer_matches(r.ingredients, offers)
        score = _score_recipe(r, matches)
        scored.append((r, score))
    scored.sort(key=lambda x: -x[1])

    # Take top 6x candidates for a wider pool, then enforce variety
    pool_size = min(len(scored), preferences.num_dinners * 6)
    pool = scored[:pool_size]
    random.shuffle(pool)

    # Classify each recipe by its primary protein — search ALL ingredients
    def _primary_protein(recipe):
        all_names = " ".join(i.name.lower() for i in recipe.ingredients)
        # Check specific proteins first (order matters: most specific first)
        if 'kyckling' in all_names: return 'kyckling'
        if 'lax' in all_names: return 'lax'
        if any(x in all_names for x in ['nötfärs', 'köttfärs', 'blandfärs', 'kycklingfärs']): return 'färs'
        if 'fläsk' in all_names: return 'fläsk'
        if 'torsk' in all_names: return 'torsk'
        if 'korv' in all_names or 'falukorv' in all_names: return 'korv'
        if 'räk' in all_names: return 'räkor'
        if 'biff' in all_names or 'entrecôte' in all_names or 'oxfilé' in all_names: return 'nötkött'
        if 'lamm' in all_names: return 'lamm'
        if 'tofu' in all_names or 'bönor' in all_names or 'linser' in all_names or 'kikärt' in all_names: return 'veg-protein'
        # Fallback: check categories
        if any(i.category == 'meat' for i in recipe.ingredients): return 'övrigt-kött'
        if any(i.category == 'fish' for i in recipe.ingredients): return 'övrigt-fisk'
        return 'vegetarisk'

    # Build ingredient fingerprint for overlap scoring (reduce waste)
    def _ingredient_set(recipe):
        return {i.name.lower().split()[0] for i in recipe.ingredients
                if not i.is_pantry_staple and len(i.name) > 2}

    def _overlap_bonus(recipe, selected_recipes):
        """Bonus for sharing ingredients with already-selected recipes."""
        if not selected_recipes:
            return 0
        recipe_ings = _ingredient_set(recipe)
        selected_ings = set()
        for sr in selected_recipes:
            selected_ings.update(_ingredient_set(sr))
        shared = recipe_ings & selected_ings
        return len(shared) * 0.5  # 0.5 points per shared ingredient

    selected = []
    used_ids = set()
    used_proteins = []
    used_title_words = set()  # Prevent "broccolipaj" + "broccolipaj med ost"

    def _title_fingerprint(recipe):
        """Key words from title for duplicate detection."""
        stop = {'med', 'och', 'i', 'på', 'till', 'för', 'en', 'ett', 'den', 'det'}
        return {w for w in recipe.title.lower().split() if len(w) >= 4 and w not in stop}

    def _too_similar(recipe):
        """Block recipes with >50% title word overlap with selected."""
        if not used_title_words:
            return False
        words = _title_fingerprint(recipe)
        if not words:
            return False
        overlap = words & used_title_words
        return len(overlap) / len(words) > 0.5

    # Pre-compute cost per portion for pool — skip outrageously expensive
    from backend.planner.savings import calculate_meal_cost
    MAX_PRICE_PER_PORTION = 100  # kr — no recipe should cost more than this per person

    pool_with_cost = []
    for r, score in pool:
        scale = _get_servings_scale(r, preferences.household_size)
        cost_w, _, _ = calculate_meal_cost(r.ingredients, offers, scale)
        pp = cost_w / max(1, preferences.household_size)
        if pp > MAX_PRICE_PER_PORTION:
            continue  # Skip absurdly expensive recipes
        pool_with_cost.append((r, score))

    # First pass: pick by score + overlap, block duplicates
    for round_num in range(preferences.num_dinners):
        best_candidate = None
        best_total_score = -1

        for r, base_score in pool_with_cost:
            if r.id in used_ids:
                continue
            if _too_similar(r):
                continue
            protein = _primary_protein(r)
            if used_proteins.count(protein) >= 2:
                continue
            if used_proteins and used_proteins[-1] == protein:
                continue

            overlap = _overlap_bonus(r, selected)
            total = base_score + overlap
            if total > best_total_score:
                best_total_score = total
                best_candidate = (r, protein)

        if best_candidate:
            r, protein = best_candidate
            selected.append(r)
            used_ids.add(r.id)
            used_proteins.append(protein)
            used_title_words.update(_title_fingerprint(r))
        else:
            break

    # If not enough after variety filter, fill from remaining (relax constraints)
    if len(selected) < preferences.num_dinners:
        for r, _ in pool:
            if r.id not in used_ids:
                selected.append(r)
                used_ids.add(r.id)
            if len(selected) >= preferences.num_dinners:
                break

    days = _get_days(preferences)

    return {
        "meals": [
            {
                "day": days[i] if i < len(days) else DAYS[i],
                "recipe_id": r.id,
                "reasoning": "Automatiskt vald baserat på erbjudanden",
                "mealprep_tip": "",
            }
            for i, r in enumerate(selected)
        ]
    }, True


def _get_days(preferences: UserPreferences) -> list[str]:
    """Get which days to assign meals to, starting from today."""
    if preferences.selected_days and len(preferences.selected_days) >= preferences.num_dinners:
        return preferences.selected_days[:preferences.num_dinners]
    # Start from today's weekday
    today_idx = datetime.now().weekday()  # 0=Monday
    remaining = [DAYS[i % 7] for i in range(today_idx, today_idx + 7)]
    return remaining[:preferences.num_dinners]


def _get_store_name(store_id: str) -> str:
    from backend.scrapers.store_registry import STORE_REGISTRY
    store = STORE_REGISTRY.get(store_id, {})
    return store.get("name", store_id)


def _get_servings_scale(recipe: Recipe, household_size: int) -> float:
    base = recipe.servings if recipe.servings and recipe.servings > 0 else 4
    return household_size / base


async def generate_menu(
    offers: list[Offer],
    recipes: list[Recipe],
    preferences: UserPreferences,
) -> WeeklyMenu:
    """Generate an optimized weekly menu using Claude."""
    import random
    settings = get_settings()
    now = datetime.now()

    eligible = filter_recipes_by_preferences(recipes, preferences)
    # Filter out recipes that make something from scratch when the ready-made is on offer
    eligible = [r for r in eligible if not _recipe_makes_ready_made(r, offers)]
    if not eligible:
        raise ValueError("Inga recept matchar dina preferenser. Prova att ändra kostval eller ta bort ingredienser du undviker.")

    match_cache = build_match_cache(eligible, offers)
    offers_text = format_offers_for_prompt(offers, preferences.pinned_offer_ids)
    recipes_text = format_recipes_for_prompt(eligible, offers, match_cache)
    prefs_text = format_preferences_for_prompt(preferences)

    # Identify pinned offers for response
    pinned_offers = [o for o in offers if o.id in preferences.pinned_offer_ids] if preferences.pinned_offer_ids else []

    # Smart fallback: use heuristic for simple requests (saves ~$0.03 per call)
    has_complex_prefs = (
        preferences.pinned_offer_ids
        or preferences.time_mix
        or preferences.lifestyle_preferences
        or preferences.has_children
        or preferences.budget_per_week
    )

    menu_data = None
    is_fallback = False

    if not has_complex_prefs:
        logger.info("Simple preferences — using fast heuristic (no AI cost)")
        menu_data, is_fallback = generate_fallback_menu(offers, eligible, preferences)

    if not menu_data:
        user_message = f"""Veckans erbjudanden:
{offers_text}

Tillgängliga recept (sorterade efter erbjudande-matchningar):
{recipes_text}

Användarens preferenser:
{prefs_text}

Skapa en veckomeny med {preferences.num_dinners} middagar.
Välj recept som maximerar erbjudande-matchningar och som varierar i stil.
Inkludera mealprep-tips där det passar (t.ex. "Gör dubbelsats och frys in halva")."""

        try:
            ai_text = await call_ai(
                system_prompt=MENU_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=2000,
                use_premium=has_complex_prefs,
            )
            if ai_text:
                menu_data = parse_json_response(ai_text)
        except Exception as e:
            logger.error(f"AI menu generation failed: {e}", exc_info=True)

    if not menu_data or not menu_data.get("meals"):
        logger.info("Using fallback menu generator")
        menu_data, is_fallback = generate_fallback_menu(offers, eligible, preferences)

    # Build the full WeeklyMenu from AI selections
    recipe_map = {r.id: r for r in eligible}
    days = _get_days(preferences)
    meals = []

    for i, meal_choice in enumerate(menu_data.get("meals", [])):
        recipe_id = meal_choice.get("recipe_id", "")
        recipe = recipe_map.get(recipe_id)
        if not recipe:
            logger.warning(f"AI returned unknown recipe_id: {recipe_id}")
            continue

        servings_scale = _get_servings_scale(recipe, preferences.household_size)
        day = meal_choice.get("day", days[i] if i < len(days) else f"day-{i}")
        reasoning = meal_choice.get("reasoning", "")
        mealprep_tip = meal_choice.get("mealprep_tip", "")
        side_suggestion = meal_choice.get("side_suggestion", "")
        cost_with, cost_without, matches = calculate_meal_cost(
            recipe.ingredients, offers, servings_scale
        )
        offer_matches = [offer for _, offer in matches if offer]
        seen_ids = set()
        unique_offers = []
        for o in offer_matches:
            if o.id not in seen_ids:
                seen_ids.add(o.id)
                unique_offers.append(o)

        # Build per-ingredient cost breakdown for transparency
        from backend.models.menu import CostDetail
        from backend.planner.savings import estimate_ingredient_cost
        cost_details = []
        for ing in recipe.ingredients:
            ing_offer = next((o for i, o in matches if i.name == ing.name), None)
            cost_w, cost_wo = estimate_ingredient_cost(ing, ing_offer, servings_scale)
            if cost_w > 0.5:  # Skip negligible items
                source = "skafferi" if ing.is_pantry_staple else ("erbjudande" if ing_offer else "uppskattad")
                cost_details.append(CostDetail(
                    ingredient=ing.name,
                    amount=round(ing.amount * servings_scale, 1),
                    unit=ing.unit,
                    cost=round(cost_w, 1),
                    source=source,
                ))

        meals.append(
            PlannedMeal(
                day=day,
                recipe=recipe,
                scaled_servings=preferences.household_size,
                offer_matches=unique_offers,
                estimated_cost=cost_with,
                estimated_cost_without_offers=cost_without,
                cost_details=cost_details,
                reasoning=reasoning,
                popularity_score=_get_crowd_rating(recipe),
                is_fallback=is_fallback,
                mealprep_tip=mealprep_tip,
                side_suggestion=side_suggestion,
            )
        )

    total_cost = sum(m.estimated_cost for m in meals)
    total_without = sum(m.estimated_cost_without_offers for m in meals)
    total_savings = max(0, total_without - total_cost)  # Clamp: never show negative savings
    savings_pct = (total_savings / total_without * 100) if total_without > 0 else 0

    # Split confirmed vs estimated savings (deduplicate offers across meals)
    confirmed = 0.0
    estimated = 0.0
    seen_offer_ids = set()
    for meal in meals:
        for offer in meal.offer_matches:
            if offer.id in seen_offer_ids:
                continue
            seen_offer_ids.add(offer.id)
            if offer.original_price:
                confirmed += max(0, offer.original_price - offer.offer_price)
            else:
                estimated += offer.offer_price * 0.3
    confirmed = round(confirmed, 2)
    estimated = round(estimated, 2)

    # Budget check
    budget_exceeded = False
    budget_exceeded_by = 0.0
    if preferences.budget_per_week and total_cost > preferences.budget_per_week:
        budget_exceeded = True
        budget_exceeded_by = round(total_cost - preferences.budget_per_week, 2)

    shopping_list = _build_shopping_list(meals, offers, preferences.household_size)

    now = datetime.now()
    # Build date range string and active filters for frontend
    from datetime import timedelta
    start_date = now.date()
    end_date = start_date + timedelta(days=preferences.num_dinners - 1)
    months_sv = {1:'jan',2:'feb',3:'mar',4:'apr',5:'maj',6:'jun',7:'jul',8:'aug',9:'sep',10:'okt',11:'nov',12:'dec'}
    date_range = f"{start_date.day} {months_sv[start_date.month]} – {end_date.day} {months_sv[end_date.month]}"

    filter_labels = {
        'vegetarian':'Vegetarisk','vegan':'Vegansk','glutenfree':'Glutenfri',
        'dairyfree':'Mjölkfri','lactosefree':'Laktosfri','porkfree':'Fläskfri',
    }
    active_filters = [filter_labels.get(d, d) for d in preferences.dietary_restrictions]
    if preferences.has_children:
        active_filters.append('Barnvänligt')

    menu = WeeklyMenu(
        id=str(uuid.uuid4())[:8],
        week_number=now.isocalendar()[1],
        year=now.year,
        store_id=preferences.store_id,
        store_name=_get_store_name(preferences.store_id),
        preferences=preferences,
        meals=meals,
        shopping_list=shopping_list,
        total_cost=round(total_cost, 2),
        total_cost_without_offers=round(total_without, 2),
        total_savings=round(total_savings, 2),
        savings_percentage=round(savings_pct, 1),
        generated_at=now.isoformat(),
        pinned_offers=pinned_offers,
        date_range=date_range,
        active_filters=active_filters,
        budget_exceeded=budget_exceeded,
        budget_exceeded_by=budget_exceeded_by,
        confirmed_savings=confirmed,
        estimated_savings=estimated,
    )

    return menu


async def swap_recipe(
    current_menu: WeeklyMenu,
    day: str,
    offers: list[Offer],
    recipes: list[Recipe],
    reason: str = "",
    chosen_recipe_id: str = "",
) -> PlannedMeal:
    """Swap out a recipe for a specific day.
    If chosen_recipe_id is given, use that directly (user picked from alternatives).
    Otherwise, ask AI for a suggestion.
    """
    current_recipe_ids = {m.recipe.id for m in current_menu.meals}
    eligible = [r for r in recipes if r.id not in current_recipe_ids]
    eligible = filter_recipes_by_preferences(eligible, current_menu.preferences)

    recipe_map = {r.id: r for r in eligible}
    recipe = None
    reasoning = ""

    # If user chose a specific recipe from alternatives
    if chosen_recipe_id and chosen_recipe_id in recipe_map:
        recipe = recipe_map[chosen_recipe_id]
        reasoning = "Vald av användaren"
    else:
        # Ask AI
        current_meal = next((m for m in current_menu.meals if m.day == day), None)
        current_title = current_meal.recipe.title if current_meal else "okänt"
        other_titles = [m.recipe.title for m in current_menu.meals if m.day != day]

        offers_text = format_offers_for_prompt(offers)
        recipes_text = format_recipes_for_prompt(eligible, offers)

        user_message = f"""Nuvarande recept på {day}: {current_title}
Anledning till byte: {reason or 'Vill ha något annat'}
Övriga rätter i menyn: {', '.join(other_titles)}

Veckans erbjudanden:
{offers_text}

Tillgängliga recept:
{recipes_text}

Föreslå ETT alternativt recept."""

        ai_text = await call_ai(
            system_prompt=SWAP_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=300,
            use_premium=False,
        )
        swap_data = parse_json_response(ai_text) if ai_text else {}

        recipe_id = swap_data.get("recipe_id", "")
        reasoning = swap_data.get("reasoning", "")
        recipe = recipe_map.get(recipe_id)

    if not recipe:
        import random
        scored = [(r, _score_recipe(r, count_offer_matches(r.ingredients, offers))) for r in eligible]
        scored.sort(key=lambda x: -x[1])
        pool = scored[:10]
        random.shuffle(pool)
        recipe = pool[0][0] if pool else eligible[0]
        reasoning = "Automatiskt vald"

    servings_scale = _get_servings_scale(recipe, current_menu.preferences.household_size)
    cost_with, cost_without, matches = calculate_meal_cost(
        recipe.ingredients, offers, servings_scale
    )
    offer_matches = list({o.id: o for _, o in matches if o}.values())

    # Build cost breakdown for transparency
    from backend.models.menu import CostDetail
    from backend.planner.savings import estimate_ingredient_cost
    cost_details = []
    for ing in recipe.ingredients:
        ing_offer = next((o for i, o in matches if i.name == ing.name), None)
        cost_w, _ = estimate_ingredient_cost(ing, ing_offer, servings_scale)
        if cost_w > 0.5:
            source = "skafferi" if ing.is_pantry_staple else ("erbjudande" if ing_offer else "uppskattad")
            cost_details.append(CostDetail(
                ingredient=ing.name,
                amount=round(ing.amount * servings_scale, 1),
                unit=ing.unit,
                cost=round(cost_w, 1),
                source=source,
            ))

    return PlannedMeal(
        day=day,
        recipe=recipe,
        scaled_servings=current_menu.preferences.household_size,
        offer_matches=offer_matches,
        estimated_cost=cost_with,
        estimated_cost_without_offers=cost_without,
        cost_details=cost_details,
        reasoning=reasoning,
        popularity_score=_get_crowd_rating(recipe),
    )



def _build_shopping_list(
    meals: list[PlannedMeal],
    offers: list[Offer],
    household_size: int,
) -> ShoppingList:
    from backend.planner.savings import estimate_ingredient_cost

    import re as _re
    aggregated: dict[str, dict] = {}

    # Things that are NOT ingredients
    NOT_INGREDIENTS = [
        'stektermometer', 'bakplåtspapper', 'plastfolie', 'aluminiumfolie',
        'grillspett', 'tandpetare', 'matlagningstermometer', 'ugnsform',
        'kastrull', 'stekpanna', 'mixer', 'stavmixer', 'bakform',
        'muffinsform', 'springform', 'plåt', 'folie', 'film',
        'gärna', 'eventuellt', 'garnering', 'till servering',
    ]

    def _is_not_ingredient(name: str) -> bool:
        n = name.lower()
        return any(kw in n for kw in NOT_INGREDIENTS)

    def _normalize_key(name: str) -> str:
        """Normalize ingredient name for deduplication."""
        n = name.lower().strip()
        n = _re.sub(r'^\d+[\s/½¼¾]*\s*', '', n)
        n = _re.sub(r'\(.*?\)', '', n)
        n = _re.sub(r'^(färsk|riven|kokt|strimla|hackad|tärnad|skivad)\s+', '', n)
        return n.strip()

    for meal in meals:
        servings_scale = _get_servings_scale(meal.recipe, household_size)
        for ing in meal.recipe.ingredients:
            if ing.is_pantry_staple:
                continue
            if _is_not_ingredient(ing.name):
                continue

            key = _normalize_key(ing.name)
            scaled_amount = ing.amount * servings_scale

            if key in aggregated:
                aggregated[key]["amount"] += scaled_amount
                aggregated[key]["price"] += estimate_ingredient_cost(ing, aggregated[key]["offer"], servings_scale)[0]
                if meal.recipe.title not in aggregated[key]["used_in"]:
                    aggregated[key]["used_in"].append(meal.recipe.title)
            else:
                offer = match_ingredient_to_offers(ing, offers)
                cost_with, cost_without = estimate_ingredient_cost(ing, offer, servings_scale)
                aggregated[key] = {
                    "name": ing.name,
                    "amount": scaled_amount,
                    "unit": ing.unit,
                    "category": ing.category,
                    "offer": offer,
                    "price": cost_with,
                    "used_in": [meal.recipe.title],
                }

    # Convert to shopping-friendly units
    def _shopping_amount(amount: float, unit: str, name: str) -> tuple[float, str]:
        """Convert recipe units to shopping-friendly units."""
        # Convert msk/tsk to grams (nobody buys "3 msk smör")
        if unit == 'msk':
            grams = amount * 15
            if grams >= 50:
                return round(grams / 25) * 25, 'g'  # Round to 25g
            return round(grams / 10) * 10, 'g'
        if unit == 'tsk':
            grams = amount * 5
            if grams >= 20:
                return round(grams / 10) * 10, 'g'
            return 0, ''  # Too small to list
        if unit == 'krm' or unit == 'nypa':
            return 0, ''  # Don't list
        # Round grams to kitchen-friendly
        if unit == 'g':
            if amount < 50:
                return round(amount / 10) * 10, 'g'
            if amount < 500:
                return round(amount / 25) * 25, 'g'
            return round(amount / 50) * 50, 'g'
        if unit == 'dl':
            return round(amount * 2) / 2, 'dl'  # Round to 0.5 dl
        if unit == 'st':
            return max(1, round(amount)), 'st'
        return round(amount, 1), unit

    items = []
    for data in aggregated.values():
        amount, unit = _shopping_amount(data["amount"], data["unit"], data["name"])
        if amount <= 0 and data["unit"] in ('krm', 'nypa', 'tsk', 'msk'):
            continue  # Skip tiny amounts
        items.append(
            ShoppingItem(
                ingredient_name=data["name"],
                total_amount=amount,
                unit=unit,
                category=data["category"],
                matched_offer=data["offer"],
                estimated_price=round(data["price"], 2),
                is_on_offer=data["offer"] is not None,
                used_in=data["used_in"],
            )
        )

    # Order matches ICA Maxi Boglundsängen, Örebro store layout
    category_order = ["bakery", "meat", "fish", "produce", "dairy", "pantry", "frozen", "other"]
    items.sort(key=lambda x: (category_order.index(x.category) if x.category in category_order else 99, x.ingredient_name))

    on_offer = sum(1 for i in items if i.is_on_offer)
    total_cost = sum(i.estimated_price for i in items)

    return ShoppingList(
        items=items,
        total_estimated_cost=round(total_cost, 2),
        items_on_offer=on_offer,
        items_not_on_offer=len(items) - on_offer,
    )
