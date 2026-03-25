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
1. Prioritera recept som har högt crowd-betyg OCH matchar erbjudanden
2. Om användaren har valt "bästa köp" att utgå från, MÅSTE minst hälften av recepten använda dessa ingredienser
3. Variera proteinkällor över veckan (inte kyckling varje dag)
4. Respektera tidsmixen om angiven (t.ex. 2 snabba + 3 längre)
5. Respektera alltid användarens kostval och livsstilspreferenser
6. Om hushållet har barn, prioritera barnvänliga rätter
7. Håll dig inom budget om angiven
8. Om "minska matsvinn" önskas: välj recept som delar ingredienser (t.ex. kyckling mån + kycklingwok ons)
9. Returnera ALLTID giltig JSON enligt schemat nedan

Du MÅSTE välja recept-ID:n från listan av tillgängliga recept. Hitta INTE på egna.

SVARSFORMAT (strikt JSON, ingen annan text):
{
  "meals": [
    {
      "day": "monday",
      "recipe_id": "ica-123456",
      "reasoning": "Kort motivering",
      "mealprep_tip": "Valfritt tips om mealprep, t.ex. 'Gör dubbelsats och frys in halva'"
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


def _is_incomplete_recipe(recipe: Recipe) -> bool:
    """Check if a recipe is just a component, not a full dinner."""
    title_lower = recipe.title.lower()
    if any(kw in title_lower for kw in INCOMPLETE_RECIPE_KEYWORDS):
        return True
    # Too few non-pantry ingredients = probably not a full meal
    real_ingredients = [i for i in recipe.ingredients if not i.is_pantry_staple]
    if len(real_ingredients) < 3:
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


def _score_recipe(recipe: Recipe, offer_matches: int) -> float:
    """Combined score: offer matches + crowd rating bonus."""
    score = offer_matches * 2.0
    if recipe.rating and recipe.rating_count and recipe.rating_count >= 5:
        score += recipe.rating * 0.5  # Bonus up to 2.5 for 5-star recipes
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
    for r, matches, _ in scored[:30]:
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
    """Pick top recipes by offer match count — no AI needed.
    Returns (menu_data, is_fallback)."""
    scored = []
    for r in recipes:
        matches = count_offer_matches(r.ingredients, offers)
        scored.append((r, matches))
    scored.sort(key=lambda x: -x[1])

    selected = []
    used_ids = set()
    for r, _ in scored:
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


def _get_servings_scale(recipe: Recipe, household_size: int) -> float:
    base = recipe.servings if recipe.servings and recipe.servings > 0 else 4
    return household_size / base


async def generate_menu(
    offers: list[Offer],
    recipes: list[Recipe],
    preferences: UserPreferences,
) -> WeeklyMenu:
    """Generate an optimized weekly menu using Claude."""
    settings = get_settings()

    # Check generation cache — same prefs + same week + same offers = same menu
    now = datetime.now()
    cache_key = hashlib.md5(
        f"{preferences.model_dump_json()}-{now.isocalendar()[1]}-{now.year}-{len(offers)}"
        .encode()
    ).hexdigest()

    if cache_key in _menu_generation_cache:
        cached = _menu_generation_cache[cache_key]
        # Return a copy with new ID so swap tracking works independently
        logger.info("Returning cached menu (same prefs + week)")
        return cached.model_copy(update={"id": str(uuid.uuid4())[:8]})

    eligible = filter_recipes_by_preferences(recipes, preferences)
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

        meals.append(
            PlannedMeal(
                day=day,
                recipe=recipe,
                scaled_servings=preferences.household_size,
                offer_matches=unique_offers,
                estimated_cost=cost_with,
                estimated_cost_without_offers=cost_without,
                reasoning=reasoning,
                popularity_score=_get_crowd_rating(recipe),
                is_fallback=is_fallback,
                mealprep_tip=mealprep_tip,
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

    # Cache the result
    _menu_generation_cache[cache_key] = menu
    if len(_menu_generation_cache) > _MENU_CACHE_MAX:
        oldest_key = next(iter(_menu_generation_cache))
        del _menu_generation_cache[oldest_key]

    return menu


async def swap_recipe(
    current_menu: WeeklyMenu,
    day: str,
    offers: list[Offer],
    recipes: list[Recipe],
    reason: str = "",
) -> PlannedMeal:
    """Swap out a recipe for a specific day."""
    settings = get_settings()

    current_recipe_ids = {m.recipe.id for m in current_menu.meals}
    eligible = [r for r in recipes if r.id not in current_recipe_ids]
    eligible = filter_recipes_by_preferences(eligible, current_menu.preferences)

    current_meal = next((m for m in current_menu.meals if m.day == day), None)
    current_title = current_meal.recipe.title if current_meal else "okänt"

    other_titles = [
        m.recipe.title for m in current_menu.meals if m.day != day
    ]

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
        use_premium=False,  # Swaps are simple — use free tier
    )
    swap_data = parse_json_response(ai_text) if ai_text else {}

    recipe_id = swap_data.get("recipe_id", "")
    reasoning = swap_data.get("reasoning", "")
    recipe_map = {r.id: r for r in eligible}
    recipe = recipe_map.get(recipe_id)

    if not recipe:
        scored = [(r, count_offer_matches(r.ingredients, offers)) for r in eligible]
        scored.sort(key=lambda x: -x[1])
        recipe = scored[0][0] if scored else eligible[0]
        reasoning = "Automatiskt vald baserat på erbjudanden"

    servings_scale = _get_servings_scale(recipe, current_menu.preferences.household_size)
    cost_with, cost_without, matches = calculate_meal_cost(
        recipe.ingredients, offers, servings_scale
    )
    offer_matches = list({o.id: o for _, o in matches if o}.values())

    return PlannedMeal(
        day=day,
        recipe=recipe,
        scaled_servings=current_menu.preferences.household_size,
        offer_matches=offer_matches,
        estimated_cost=cost_with,
        estimated_cost_without_offers=cost_without,
        reasoning=reasoning,
        popularity_score=_get_crowd_rating(recipe),
    )



def _build_shopping_list(
    meals: list[PlannedMeal],
    offers: list[Offer],
    household_size: int,
) -> ShoppingList:
    from backend.planner.savings import estimate_ingredient_cost

    aggregated: dict[str, dict] = {}

    for meal in meals:
        servings_scale = _get_servings_scale(meal.recipe, household_size)
        for ing in meal.recipe.ingredients:
            if ing.is_pantry_staple:
                continue

            key = ing.name.lower().strip()
            scaled_amount = ing.amount * servings_scale

            if key in aggregated:
                aggregated[key]["amount"] += scaled_amount
            else:
                offer = match_ingredient_to_offers(ing, offers)
                cost_with, cost_without = estimate_ingredient_cost(
                    ing, offer, servings_scale
                )
                aggregated[key] = {
                    "name": ing.name,
                    "amount": scaled_amount,
                    "unit": ing.unit,
                    "category": ing.category,
                    "offer": offer,
                    "price": cost_with,
                }

    items = []
    for data in aggregated.values():
        items.append(
            ShoppingItem(
                ingredient_name=data["name"],
                total_amount=round(data["amount"], 1),
                unit=data["unit"],
                category=data["category"],
                matched_offer=data["offer"],
                estimated_price=round(data["price"], 2),
                is_on_offer=data["offer"] is not None,
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
