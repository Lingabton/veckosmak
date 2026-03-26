"""Scrape all ICA stores — run as cron job or manually.

Usage:
  python scripts/scrape_all_stores.py                    # All stores
  python scripts/scrape_all_stores.py --type maxi        # Only Maxi
  python scripts/scrape_all_stores.py --type maxi,kvantum # Maxi + Kvantum

Or via API:
  curl -X POST "https://veckosmak-api.onrender.com/api/cron/scrape-all?key=SECRET"
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import init_db, save_offers
from backend.scrapers.ica_maxi import IcaMaxiScraper
from backend.scrapers.store_registry import STORE_REGISTRY

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    # Filter by type if specified
    type_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--type="):
            type_filter = arg.split("=")[1].split(",")

    stores = list(STORE_REGISTRY.items())
    if type_filter:
        stores = [(k, v) for k, v in stores if v.get("type") in type_filter]

    logger.info(f"Scraping {len(stores)} stores...")
    scraper = IcaMaxiScraper()
    total_offers = 0
    failed = 0
    start = time.time()

    for i, (store_id, store) in enumerate(stores):
        try:
            offers = await scraper.fetch_offers(store_id)
            if offers:
                await save_offers(offers)
                total_offers += len(offers)
        except Exception as e:
            failed += 1
            logger.debug(f"Failed {store_id}: {e}")

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            logger.info(f"Progress: {i+1}/{len(stores)} ({total_offers} offers, {failed} failed, {elapsed:.0f}s)")
            await asyncio.sleep(1)

    elapsed = time.time() - start
    logger.info(f"Done: {total_offers} offers from {len(stores)} stores in {elapsed:.0f}s ({failed} failed)")


if __name__ == "__main__":
    asyncio.run(main())
