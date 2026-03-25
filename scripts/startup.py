"""Run on deploy: initialize DB, scrape offers if stale, ensure recipes exist."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import get_all_recipes, get_current_offers, init_db, save_offers, save_recipes
from backend.scrapers.ica_maxi import IcaMaxiScraper
from backend.recipes.scraper import scrape_all_recipes

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    # Check offers
    offers = await get_current_offers("ica-maxi-1004097")
    if not offers:
        logger.info("No current offers — scraping...")
        scraper = IcaMaxiScraper()
        new_offers = await scraper.fetch_offers("ica-maxi-1004097")
        if new_offers:
            await save_offers(new_offers)
            logger.info(f"Saved {len(new_offers)} offers")
        else:
            logger.warning("Scraping returned 0 offers")
    else:
        logger.info(f"{len(offers)} current offers in DB")

    # Check recipes
    recipes = await get_all_recipes()
    if len(recipes) < 50:
        logger.info(f"Only {len(recipes)} recipes — scraping more...")
        new_recipes = await scrape_all_recipes(max_recipes=300)
        if new_recipes:
            await save_recipes(new_recipes)
            logger.info(f"Saved {len(new_recipes)} recipes")
    else:
        logger.info(f"{len(recipes)} recipes in DB")

    logger.info("Startup complete")


if __name__ == "__main__":
    asyncio.run(main())
