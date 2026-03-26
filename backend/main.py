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

    logger.warning("Cron: 0 offers found")
    return {"status": "warning", "scraped": 0}


@app.get("/api/offers")
async def list_offers(store_id: str = "ica-maxi-1004097", category: str | None = None):
    offers = await get_current_offers(store_id, category)
    return {"offers": offers, "count": len(offers)}


@app.post("/api/offers/scrape")
async def scrape_offers(store_id: str = "ica-maxi-1004097"):
    scraper = IcaMaxiScraper()
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
async def generate_weekly_menu(preferences: UserPreferences, request: Request):
    from backend.analytics import log_preference, log_generation, update_recipe_stats
    _check_rate_limit(request.client.host)

    raw_offers = await get_current_offers(preferences.store_id)
    if not raw_offers:
        raise HTTPException(status_code=404, detail="Inga erbjudanden hittades för denna butik just nu. Veckans erbjudanden kanske inte har laddats ännu.")

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

    return menu


class SwapRequest(BaseModel):
    menu_id: str
    day: str
    reason: str = ""
    recipe_id: str = ""  # If user chose a specific alternative


@app.post("/api/menu/alternatives")
async def get_swap_alternatives(req: SwapRequest):
    """Return 5 alternative recipes for a day — user picks one."""
    from backend.planner.optimizer import _score_recipe, _get_servings_scale, filter_recipes_by_preferences
    from backend.planner.matcher import count_offer_matches
    from backend.planner.savings import calculate_meal_cost
    import random

    menu = _menu_cache.get(req.menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menyn hittades inte.")

    raw_offers = await get_current_offers(menu.store_id)
    raw_recipes = await get_all_recipes()
    offers = [_db_offer_to_model(o) for o in raw_offers]
    recipes = [_db_recipe_to_model(r) for r in raw_recipes]

    current_ids = {m.recipe.id for m in menu.meals}
    eligible = [r for r in recipes if r.id not in current_ids]
    eligible = filter_recipes_by_preferences(eligible, menu.preferences)

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
        scale = _get_servings_scale(recipe, menu.preferences.household_size)
        cost_w, cost_wo, _ = calculate_meal_cost(recipe.ingredients, offers, scale)
        pp = round(cost_w / menu.preferences.household_size) if menu.preferences.household_size > 0 else 0
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
async def top_offers(store_id: str = "ica-maxi-1004097", limit: int = 8):
    """Return the best deals — highest discount percentage."""
    raw_offers = await get_current_offers(store_id)
    offers = [_db_offer_to_model(o) for o in raw_offers]

    # Score by discount percentage
    scored = []
    for o in offers:
        if o.original_price and o.original_price > 0 and o.category in ("meat", "fish", "dairy", "produce"):
            discount = (1 - o.offer_price / o.original_price) * 100
            scored.append((o, discount))

    scored.sort(key=lambda x: -x[1])
    top = [o.model_dump() for o, _ in scored[:limit]]
    return {"offers": top, "count": len(top)}


# --- Auth endpoints ---

class LoginRequest(BaseModel):
    email: str


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Request a magic link. In production, sends email. For now, returns token directly."""
    from backend.auth import create_magic_link
    token = await create_magic_link(req.email)
    # TODO: Send email with link https://veckosmak.vercel.app/auth?token=xxx
    # For now, return token directly (dev mode)
    login_url = f"{settings.frontend_url}#auth={token}"
    logger.info(f"Magic link for {req.email}: {login_url}")
    return {"status": "ok", "message": "Inloggningslänk skickad till din e-post", "token": token}


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


BONUS_CATEGORIES = {
    "frukost": {
        "label": "Frukost",
        "keywords": ["yoghurt", "müsli", "flingor", "juice", "ägg", "ost", "smör",
                      "bregott", "fil", "kvarg", "havre", "marmelad", "sylt", "honung",
                      "mjölk", "apelsin"],
        "max": 3,
    },
    "frukt": {
        "label": "Frukt & mellanmål",
        "keywords": ["banan", "äpple", "päron", "clementin", "druv", "mango",
                      "ananas", "melon", "bär", "nötter", "mandel", "frukt",
                      "avokado", "smoothie", "bar "],
        "max": 3,
    },
    "fika": {
        "label": "Fika & snacks",
        "keywords": ["kaffe", "te ", "kex", "choklad", "kaka", "bulle", "chips",
                      "godis", "glass", "läsk", "saft", "dryck", "cookie"],
        "max": 3,
    },
    "hushal": {
        "label": "Bra att ha",
        "keywords": ["toapapper", "hushålls", "tvättmedel", "diskmedel", "servett",
                      "påse", "folie", "blöja", "schampo", "tandkräm", "tvål",
                      "rengöring", "sköljmedel"],
        "max": 2,
    },
}


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
        if discount < 5 and not o.quantity_deal:
            continue

        item = {**o.model_dump(), "discount": round(discount)}
        name_lower = o.product_name.lower()
        placed = False

        for cat_key, cat_config in BONUS_CATEGORIES.items():
            if any(kw in name_lower for kw in cat_config["keywords"]):
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

    # Add top uncategorized as "Övrigt" if there's room
    if uncategorized:
        uncategorized.sort(key=lambda x: -x.get("discount", 0))
        groups.append({
            "label": "Övrigt",
            "offers": uncategorized[:3],
        })

    return {"groups": groups}


@app.get("/api/stores")
async def list_stores():
    from backend.scrapers.store_registry import STORE_REGISTRY
    return {"stores": STORE_REGISTRY}
