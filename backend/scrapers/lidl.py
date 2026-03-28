"""Lidl grocery store offer scraper.

Uses Lidl's gridboxes API: https://www.lidl.se/p/api/gridboxes/SE/sv
Returns structured JSON with product data including prices, dates, and categories.

LIMITATION: The API currently returns mostly NonFood items (~25 products).
Food offers may be loaded from a separate endpoint or are only available
via the Lidl Plus app. The scraper works but may return few or zero food offers
depending on the week.

Lidl offers are national (same for all stores in Sweden).
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

LIDL_API_URL = "https://www.lidl.se/p/api/gridboxes/SE/sv"

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

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(LIDL_API_URL, headers=BASE_HEADERS)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Lidl API request failed: {e}")
            return []

        if not isinstance(data, list):
            logger.warning(f"Lidl API returned unexpected type: {type(data)}")
            return []

        # Filter to unique products only (skip variants)
        unique = [item for item in data if item.get("productType") == "RETAIL_HEAD"]
        logger.info(f"Lidl API returned {len(data)} items, {len(unique)} unique products")

        offers = []
        for item in unique:
            offer = self._parse_item(item, store_id)
            if offer:
                offers.append(offer)

        logger.info(f"Parsed {len(offers)} Lidl offers")
        if not offers:
            logger.warning("Lidl returned 0 usable offers — food items may not be in the gridboxes API this week")

        return offers

    def _parse_item(self, item: dict, store_id: str) -> Optional[Offer]:
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
            if category_raw == "Food":
                category = classify_category(name, brand or "")
            else:
                category = "other"

            # Parse dates from unix timestamps
            start_ts = item.get("storeStartDate")
            end_ts = item.get("storeEndDate")
            today = date.today()

            if start_ts:
                valid_from = datetime.fromtimestamp(start_ts).date()
            else:
                valid_from = today - timedelta(days=today.weekday())

            if end_ts:
                valid_to = datetime.fromtimestamp(end_ts).date()
            else:
                valid_to = valid_from + timedelta(days=6)

            # Image
            image_url = item.get("image")

            # Badge text for raw_text
            badges = item.get("stockAvailability", {}).get("badgeInfo", {}).get("badges", [])
            badge_text = badges[0].get("text", "") if badges else ""

            # Lidl Plus
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
