"""Coop grocery store offer scraper.

STATUS: NOT YET WORKING — Coop's offers are served via their DKE API at
external.api.coop.se/dke/offers/v1/store-offers?storeId=STORE_ID

The API requires:
- Header: Ocp-Apim-Subscription-Key: 32895bd5b86e4a5ab6e94fb0bc8ae234
- Header: Authorization: Bearer <oauth_token>

Without a Bearer token, the API returns 200 but with an empty body.
The OAuth token endpoint is at external.api.coop.se/ecommerce/coop/oauth/token
but requires client credentials not exposed in the frontend.

Options to implement:
1. Headless browser (Playwright) to capture XHR responses from store pages
2. Reverse-engineer auth via Coop mobile app with MITM proxy
3. Third-party aggregator (matspar.se, allahushall.se)
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
            f"Coop scraper not yet implemented — their DKE API requires OAuth "
            f"Bearer token. Returning 0 offers for {store_id}."
        )
        return []

    def get_store_info(self, store_id: str) -> dict:
        return COOP_STORES.get(store_id, {})
