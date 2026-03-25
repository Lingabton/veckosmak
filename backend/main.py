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


app = FastAPI(title="Veckosmak API", version="0.1.0", lifespan=lifespan)

settings = get_settings()

# Allow both local dev and deployed frontend
allowed_origins = [settings.frontend_url]
if settings.app_env == "production":
    # Add production frontend URLs here when deployed
    allowed_origins.append("https://veckosmak.vercel.app")

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
    return {
        "status": "ok",
        "version": "0.1.0",
        "offers": len(offers),
        "recipes": len(recipes),
    }


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
    _check_rate_limit(request.client.host)

    raw_offers = await get_current_offers(preferences.store_id)
    if not raw_offers:
        raise HTTPException(status_code=404, detail="Inga erbjudanden hittades för denna butik just nu. Veckans erbjudanden kanske inte har laddats ännu.")

    raw_recipes = await get_all_recipes()
    if not raw_recipes:
        raise HTTPException(status_code=404, detail="Receptdatabasen är tom. Vi jobbar på att fylla på — försök igen snart.")

    offers = [_db_offer_to_model(o) for o in raw_offers]
    recipes = [_db_recipe_to_model(r) for r in raw_recipes]

    try:
        menu = await generate_menu(offers, recipes, preferences)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Menu generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kunde inte generera meny just nu. Försök igen om en stund.")

    if not menu.meals:
        raise HTTPException(status_code=500, detail="Menyn blev tom. Försök igen eller ändra dina preferenser.")

    _menu_cache[menu.id] = menu
    # Keep cache bounded
    if len(_menu_cache) > 100:
        oldest = sorted(_menu_cache, key=lambda k: _menu_cache[k].generated_at)[:50]
        for k in oldest:
            del _menu_cache[k]

    return menu


class SwapRequest(BaseModel):
    menu_id: str
    day: str
    reason: str = ""


@app.post("/api/menu/swap")
async def swap_menu_recipe(req: SwapRequest):
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
        new_meal = await swap_recipe(menu, req.day, offers, recipes, req.reason)
    except Exception as e:
        logger.error(f"Swap failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Kunde inte byta recept just nu. Försök igen.")

    # Update swap count and cached menu
    _swap_counts[req.menu_id] = swap_count + 1
    menu.meals = [m if m.day != req.day else new_meal for m in menu.meals]
    menu.total_cost = round(sum(m.estimated_cost for m in menu.meals), 2)
    menu.total_cost_without_offers = round(
        sum(m.estimated_cost_without_offers for m in menu.meals), 2
    )
    menu.total_savings = round(menu.total_cost_without_offers - menu.total_cost, 2)
    menu.savings_percentage = round(
        (menu.total_savings / menu.total_cost_without_offers * 100)
        if menu.total_cost_without_offers > 0
        else 0,
        1,
    )

    return new_meal


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


class FeedbackRequest(BaseModel):
    menu_id: str
    day: str
    action: str  # "liked" or "disliked"


@app.post("/api/menu/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Record user feedback on a recipe (like/dislike)."""
    menu = _menu_cache.get(req.menu_id)
    if not menu:
        return {"status": "ok", "note": "Menu not in cache, feedback noted"}
    # In future: persist to feedback table
    logger.info(f"Feedback: menu={req.menu_id} day={req.day} action={req.action}")
    return {"status": "ok"}


@app.get("/api/offers/bonus")
async def bonus_offers(menu_id: str = "", store_id: str = "ica-maxi-1004097"):
    """Return good deals NOT used in the menu — 'passa på' offers."""
    raw_offers = await get_current_offers(store_id)
    offers = [_db_offer_to_model(o) for o in raw_offers]

    # Find which offer IDs are already used in the menu
    used_ids = set()
    menu = _menu_cache.get(menu_id)
    if menu:
        for meal in menu.meals:
            for o in meal.offer_matches:
                used_ids.add(o.id)

    # Return unused offers with decent discounts
    bonus = []
    for o in offers:
        if o.id in used_ids:
            continue
        discount = 0
        if o.original_price and o.original_price > 0:
            discount = (1 - o.offer_price / o.original_price) * 100
        if discount > 10 or o.quantity_deal:
            bonus.append({**o.model_dump(), "discount": round(discount)})

    bonus.sort(key=lambda x: -x.get("discount", 0))
    return {"offers": bonus[:12]}


@app.get("/api/stores")
async def list_stores():
    from backend.scrapers.store_registry import STORE_REGISTRY
    return {"stores": STORE_REGISTRY}
