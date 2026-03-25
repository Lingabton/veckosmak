"""Weekly cron job: scrape fresh offers every Monday morning."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import init_db, save_offers
from backend.scrapers.ica_maxi import IcaMaxiScraper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    scraper = IcaMaxiScraper()
    offers = await scraper.fetch_offers("ica-maxi-1004097")

    if not offers:
        logger.error("ALERT: 0 erbjudanden hittades! Sidans struktur kan ha andrats.")
        sys.exit(1)

    await save_offers(offers)
    logger.info(f"Scraped and saved {len(offers)} offers")


if __name__ == "__main__":
    asyncio.run(main())
