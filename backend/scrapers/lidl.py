"""Lidl grocery store offer scraper.

STATUS: NOT YET WORKING — Lidl's offers pages are fully client-side rendered
SPAs with no server-side product data. The offer pages at
/c/lidl-plus-erbjudanden/s10017715 return HTML shells with no product info.

To make this work, options are:
1. Use a headless browser (Playwright) to render the SPA and extract product data
2. Find Lidl's internal API (not yet discovered)
3. Use a third-party source (e.g. bastaerbjudanden.se)

For now, this scraper returns an empty list and logs a warning.
"""

import logging

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper

logger = logging.getLogger(__name__)

LIDL_STORES: dict[str, dict] = {
    "lidl-stockholm-hornsberg": {"name": "Lidl Hornsberg", "city": "Stockholm", "type": "lidl"},
    "lidl-stockholm-liljeholmen": {"name": "Lidl Liljeholmen", "city": "Stockholm", "type": "lidl"},
    "lidl-goteborg-backaplan": {"name": "Lidl Backaplan", "city": "Göteborg", "type": "lidl"},
    "lidl-goteborg-munkeback": {"name": "Lidl Munkebäck", "city": "Göteborg", "type": "lidl"},
    "lidl-malmo-centrum": {"name": "Lidl Malmö Centrum", "city": "Malmö", "type": "lidl"},
    "lidl-uppsala": {"name": "Lidl Uppsala", "city": "Uppsala", "type": "lidl"},
    "lidl-linkoping": {"name": "Lidl Linköping", "city": "Linköping", "type": "lidl"},
    "lidl-orebro": {"name": "Lidl Örebro", "city": "Örebro", "type": "lidl"},
    "lidl-vasteras": {"name": "Lidl Västerås", "city": "Västerås", "type": "lidl"},
    "lidl-helsingborg": {"name": "Lidl Helsingborg", "city": "Helsingborg", "type": "lidl"},
}


class LidlScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        logger.warning(
            f"Lidl scraper not yet implemented — their offers page is a "
            f"client-side SPA with no server-rendered data. Returning 0 offers for {store_id}."
        )
        return []

    def get_store_info(self, store_id: str) -> dict:
        return LIDL_STORES.get(store_id, {})
