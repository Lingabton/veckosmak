"""Manually run: fetch this week's offers and save to database."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import init_db, save_offers
from backend.scrapers.ica_maxi import IcaMaxiScraper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main():
    await init_db()

    scraper = IcaMaxiScraper()
    store_id = "ica-maxi-1004097"

    print(f"Hamtar erbjudanden for {store_id}...")
    offers = await scraper.fetch_offers(store_id)

    if not offers:
        print("Inga erbjudanden hittades!")
        return

    print(f"\nHittade {len(offers)} erbjudanden:\n")
    for o in offers:
        savings = ""
        if o.original_price and o.offer_price:
            pct = (1 - o.offer_price / o.original_price) * 100
            savings = f" (-{pct:.0f}%)"
        deal = f" [{o.quantity_deal}]" if o.quantity_deal else ""
        print(f"  {o.product_name} ({o.brand or '-'}) — {o.offer_price} {o.unit}{deal}{savings}")
        print(f"    Kategori: {o.category} | Ord.pris: {o.original_price or '?'}")

    await save_offers(offers)
    print(f"\nSparat {len(offers)} erbjudanden till databasen.")


if __name__ == "__main__":
    asyncio.run(main())
