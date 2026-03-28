"""Weekly cron job: scrape fresh offers.

Usage:
    python scripts/weekly_scrape.py                        # Default store
    python scripts/weekly_scrape.py --store-id ica-maxi-1004097
    python scripts/weekly_scrape.py --dry-run              # Scrape but don't save
    python scripts/weekly_scrape.py --all-maxi             # All Maxi stores

Exit codes:
    0 = success
    1 = 0 offers found (scraper likely broken)
    2 = fewer than 5 offers (suspiciously low)
"""

import argparse
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


async def scrape_store(scraper, store_id, dry_run=False):
    """Scrape a single store. Returns (store_id, offer_count, date_range)."""
    store = STORE_REGISTRY.get(store_id)
    if not store:
        logger.error(f"Unknown store: {store_id}")
        return store_id, 0, ""

    logger.info(f"Scraping {store.get('name', store_id)}...")
    offers = await scraper.fetch_offers(store_id)

    if not offers:
        logger.error(f"[ALERT] 0 offers for {store_id}")
        return store_id, 0, ""

    date_range = f"{offers[0].valid_from} - {offers[0].valid_to}"

    if not dry_run:
        await save_offers(offers)
        logger.info(f"Saved {len(offers)} offers for {store_id}")
    else:
        logger.info(f"[DRY RUN] Would save {len(offers)} offers for {store_id}")

    return store_id, len(offers), date_range


async def main():
    parser = argparse.ArgumentParser(description="Scrape ICA offers")
    parser.add_argument("--store-id", default="ica-maxi-1004097", help="Store ID to scrape")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but don't save to DB")
    parser.add_argument("--all-maxi", action="store_true", help="Scrape all Maxi stores")
    args = parser.parse_args()

    start = time.time()
    await init_db()
    scraper = IcaMaxiScraper()

    if args.all_maxi:
        store_ids = [sid for sid, s in STORE_REGISTRY.items() if s.get("type") == "maxi"]
    else:
        store_ids = [args.store_id]

    results = []
    for store_id in store_ids:
        result = await scrape_store(scraper, store_id, args.dry_run)
        results.append(result)

    elapsed = time.time() - start

    # Summary
    logger.info("=" * 50)
    logger.info(f"Scraping complete in {elapsed:.1f}s")
    total_offers = 0
    exit_code = 0
    for store_id, count, date_range in results:
        status = "OK" if count >= 5 else "LOW" if count > 0 else "FAIL"
        logger.info(f"  {store_id}: {count} offers ({date_range}) [{status}]")
        total_offers += count
        if count == 0:
            exit_code = max(exit_code, 1)
        elif count < 5:
            exit_code = max(exit_code, 2)

    logger.info(f"Total: {total_offers} offers from {len(results)} stores")

    if exit_code == 1:
        logger.error("[ALERT] One or more stores returned 0 offers!")
    elif exit_code == 2:
        logger.warning("One or more stores returned suspiciously few offers (<5)")

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
