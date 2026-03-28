"""Coop grocery store offer scraper.

STATUS: NOT YET WORKING — Coop's offers are loaded client-side via their
DKE API (external.api.coop.se/dke/offers/) which requires an API subscription
key. The key is publicly visible in their page source but the endpoint returns
404 — likely needs additional auth headers or has been moved.

To make this work, options are:
1. Reverse-engineer the full auth flow from coop.se/butiker-erbjudanden/
2. Use a headless browser (Playwright) to render the SPA
3. Partner with Coop for API access

For now, this scraper returns an empty list and logs a warning.
"""

import logging

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper

logger = logging.getLogger(__name__)

COOP_STORES: dict[str, dict] = {
    "coop-stockholm-stadion": {"name": "Coop Stadion Stockholm", "city": "Stockholm", "type": "coop"},
    "coop-stockholm-karlaplan": {"name": "Coop Karlaplan", "city": "Stockholm", "type": "coop"},
    "coop-goteborg-nordstan": {"name": "Coop Nordstan", "city": "Göteborg", "type": "coop"},
    "coop-malmo-triangeln": {"name": "Coop Triangeln", "city": "Malmö", "type": "coop"},
    "coop-uppsala-centrum": {"name": "Coop Uppsala Centrum", "city": "Uppsala", "type": "coop"},
    "coop-linkoping": {"name": "Stora Coop Linköping", "city": "Linköping", "type": "stora-coop"},
    "coop-orebro": {"name": "Stora Coop Örebro", "city": "Örebro", "type": "stora-coop"},
    "coop-vasteras": {"name": "Coop Västerås", "city": "Västerås", "type": "coop"},
    "coop-umea": {"name": "Coop Umeå", "city": "Umeå", "type": "coop"},
    "coop-gavle": {"name": "Coop Gävle", "city": "Gävle", "type": "coop"},
}


class CoopScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        logger.warning(
            f"Coop scraper not yet implemented — their offers API requires "
            f"client-side rendering. Returning 0 offers for {store_id}."
        )
        return []

    def get_store_info(self, store_id: str) -> dict:
        return COOP_STORES.get(store_id, {})
