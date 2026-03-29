"""Coop grocery store offer scraper.

STATUS: STUB — Coop's Hybris ecommerce API at external.api.coop.se requires
OAuth authentication. All product/offer data is loaded client-side via
authenticated XHR calls. No public endpoint found.

Known API details (for future implementation):
- Hybris API: external.api.coop.se/ecommerce/coop
- DKE offers: external.api.coop.se/dke/offers/
- Subscription key: 3becf0ce306f41a1ae94077c16798187 (Hybris)
- DKE key: 32895bd5b86e4a5ab6e94fb0bc8ae234
- Store pages in sitemap: coop.se/sitemap_pages.xml (801 stores)
- Store IDs are numeric (e.g., 1355 for Coop Eken Gävle)
- Product search path: /search/products/promotion (requires Bearer token)

To implement, use Playwright to:
1. Load coop.se/butiker-erbjudanden/coop/STORE-NAME/
2. Wait for DKE offers XHR to complete
3. Intercept the JSON response
"""

import logging

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper

logger = logging.getLogger(__name__)

COOP_STORES: dict[str, dict] = {
    "coop-stockholm-stadion": {"name": "Coop Stadion Stockholm", "city": "Stockholm", "type": "coop", "store_id": "206801"},
    "coop-stockholm-karlaplan": {"name": "Coop Karlaplan", "city": "Stockholm", "type": "coop", "store_id": "206802"},
    "coop-goteborg-nordstan": {"name": "Coop Nordstan", "city": "Göteborg", "type": "coop", "store_id": "206810"},
    "coop-malmo-triangeln": {"name": "Coop Triangeln", "city": "Malmö", "type": "coop", "store_id": "206820"},
    "coop-uppsala-centrum": {"name": "Coop Uppsala Centrum", "city": "Uppsala", "type": "coop", "store_id": "206830"},
    "coop-linkoping": {"name": "Stora Coop Linköping", "city": "Linköping", "type": "stora-coop", "store_id": "206840"},
    "coop-orebro": {"name": "Stora Coop Örebro", "city": "Örebro", "type": "stora-coop", "store_id": "206850"},
    "coop-vasteras": {"name": "Coop Västerås", "city": "Västerås", "type": "coop", "store_id": "206860"},
    "coop-umea": {"name": "Coop Umeå", "city": "Umeå", "type": "coop", "store_id": "206870"},
    "coop-gavle-eken": {"name": "Coop Eken Gävle", "city": "Gävle", "type": "coop", "store_id": "1355"},
}


class CoopScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        logger.warning(
            f"Coop scraper not yet implemented — requires Playwright for "
            f"client-side rendered offers. Returning 0 offers for {store_id}."
        )
        return []

    def get_store_info(self, store_id: str) -> dict:
        return COOP_STORES.get(store_id, {})
