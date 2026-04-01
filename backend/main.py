import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import get_settings
from backend.db.database import get_all_recipes, get_current_offers, init_db, save_offers
from backend.models.offer import Offer
from backend.models.recipe import Ingredient, Nutrition, Recipe
from backend.models.user_prefs import UserPreferences
from backend.planner.optimizer import generate_menu, swap_recipe
from backend.scrapers.ica_maxi import IcaMaxiScraper
from backend.scrapers.factory import get_scraper_for_store, get_all_store_registries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    offers = await get_current_offers("ica-maxi-1004097")
    recipes = await get_all_recipes()
    logger.info(f"Startup: {len(offers)} offers, {len(recipes)} recipes in DB")
    yield


app = FastAPI(
    title="Veckosmak API",
    version="0.2.0",
    description="AI-driven menyplanering baserad på veckans matbutikserbjudanden",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

settings = get_settings()

# Allow both local dev and deployed frontend
allowed_origins = [settings.frontend_url]
if settings.app_env == "production":
    # Add production frontend URLs here when deployed
    allowed_origins.append("https://veckosmak.vercel.app")

# API version prefix — all endpoints available at both /api/ and /api/v1/
API_PREFIX = "/api"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for generated menus
_menu_cache: dict = {}

# Track swap counts per menu
_swap_counts: dict[str, int] = {}

# Simple rate limiting: track generation timestamps per IP
_rate_limit: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 3600  # 1 hour
RATE_LIMIT_MAX = settings.max_menu_generations_per_hour


def _check_rate_limit(client_ip: str):
    now = time.time()
    timestamps = _rate_limit[client_ip]
    # Remove old entries
    _rate_limit[client_ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Max {RATE_LIMIT_MAX} menygenereringar per timme",
        )
    _rate_limit[client_ip].append(now)


def _db_offer_to_model(row: dict) -> Offer:
    return Offer(**{k: v for k, v in row.items() if k != "scraped_at"})


def _db_recipe_to_model(row: dict) -> Recipe:
    ingredients = [Ingredient(**i) for i in row["ingredients"]]
    return Recipe(
        id=row["id"],
        title=row["title"],
        source_url=row.get("source_url"),
        source=row["source"],
        servings=row["servings"],
        cook_time_minutes=row["cook_time_minutes"],
        difficulty=row["difficulty"],
        tags=row["tags"],
        diet_labels=row["diet_labels"],
        ingredients=ingredients,
        instructions=row["instructions"],
        image_url=row.get("image_url"),
        rating=row.get("rating"),
        rating_count=row.get("rating_count"),
        nutrition=Nutrition(**json.loads(row["nutrition"])) if row.get("nutrition") and row["nutrition"] != "null" else None,
        cooking_method=row.get("cooking_method"),
    )


@app.get("/api/health")
async def health():
    offers = await get_current_offers("ica-maxi-1004097")
    recipes = await get_all_recipes()
    # Check offer freshness
    from datetime import date
    stale_offers = all(
        o.get("valid_to", "2000-01-01") < date.today().isoformat()
        for o in offers
    ) if offers else True

    return {
        "status": "ok" if not stale_offers else "warning",
        "version": "0.2.0",
        "offers": len(offers),
        "recipes": len(recipes),
        "offers_stale": stale_offers,
        "database": "postgresql" if "postgresql" in settings.database_url else "sqlite",
    }


@app.post("/api/cron/scrape")
async def cron_scrape(key: str = ""):
    """Cron endpoint — call weekly to refresh offers.
    Use with cron-job.org or UptimeRobot.
    Set CRON_SECRET env var and pass as ?key=xxx for security.
    """
    expected = settings.cron_secret
    if expected and key != expected:
        raise HTTPException(status_code=403, detail="Invalid key")

    scraper = IcaMaxiScraper()
    try:
        offers = await scraper.fetch_offers("ica-maxi-1004097")
    except Exception as e:
        logger.error(f"Cron scrape failed: {e}")
        return {"status": "error", "detail": str(e)}

    if offers:
        await save_offers(offers)
        logger.info(f"Cron: scraped {len(offers)} offers")
        if len(offers) < 5:
            logger.warning(f"ALERT: Only {len(offers)} offers — unusually low")
        return {"status": "ok", "scraped": len(offers)}

    logger.error("[ALERT] Cron: 0 offers found — scraper may be broken or site changed")
    return {"status": "warning", "scraped": 0}


# Background scraping state
_scrape_all_status = {"running": False, "progress": 0, "total": 0, "scraped": 0, "failed": 0}


@app.post("/api/cron/scrape-all")
async def cron_scrape_all(key: str = "", types: str = "", batch_size: int = 20):
    """Scrape stores by type in background.

    Schedule as separate cron jobs:
      06:05 — POST /api/cron/scrape-all?types=maxi,kvantum&key=SECRET
      07:05 — POST /api/cron/scrape-all?types=supermarket&key=SECRET
      07:45 — POST /api/cron/scrape-all?types=nara&key=SECRET

    Or scrape all at once:
      POST /api/cron/scrape-all?key=SECRET
    """
    import asyncio
    expected = settings.cron_secret
    if expected and key != expected:
        raise HTTPException(status_code=403, detail="Invalid key")

    if _scrape_all_status["running"]:
        return {"status": "already_running", **_scrape_all_status}

    from backend.scrapers.store_registry import STORE_REGISTRY

    # Filter by type if specified
    type_filter = [t.strip() for t in types.split(",") if t.strip()] if types else []
    store_ids = [
        sid for sid, s in STORE_REGISTRY.items()
        if not type_filter or s.get("type") in type_filter
    ]

    if not store_ids:
        return {"status": "error", "detail": f"No stores found for types: {types}"}

    type_label = types or "all"

    async def scrape_background():
        from backend.scrapers.factory import get_scraper_for_store as _get_scraper
        _scrape_all_status.update({"running": True, "progress": 0, "total": len(store_ids), "scraped": 0, "failed": 0, "types": type_label})

        for i in range(0, len(store_ids), batch_size):
            batch = store_ids[i:i + batch_size]
            for store_id in batch:
                try:
                    scraper = _get_scraper(store_id)
                    offers = await scraper.fetch_offers(store_id)
                    if offers:
                        await save_offers(offers)
                        _scrape_all_status["scraped"] += len(offers)
                except Exception as e:
                    _scrape_all_status["failed"] += 1
                    logger.debug(f"Scrape failed for {store_id}: {e}")
                _scrape_all_status["progress"] += 1

            await asyncio.sleep(2)
            logger.info(f"Scrape [{type_label}]: {_scrape_all_status['progress']}/{len(store_ids)}")

        _scrape_all_status["running"] = False
        logger.info(f"Scrape [{type_label}] complete: {_scrape_all_status['scraped']} offers from {_scrape_all_status['progress']} stores ({_scrape_all_status['failed']} failed)")

    asyncio.create_task(scrape_background())
    return {"status": "started", "types": type_label, "stores": len(store_ids)}


@app.get("/api/cron/scrape-all/status")
async def scrape_all_status():
    """Check progress of scrape-all background job."""
    return _scrape_all_status


@app.get("/api/offers")
async def list_offers(store_id: str = "ica-maxi-1004097", category: str | None = None):
    offers = await get_current_offers(store_id, category)
    return {"offers": offers, "count": len(offers)}


@app.post("/api/offers/scrape")
async def scrape_offers(store_id: str = "ica-maxi-1004097"):
    scraper = get_scraper_for_store(store_id)
    try:
        offers = await scraper.fetch_offers(store_id)
    except Exception as e:
        logger.error(f"Scraping failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Kunde inte hämta erbjudanden från butiken just nu. Försök igen om en stund.")
    if not offers:
        raise HTTPException(status_code=502, detail="Inga erbjudanden hittades just nu. Butikens sida kan ha uppdaterats.")
    await save_offers(offers)
    return {"scraped": len(offers)}


@app.post("/api/recipes/scrape")
async def scrape_recipes_endpoint(max_recipes: int = 100):
    """Scrape recipes from ica.se and save to DB."""
    from backend.recipes.scraper import scrape_all_recipes
    from backend.db.database import save_recipes
    try:
        recipes = await scrape_all_recipes(max_recipes=max_recipes)
        if recipes:
            await save_recipes(recipes)
        return {"scraped": len(recipes)}
    except Exception as e:
        logger.error(f"Recipe scraping failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Kunde inte scrapa recept just nu.")


@app.get("/api/recipes")
async def list_recipes(tags: str | None = None, diet: str | None = None, max_time: int | None = None):
    recipes = await get_all_recipes()
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        recipes = [r for r in recipes if any(t in r["tags"] for t in tag_list)]
    if diet:
        recipes = [r for r in recipes if diet in r["diet_labels"]]
    if max_time:
        recipes = [r for r in recipes if r["cook_time_minutes"] <= max_time]
    return {"recipes": recipes, "count": len(recipes)}


@app.post("/api/menu/generate")
async def generate_weekly_menu(preferences: UserPreferences, request: Request, email: str = ""):
    from backend.analytics import log_preference, log_generation, update_recipe_stats
    _check_rate_limit(request.client.host)

    raw_offers = await get_current_offers(preferences.store_id)
    offers_stale = any(o.get("_stale") for o in raw_offers) if raw_offers else False

    raw_recipes = await get_all_recipes()
    if not raw_recipes:
        raise HTTPException(status_code=404, detail="Receptdatabasen är tom. Vi jobbar på att fylla på — försök igen snart.")

    offers = [_db_offer_to_model(o) for o in raw_offers]
    recipes = [_db_recipe_to_model(r) for r in raw_recipes]

    start_time = time.time()
    try:
        menu = await generate_menu(offers, recipes, preferences)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Menu generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kunde inte generera meny just nu. Försök igen om en stund.")
    duration_ms = int((time.time() - start_time) * 1000)

    if not menu.meals:
        raise HTTPException(status_code=500, detail="Menyn blev tom. Försök igen eller ändra dina preferenser.")

    _menu_cache[menu.id] = menu
    if len(_menu_cache) > 100:
        oldest = sorted(_menu_cache, key=lambda k: _menu_cache[k].generated_at)[:50]
        for k in oldest:
            del _menu_cache[k]

    # Analytics (non-blocking)
    try:
        await log_preference(preferences.model_dump())
        ai_provider = "fallback" if any(m.is_fallback for m in menu.meals) else "ai"
        await log_generation(menu.id, ai_provider, len(menu.meals),
                             menu.total_cost, menu.total_savings, len(raw_offers), duration_ms)
        for meal in menu.meals:
            await update_recipe_stats(meal.recipe.id, 'selected')
    except Exception:
        pass

    # Save menu to user history if logged in
    if email:
        try:
            from backend.auth import save_user_menu
            await save_user_menu(email, menu.model_dump())
        except Exception:
            pass

    # Add staleness/no-offers info to response
    if offers_stale:
        menu.offers_note = "Erbjudandena kan vara utgångna — vi visar de senaste vi har."
    elif not raw_offers:
        menu.offers_note = "Inga erbjudanden hittades — menyn är baserad på våra bästa recept."

    return menu


class SwapRequest(BaseModel):
    menu_id: str = ""
    day: str = ""
    reason: str = ""
    recipe_id: str = ""
    exclude_recipe_ids: list[str] = []


@app.post("/api/menu/alternatives")
async def get_swap_alternatives(req: SwapRequest):
    """Return 5 alternative recipes for a day — user picks one."""
    from backend.planner.optimizer import _score_recipe, _get_servings_scale, filter_recipes_by_preferences
    from backend.planner.matcher import count_offer_matches
    from backend.planner.savings import calculate_meal_cost
    import random

    menu = _menu_cache.get(req.menu_id) if req.menu_id else None

    # Get store_id and preferences — from cache or from request context
    store_id = menu.store_id if menu else "ica-maxi-1004097"
    prefs = menu.preferences if menu else UserPreferences()

    raw_offers = await get_current_offers(store_id)
    raw_recipes = await get_all_recipes()
    offers = [_db_offer_to_model(o) for o in raw_offers]
    recipes = [_db_recipe_to_model(r) for r in raw_recipes]

    # Exclude current menu recipes
    exclude_ids = set(req.exclude_recipe_ids) if req.exclude_recipe_ids else set()
    if menu:
        exclude_ids.update(m.recipe.id for m in menu.meals)
    eligible = [r for r in recipes if r.id not in exclude_ids]
    eligible = filter_recipes_by_preferences(eligible, prefs)

    # Score and pick top candidates with some randomization
    scored = []
    for r in eligible:
        matches = count_offer_matches(r.ingredients, offers)
        score = _score_recipe(r, matches)
        scored.append((r, matches, score))
    scored.sort(key=lambda x: -x[2])

    # Take top 15, shuffle, pick 5
    pool = scored[:15]
    random.shuffle(pool)
    candidates = pool[:5]
    # Re-sort by score for display
    candidates.sort(key=lambda x: -x[2])

    results = []
    for recipe, matches, score in candidates:
        hs = prefs.household_size or 4
        scale = _get_servings_scale(recipe, hs)
        cost_w, cost_wo, _ = calculate_meal_cost(recipe.ingredients, offers, scale)
        pp = round(cost_w / hs) if hs > 0 else 0
        is_favorite = recipe.rating and recipe.rating >= 4.0 and (recipe.rating_count or 0) >= 50
        results.append({
            "recipe_id": recipe.id,
            "title": recipe.title,
            "cook_time_minutes": recipe.cook_time_minutes,
            "difficulty": recipe.difficulty,
            "rating": recipe.rating,
            "rating_count": recipe.rating_count,
            "estimated_cost": round(cost_w, 2),
            "price_per_portion": pp,
            "offer_matches": matches,
            "image_url": recipe.image_url,
            "is_favorite": is_favorite,
            "tags": recipe.tags,
        })

    return {"alternatives": results}


@app.post("/api/menu/swap")
async def swap_menu_recipe(req: SwapRequest):
    from backend.analytics import log_swap, update_recipe_stats
    menu = _menu_cache.get(req.menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte. Generera en ny meny.")

    # Count swaps for this menu
    swap_count = _swap_counts.get(req.menu_id, 0)
    if swap_count >= settings.max_swaps_per_menu:
        raise HTTPException(status_code=429, detail=f"Max {settings.max_swaps_per_menu} byten per meny")

    raw_offers = await get_current_offers(menu.store_id)
    raw_recipes = await get_all_recipes()
    offers = [_db_offer_to_model(o) for o in raw_offers]
    recipes = [_db_recipe_to_model(r) for r in raw_recipes]

    try:
        new_meal = await swap_recipe(menu, req.day, offers, recipes, req.reason, req.recipe_id)
    except Exception as e:
        logger.error(f"Swap failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kunde inte byta recept just nu. Försök igen.")

    # Log swap analytics
    old_meal = next((m for m in menu.meals if m.day == req.day), None)
    try:
        if old_meal:
            await log_swap(old_meal.recipe.id, old_meal.recipe.title,
                          new_meal.recipe.id, new_meal.recipe.title, req.day, req.reason)
            await update_recipe_stats(old_meal.recipe.id, 'swapped_away')
            await update_recipe_stats(new_meal.recipe.id, 'selected')
    except Exception:
        pass

    # Update swap count and cached menu
    _swap_counts[req.menu_id] = swap_count + 1
    menu.meals = [m if m.day != req.day else new_meal for m in menu.meals]
    menu.total_cost = round(sum(m.estimated_cost for m in menu.meals), 2)
    menu.total_cost_without_offers = round(
        sum(m.estimated_cost_without_offers for m in menu.meals), 2
    )
    menu.total_savings = round(max(0, menu.total_cost_without_offers - menu.total_cost), 2)
    menu.savings_percentage = round(
        (menu.total_savings / menu.total_cost_without_offers * 100)
        if menu.total_cost_without_offers > 0
        else 0,
        1,
    )

    # Rebuild shopping list with updated meals
    from backend.planner.optimizer import _build_shopping_list
    menu.shopping_list = _build_shopping_list(menu.meals, offers, menu.preferences.household_size)

    # Return the full updated menu so frontend can refresh everything
    return menu


@app.get("/api/offers/top")
async def top_offers(store_id: str = "ica-maxi-1004097", limit: int = 12):
    """Return best dinner-relevant deals — proteins first, good mix, best value.

    Scoring: dinner relevance × discount × category diversity.
    Proteins (meat, fish) get a bonus since they're the most expensive
    part of a dinner and offer the most savings.
    """
    raw_offers = await get_current_offers(store_id)
    offers = [_db_offer_to_model(o) for o in raw_offers]

    # Categories useful for cooking dinners (not läsk, godis, toapapper)
    DINNER_CATEGORIES = {"meat", "fish", "dairy", "produce", "pantry", "frozen"}
    # Non-food keywords to filter out
    NON_DINNER = [
        "läsk", "coca", "pepsi", "fanta", "sprite", "godis", "chips", "snacks",
        "toapapper", "hushållspapper", "tvättmedel", "diskmedel", "schampo",
        "tandkräm", "blöja", "servett", "kaffe", "te ", "glass", "saft",
        "juice", "öl", "vin", "cider", "energidryck", "tuggummi",
    ]

    scored = []
    for o in offers:
        name_lower = o.product_name.lower()

        # Skip non-dinner items
        if any(nd in name_lower for nd in NON_DINNER):
            continue

        # Skip non-food categories (unless they're actually food in "other")
        if o.category == "other" and o.category not in DINNER_CATEGORIES:
            # Allow "other" if it looks like food
            food_hints = ["grädde", "ägg", "tomat", "sås", "buljong", "krydda",
                          "olja", "vinäger", "senap", "ketchup"]
            if not any(h in name_lower for h in food_hints):
                continue

        discount = 0
        if o.original_price and o.original_price > 0:
            discount = (1 - o.offer_price / o.original_price) * 100
        if discount < 3 and not o.quantity_deal:
            continue

        # Score: base discount + dinner relevance bonus
        score = max(discount, 8 if o.quantity_deal else 0)

        # Protein bonus — meat & fish are the expensive part of dinner
        if o.category == "meat":
            score += 15
        elif o.category == "fish":
            score += 12
        # Other dinner essentials
        elif o.category == "dairy":
            score += 5
        elif o.category == "produce":
            score += 5

        scored.append((o, score, discount))

    scored.sort(key=lambda x: -x[1])

    # Pick top items but ensure category diversity
    # Goal: at least 2 proteins, 1 dairy, 1 produce in the top results
    selected = []
    cat_counts = {}
    MAX_PER_CAT = 4  # Don't show 8 meat items

    for o, score, discount in scored:
        cat = o.category
        if cat_counts.get(cat, 0) >= MAX_PER_CAT:
            continue
        selected.append({**o.model_dump(), "discount": round(discount)})
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if len(selected) >= limit:
            break

    # If we didn't fill up, add more without category limit
    if len(selected) < limit:
        selected_ids = {s["id"] for s in selected}
        for o, score, discount in scored:
            if o.id not in selected_ids:
                selected.append({**o.model_dump(), "discount": round(discount)})
                if len(selected) >= limit:
                    break

    return {"offers": selected, "count": len(selected), "total_available": len(offers)}


@app.get("/api/offers/all")
async def all_offers(store_id: str = "ica-maxi-1004097"):
    """Return ALL current offers for a store — for browsing."""
    raw_offers = await get_current_offers(store_id)
    offers = []
    for o in raw_offers:
        offer = _db_offer_to_model(o)
        discount = 0
        if offer.original_price and offer.original_price > 0:
            discount = round((1 - offer.offer_price / offer.original_price) * 100)
        offers.append({**offer.model_dump(), "discount": discount})
    # Group by category
    grouped = {}
    for o in sorted(offers, key=lambda x: -x.get("discount", 0)):
        cat = o.get("category", "other")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(o)
    return {"offers": offers, "grouped": grouped, "count": len(offers)}


# --- Auth endpoints ---

class LoginRequest(BaseModel):
    email: str


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Request a magic link. Sends email in production, returns token in dev."""
    from backend.auth import create_magic_link
    from backend.email_sender import send_magic_link_email
    token = await create_magic_link(req.email)
    email_sent = await send_magic_link_email(req.email, token)
    response = {"status": "ok", "message": "Inloggningslänk skickad till din e-post"}
    # In development (no email sent), include token for easy testing
    if not email_sent:
        response["token"] = token
    return response


@app.get("/api/auth/verify")
async def verify(token: str):
    """Verify a magic link token and return user data."""
    from backend.auth import verify_token, get_user
    email = await verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Länken har gått ut eller redan använts")
    user = await get_user(email)
    return {"status": "ok", "email": email, "user": user}


@app.post("/api/user/preferences")
async def save_prefs(preferences: UserPreferences, email: str = ""):
    """Save preferences for a logged-in user."""
    if not email:
        return {"status": "ok", "note": "No user — preferences saved locally"}
    from backend.auth import save_user_preferences
    await save_user_preferences(email, preferences.model_dump())
    return {"status": "ok"}


class FeedbackRequest(BaseModel):
    menu_id: str
    day: str
    action: str  # "liked" or "disliked"


@app.post("/api/menu/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Record user feedback on a recipe (like/dislike)."""
    from backend.analytics import update_recipe_stats
    menu = _menu_cache.get(req.menu_id)
    if menu:
        meal = next((m for m in menu.meals if m.day == req.day), None)
        if meal:
            try:
                await update_recipe_stats(meal.recipe.id, req.action)
            except Exception:
                pass
    logger.info(f"Feedback: menu={req.menu_id} day={req.day} action={req.action}")
    return {"status": "ok"}


# "Passa på" categories — practical needs for a family, not junk
# Use word-boundary matching to avoid "rotfruktsgratäng" matching "frukt"
BONUS_CATEGORIES = {
    "frukost": {
        "label": "Frukost & mejeri",
        "keywords": ["yoghurt", "müsli", "flingor", "havre", "fil ",
                      "kvarg", "marmelad", "sylt", "honung", "bregott"],
        "max": 3,
    },
    "basvara": {
        "label": "Bra basvaror",
        "keywords": ["mjölk ", "smör ", "ost ", "grädde", "ägg ",
                      "pasta ", "ris ", "mjöl ", "olja", "buljong",
                      "krossade tomater", "tomatpuré"],
        "max": 4,
    },
    "hushal": {
        "label": "Hushåll",
        "keywords": ["toapapper", "hushållspapper", "tvättmedel", "diskmedel",
                      "sköljmedel", "rengöring"],
        "max": 2,
    },
}

# Items to EXCLUDE from "Passa på" — not basic needs
BONUS_EXCLUDE = [
    "godis", "chips", "snacks", "choklad", "kaka", "bulle",
    "läsk", "coca", "pepsi", "fanta", "sprite", "energidryck",
    "glass", "cookie", "tuggummi",
    "påskägg", "servett", "ljus ", "dekoration",
    "saft", "dryck",
]


@app.get("/api/offers/bonus")
async def bonus_offers(menu_id: str = "", store_id: str = "ica-maxi-1004097"):
    """Return curated deals NOT used in the menu, grouped by category."""
    raw_offers = await get_current_offers(store_id)
    offers = [_db_offer_to_model(o) for o in raw_offers]

    used_ids = set()
    menu = _menu_cache.get(menu_id)
    if menu:
        for meal in menu.meals:
            for o in meal.offer_matches:
                used_ids.add(o.id)

    # Categorize unused offers
    categorized = {cat: [] for cat in BONUS_CATEGORIES}
    uncategorized = []

    for o in offers:
        if o.id in used_ids:
            continue
        discount = 0
        if o.original_price and o.original_price > 0:
            discount = (1 - o.offer_price / o.original_price) * 100
        if discount < 3 and not o.quantity_deal:
            continue

        name_lower = o.product_name.lower()

        # Exclude junk/non-essential items
        if any(ex in name_lower for ex in BONUS_EXCLUDE):
            continue

        item = {**o.model_dump(), "discount": round(discount)}
        placed = False

        # Use space-padded keywords for word-boundary matching
        # " ost " won't match "rotfruktsgratäng", " ägg " won't match "påskägg"
        name_padded = f" {name_lower} "
        for cat_key, cat_config in BONUS_CATEGORIES.items():
            if any(kw in name_padded or (not kw.endswith(' ') and kw in name_lower) for kw in cat_config["keywords"]):
                if len(categorized[cat_key]) < cat_config["max"]:
                    categorized[cat_key].append(item)
                    placed = True
                    break

        if not placed:
            uncategorized.append(item)

    # Sort each category by discount
    for cat in categorized:
        categorized[cat].sort(key=lambda x: -x.get("discount", 0))

    # Build response — only include non-empty categories
    groups = []
    for cat_key, cat_config in BONUS_CATEGORIES.items():
        if categorized[cat_key]:
            groups.append({
                "label": cat_config["label"],
                "offers": categorized[cat_key],
            })

    # Add top uncategorized — only food items (meat, fish, dairy, produce, pantry)
    food_uncat = [u for u in uncategorized if u.get("category") in ("meat", "fish", "dairy", "produce", "pantry", "frozen")]
    if food_uncat:
        food_uncat.sort(key=lambda x: -x.get("discount", 0))
        groups.append({
            "label": "Fler matvaror",
            "offers": food_uncat[:3],
        })

    return {"groups": groups}


@app.get("/api/stores")
async def list_stores():
    return {"stores": get_all_store_registries()}


@app.get("/api/stores/leaflet")
async def store_leaflet_redirect(store_id: str = ""):
    """Redirect to the store's offer/leaflet page."""
    from fastapi.responses import RedirectResponse
    all_stores = get_all_store_registries()
    store = all_stores.get(store_id, {})
    url = store.get("url", "")
    if url:
        return RedirectResponse(url=url)
    # Fallback
    if store_id.startswith("willys"):
        return RedirectResponse(url="https://www.willys.se/erbjudanden")
    return RedirectResponse(url="https://www.ica.se/erbjudanden/")


# --- User profile & account endpoints ---

class ProfileUpdateRequest(BaseModel):
    name: str = ""
    bio: str = ""
    city: str = ""
    is_public: bool = False


@app.post("/api/user/profile")
async def update_profile(req: ProfileUpdateRequest, email: str = ""):
    """Update user profile (name, bio, city, public visibility)."""
    if not email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    from backend.auth import update_user_profile
    await update_user_profile(email, name=req.name or None, bio=req.bio or None,
                               city=req.city or None, is_public=req.is_public)
    return {"status": "ok"}


@app.get("/api/user/profile")
async def get_profile(email: str = ""):
    """Get user profile and subscription info."""
    if not email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    from backend.auth import get_user
    user = await get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="Användare hittades inte")
    return {
        "user": {
            "email": user["email"],
            "name": user.get("name"),
            "bio": user.get("bio"),
            "city": user.get("city"),
            "is_public": user.get("is_public", False),
            "created_at": user.get("created_at"),
        },
    }


@app.get("/api/user/menus")
async def get_user_menus(email: str = "", limit: int = 20):
    """Get user's menu history."""
    if not email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    from backend.auth import get_user_menu_history
    menus = await get_user_menu_history(email, limit)
    return {"menus": menus}



# --- Price poll & email signup (launch validation) ---

class PricePollRequest(BaseModel):
    menu_id: str
    answer: str  # "0", "29", "49", "79"

@app.post("/api/poll/price")
async def submit_price_poll(req: PricePollRequest):
    """Save a price willingness-to-pay response."""
    import aiosqlite
    from backend.db.database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO price_poll (menu_id, answer) VALUES (?, ?)",
            (req.menu_id, req.answer)
        )
        await db.commit()
    logger.info(f"Price poll: menu={req.menu_id} answer={req.answer}")
    return {"status": "ok"}


class EmailSignupRequest(BaseModel):
    email: str

@app.post("/api/signup/email")
async def email_signup(req: EmailSignupRequest):
    """Save an email for weekly menu delivery."""
    import aiosqlite
    from backend.db.database import DB_PATH
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Ogiltig e-postadress")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO email_signups (email) VALUES (?)",
            (email,)
        )
        await db.commit()
    logger.info(f"Email signup: {email}")
    return {"status": "ok"}


# --- PDF export endpoints ---

@app.get("/api/export/shopping-list/{menu_id}")
async def export_shopping_list_pdf(menu_id: str):
    """Download shopping list as PDF."""
    from fastapi.responses import Response
    menu = _menu_cache.get(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte")
    try:
        from backend.pdf_export import generate_shopping_list_pdf
        pdf_bytes = generate_shopping_list_pdf(menu.model_dump())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="inkopslista-v{menu.week_number}.pdf"'}
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF-export inte tillgängligt — installera reportlab")


@app.get("/api/export/menu/{menu_id}")
async def export_menu_pdf(menu_id: str):
    """Download full menu + shopping list as PDF."""
    from fastapi.responses import Response
    menu = _menu_cache.get(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte")
    try:
        from backend.pdf_export import generate_menu_pdf
        pdf_bytes = generate_menu_pdf(menu.model_dump())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="veckomeny-v{menu.week_number}.pdf"'}
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF-export inte tillgängligt — installera reportlab")


# --- ICA cart integration ---

@app.get("/api/cart/ica")
async def ica_cart_link(menu_id: str = ""):
    """Get ICA Handla deep link for the shopping list."""
    from backend.ica_cart import build_cart_url, match_shopping_list_to_ica
    menu = _menu_cache.get(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte")

    items = [item.model_dump() if hasattr(item, 'model_dump') else item
             for item in menu.shopping_list.items]
    cart_url = build_cart_url(items, menu.store_id)
    # Try to match items to ICA products (non-blocking, best-effort)
    try:
        enriched = await match_shopping_list_to_ica(items[:10], menu.store_id)
    except Exception:
        enriched = []

    return {
        "cart_url": cart_url,
        "matched_items": enriched,
        "store_id": menu.store_id,
    }


# --- Community endpoints ---

class ShareMenuRequest(BaseModel):
    menu_id: str
    title: str = ""
    description: str = ""
    email: str = ""


@app.post("/api/community/share")
async def share_menu(req: ShareMenuRequest):
    """Share a menu with the community."""
    if not req.email:
        raise HTTPException(status_code=401, detail="Du måste vara inloggad för att dela")
    from backend.auth import get_user
    user = await get_user(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Användare hittades inte")

    menu = _menu_cache.get(req.menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte")

    from backend.community import share_menu as do_share
    title = req.title or f"Veckomeny v{menu.week_number}"
    dietary_tags = menu.active_filters if menu.active_filters else []

    shared_id = await do_share(
        user_id=user["id"],
        title=title,
        description=req.description,
        menu_data=menu.model_dump(),
        store_name=menu.store_name,
        city=user.get("city", ""),
        total_cost=menu.total_cost,
        total_savings=menu.total_savings,
        num_meals=len(menu.meals),
        dietary_tags=dietary_tags,
    )
    return {"status": "ok", "shared_id": shared_id}


@app.get("/api/community/menus")
async def community_menus(sort: str = "popular", city: str = "", limit: int = 10):
    """Browse shared menus."""
    from backend.community import get_popular_menus, get_recent_menus
    if sort == "recent":
        menus = await get_recent_menus(limit, city or None)
    else:
        menus = await get_popular_menus(limit, city or None)
    return {"menus": menus}


@app.get("/api/community/menu/{menu_id}")
async def get_shared_menu(menu_id: str):
    """Get a specific shared menu."""
    from backend.community import get_shared_menu as get_menu
    menu = await get_menu(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Delad meny hittades inte")
    return menu


class LikeRequest(BaseModel):
    email: str


@app.post("/api/community/menu/{menu_id}/like")
async def like_menu(menu_id: str, req: LikeRequest):
    """Like or unlike a shared menu."""
    if not req.email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    from backend.auth import get_user
    from backend.community import toggle_like
    user = await get_user(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Användare hittades inte")
    result = await toggle_like(user["id"], menu_id)
    return result


class RateRequest(BaseModel):
    email: str
    rating: int  # 1-5
    comment: str = ""


@app.post("/api/recipes/{recipe_id}/rate")
async def rate_recipe(recipe_id: str, req: RateRequest):
    """Rate a recipe 1-5."""
    if not req.email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    if not 1 <= req.rating <= 5:
        raise HTTPException(status_code=400, detail="Betyg måste vara 1-5")
    from backend.auth import get_user
    from backend.community import rate_recipe as do_rate
    user = await get_user(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Användare hittades inte")
    await do_rate(user["id"], recipe_id, req.rating, req.comment or None)
    return {"status": "ok"}


@app.get("/api/recipes/{recipe_id}/ratings")
async def get_recipe_ratings(recipe_id: str):
    """Get ratings for a recipe."""
    from backend.community import get_recipe_ratings as get_ratings
    return await get_ratings(recipe_id)


@app.post("/api/recipes/{recipe_id}/favorite")
async def toggle_favorite(recipe_id: str, req: LikeRequest):
    """Toggle recipe as favorite."""
    if not req.email:
        raise HTTPException(status_code=401, detail="Inte inloggad")
    from backend.auth import get_user
    from backend.community import toggle_favorite as do_toggle
    user = await get_user(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Användare hittades inte")
    is_fav = await do_toggle(user["id"], recipe_id)
    return {"status": "ok", "is_favorite": is_fav}


@app.get("/api/user/favorites")
async def get_favorites(email: str = ""):
    """Get user's favorite recipe IDs."""
    if not email:
        return {"favorites": []}
    from backend.auth import get_user
    from backend.community import get_user_favorites
    user = await get_user(email)
    if not user:
        return {"favorites": []}
    favs = await get_user_favorites(user["id"])
    return {"favorites": favs}


@app.get("/api/community/stats")
async def community_stats():
    """Get community statistics."""
    from backend.community import get_community_stats
    return await get_community_stats()


