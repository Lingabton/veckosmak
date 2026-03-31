"""Cron job: scrape all stores (ICA + Willys).

Can be run directly or triggered via POST /api/cron/scrape-all?key=SECRET

Usage:
    python scripts/cron_scrape_all.py
    python scripts/cron_scrape_all.py --willys-only
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import init_db, save_offers
from backend.scrapers.ica_maxi import IcaMaxiScraper
from backend.scrapers.willys import WillysScraper, WILLYS_STORES
from backend.scrapers.store_registry import STORE_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def scrape_willys():
    """Scrape all Willys stores."""
    scraper = WillysScraper()
    total = 0
    for store_id in WILLYS_STORES:
        try:
            offers = await scraper.fetch_offers(store_id)
            if offers:
                await save_offers(offers)
                total += len(offers)
                logger.info(f"  {store_id}: {len(offers)} offers")
        except Exception as e:
            logger.warning(f"  {store_id}: failed — {e}")
    return total


async def scrape_ica(store_type="maxi", limit=None):
    """Scrape ICA stores of a given type."""
    scraper = IcaMaxiScraper()
    stores = [(k, v) for k, v in STORE_REGISTRY.items() if v.get("type") == store_type]
    if limit:
        stores = stores[:limit]

    total = 0
    for i, (store_id, store) in enumerate(stores):
        try:
            offers = await scraper.fetch_offers(store_id)
            if offers:
                await save_offers(offers)
                total += len(offers)
            if (i + 1) % 10 == 0:
                logger.info(f"  ICA {store_type}: {i+1}/{len(stores)} ({total} offers)")
                await asyncio.sleep(1)  # Rate limit
        except Exception as e:
            logger.warning(f"  {store_id}: failed — {e}")
    return total


async def main():
    await init_db()

    willys_only = "--willys-only" in sys.argv

    if not willys_only:
        logger.info("=== Scraping ICA Maxi stores ===")
        ica_total = await scrape_ica("maxi")
        logger.info(f"ICA Maxi: {ica_total} total offers")

    logger.info("=== Scraping Willys stores ===")
    willys_total = await scrape_willys()
    logger.info(f"Willys: {willys_total} total offers")

    logger.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
