"""Lidl grocery store offer scraper.

Uses two Schwarz/Lidl APIs:
1. Gridboxes API (lidl.se/p/api/gridboxes/SE/sv) — weekly specials, mostly non-food
2. Leaflets API (endpoints.leaflets.schwarz) — reklamblad metadata (titles, dates, IDs)

LIMITATION: The gridboxes API currently returns mostly non-food items.
Food offers from the reklamblad (weekly flyer) are only accessible via the
Lidl Plus app or client-side JS rendering. The leaflet detail/pages endpoint
is not publicly accessible.

Lidl offers are national — same for all stores in Sweden.

Known API details:
- Gridboxes: GET lidl.se/p/api/gridboxes/SE/sv → JSON array of products
- Leaflet overview: GET endpoints.leaflets.schwarz/v4/overview?subcategory_id=be7864da-6d56-11e8-8e93-005056ab0fb6
- Leaflet category "Reklamblad": be7864da-6d56-11e8-8e93-005056ab0fb6
- Category pages (HTML, no product data): lidl.se/c/mandag-soendag/a10090968
"""

import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper
from backend.scrapers.ica_maxi import classify_category

logger = logging.getLogger(__name__)

GRIDBOXES_URL = "https://www.lidl.se/p/api/gridboxes/SE/sv"
LEAFLETS_URL = "https://endpoints.leaflets.schwarz/v4/overview"
LEAFLET_SUBCATEGORY_ID = "be7864da-6d56-11e8-8e93-005056ab0fb6"

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

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


class LidlScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        logger.info(f"Fetching Lidl offers (national, tagged as {store_id})")
        offers = []

        # Source 1: Gridboxes API — weekly specials
        gridbox_offers = await self._fetch_gridboxes(store_id)
        offers.extend(gridbox_offers)

        if not offers:
            logger.warning(
                "Lidl: 0 offers from gridboxes API — food offers may only be "
                "available via Lidl Plus app this week"
            )

        return offers

    async def _fetch_gridboxes(self, store_id: str) -> list[Offer]:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(GRIDBOXES_URL, headers=BASE_HEADERS)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Lidl gridboxes API failed: {e}")
            return []

        if not isinstance(data, list):
            return []

        # Filter to unique products only
        unique = [item for item in data if item.get("productType") == "RETAIL_HEAD"]
        logger.info(f"Lidl gridboxes: {len(data)} items, {len(unique)} unique")

        offers = []
        for item in unique:
            offer = self._parse_gridbox_item(item, store_id)
            if offer:
                offers.append(offer)

        return offers

    def _parse_gridbox_item(self, item: dict, store_id: str) -> Optional[Offer]:
        try:
            name = item.get("fullTitle", "")
            if not name:
                return None

            price_data = item.get("price", {})
            offer_price = float(price_data.get("price", 0))
            if offer_price <= 0:
                return None

            brand_data = item.get("brand", {})
            brand = brand_data.get("name") if isinstance(brand_data, dict) else None

            category_raw = item.get("category", "other")
            category = classify_category(name, brand or "") if category_raw == "Food" else "other"

            # Dates from unix timestamps
            start_ts = item.get("storeStartDate")
            end_ts = item.get("storeEndDate")
            today = date.today()
            valid_from = datetime.fromtimestamp(start_ts).date() if start_ts else today - timedelta(days=today.weekday())
            valid_to = datetime.fromtimestamp(end_ts).date() if end_ts else valid_from + timedelta(days=6)

            image_url = item.get("image")
            badges = item.get("stockAvailability", {}).get("badgeInfo", {}).get("badges", [])
            badge_text = badges[0].get("text", "") if badges else ""
            requires_membership = "lidl plus" in name.lower() or "plus" in badge_text.lower()

            offer_id = hashlib.md5(f"lidl:{name}:{item.get('productId', '')}".encode()).hexdigest()[:12]

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=name,
                brand=brand,
                category=category,
                offer_price=offer_price,
                original_price=None,
                unit="kr/st",
                quantity_deal=None,
                max_per_household=None,
                valid_from=valid_from,
                valid_to=valid_to,
                requires_membership=requires_membership,
                image_url=image_url,
                raw_text=f"{name} | {offer_price} kr | {badge_text}",
            )
        except Exception as e:
            logger.debug(f"Failed to parse Lidl item: {e}")
            return None

    def get_store_info(self, store_id: str) -> dict:
        return LIDL_STORES.get(store_id, {})
