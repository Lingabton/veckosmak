"""Run on deploy: initialize DB, seed recipes from JSON, scrape offers if stale."""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import get_all_recipes, get_current_offers, init_db, save_offers, save_recipes
from backend.models.recipe import Ingredient, Nutrition, Recipe
from backend.scrapers.ica_maxi import IcaMaxiScraper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEED_FILE = Path(__file__).parent / "recipes_seed.json"


def load_recipes_from_seed() -> list[Recipe]:
    """Load recipes from bundled seed file."""
    if not SEED_FILE.exists():
        logger.warning("No seed file found")
        return []

    data = json.loads(SEED_FILE.read_text())
    recipes = []
    for r in data:
        try:
            ingredients = [Ingredient(**i) for i in r.get("ingredients", [])]
            nutrition = None
            if r.get("nutrition") and isinstance(r["nutrition"], dict):
                nutrition = Nutrition(**r["nutrition"])
            recipes.append(Recipe(
                id=r["id"], title=r["title"],
                source_url=r.get("source_url"), source=r["source"],
                servings=r.get("servings", 4),
                cook_time_minutes=r.get("cook_time_minutes", 30),
                difficulty=r.get("difficulty", "medium"),
                tags=r.get("tags", []), diet_labels=r.get("diet_labels", []),
                ingredients=ingredients,
                instructions=r.get("instructions", []),
                image_url=r.get("image_url"),
                rating=r.get("rating"), rating_count=r.get("rating_count"),
                nutrition=nutrition,
                cooking_method=r.get("cooking_method"),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse seed recipe {r.get('id')}: {e}")
    return recipes


async def main():
    await init_db()

    # Check offers
    offers = await get_current_offers("ica-maxi-1004097")
    if not offers:
        logger.info("No current offers — scraping...")
        scraper = IcaMaxiScraper()
        try:
            new_offers = await scraper.fetch_offers("ica-maxi-1004097")
            if new_offers:
                await save_offers(new_offers)
                logger.info(f"Saved {len(new_offers)} offers")
            else:
                logger.warning("Scraping returned 0 offers")
        except Exception as e:
            logger.warning(f"Offer scraping failed: {e}")
    else:
        logger.info(f"{len(offers)} current offers in DB")

    # Seed recipes from JSON if DB is empty/small
    recipes = await get_all_recipes()
    if len(recipes) < 50:
        logger.info(f"Only {len(recipes)} recipes — seeding from {SEED_FILE.name}...")
        seed_recipes = load_recipes_from_seed()
        if seed_recipes:
            await save_recipes(seed_recipes)
            logger.info(f"Seeded {len(seed_recipes)} recipes from file")
        else:
            logger.warning("No seed recipes found — DB will be empty")
    else:
        logger.info(f"{len(recipes)} recipes in DB")

    logger.info("Startup complete")


if __name__ == "__main__":
    asyncio.run(main())
