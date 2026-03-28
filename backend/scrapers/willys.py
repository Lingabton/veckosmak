"""Willys offer scraper.

Fetches weekly offers from the Willys campaigns API.
API endpoint: https://www.willys.se/search/campaigns?storeId=STORE_ID&size=100&page=0

Willys is part of Axfood and shares the same platform as Hemköp.
The API returns paginated results with product data, prices, and promotion info.
"""

import hashlib
import logging
from datetime import date, timedelta
from typing import Optional

import httpx

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper
from backend.scrapers.ica_maxi import classify_category

logger = logging.getLogger(__name__)

# Willys stores — store ID is the numeric part after "willys-"
WILLYS_STORES: dict[str, dict] = {
    "willys-2110": {"name": "Willys Södermalm", "city": "Stockholm", "type": "willys", "store_api_id": "2110"},
    "willys-2063": {"name": "Willys Liljeholmen", "city": "Stockholm", "type": "willys", "store_api_id": "2063"},
    "willys-2107": {"name": "Willys Kungsholmen", "city": "Stockholm", "type": "willys", "store_api_id": "2107"},
    "willys-2005": {"name": "Willys Angered", "city": "Göteborg", "type": "willys", "store_api_id": "2005"},
    "willys-2032": {"name": "Willys Frölunda Torg", "city": "Göteborg", "type": "willys", "store_api_id": "2032"},
    "willys-2037": {"name": "Willys Gamlestaden", "city": "Göteborg", "type": "willys", "store_api_id": "2037"},
    "willys-2068": {"name": "Willys Mölndal", "city": "Göteborg", "type": "willys", "store_api_id": "2068"},
    "willys-2069": {"name": "Willys Malmö Jägersro", "city": "Malmö", "type": "willys", "store_api_id": "2069"},
    "willys-2053": {"name": "Willys Malmö Mobilia", "city": "Malmö", "type": "willys", "store_api_id": "2053"},
    "willys-2064": {"name": "Willys Lund", "city": "Lund", "type": "willys", "store_api_id": "2064"},
    "willys-2125": {"name": "Willys Uppsala Boländerna", "city": "Uppsala", "type": "willys", "store_api_id": "2125"},
    "willys-2065": {"name": "Willys Linköping", "city": "Linköping", "type": "willys", "store_api_id": "2065"},
    "willys-2131": {"name": "Willys Västerås", "city": "Västerås", "type": "willys", "store_api_id": "2131"},
    "willys-2098": {"name": "Willys Örebro", "city": "Örebro", "type": "willys", "store_api_id": "2098"},
    "willys-2043": {"name": "Willys Helsingborg", "city": "Helsingborg", "type": "willys", "store_api_id": "2043"},
    "willys-2089": {"name": "Willys Norrköping", "city": "Norrköping", "type": "willys", "store_api_id": "2089"},
    "willys-2055": {"name": "Willys Jönköping", "city": "Jönköping", "type": "willys", "store_api_id": "2055"},
    "willys-2126": {"name": "Willys Umeå", "city": "Umeå", "type": "willys", "store_api_id": "2126"},
    "willys-2036": {"name": "Willys Gävle", "city": "Gävle", "type": "willys", "store_api_id": "2036"},
    "willys-2056": {"name": "Willys Karlstad", "city": "Karlstad", "type": "willys", "store_api_id": "2056"},
}

BASE_URL = "https://www.willys.se/search/campaigns"
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


class WillysScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        store = WILLYS_STORES.get(store_id)
        if not store:
            logger.warning(f"Unknown Willys store: {store_id}")
            return []

        api_store_id = store.get("store_api_id", store_id.split("-")[-1])
        logger.info(f"Fetching Willys offers for {store.get('name')} (API ID: {api_store_id})")

        all_results = []
        page = 0

        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            while True:
                try:
                    resp = await client.get(
                        BASE_URL,
                        params={"storeId": api_store_id, "size": 100, "page": page},
                        headers=BASE_HEADERS,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as e:
                    logger.error(f"Willys API error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Willys request failed: {e}")
                    break

                results = data.get("results", [])
                if not results:
                    break

                all_results.extend(results)

                pagination = data.get("pagination", {})
                total = pagination.get("totalNumberOfResults", 0)
                if len(all_results) >= total:
                    break

                page += 1
                if page > 10:  # Safety limit
                    break

        logger.info(f"Fetched {len(all_results)} raw Willys offers")

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        offers = []
        for item in all_results:
            offer = self._parse_item(item, store_id, week_start, week_end)
            if offer:
                offers.append(offer)

        logger.info(f"Parsed {len(offers)} Willys offers for {store_id}")
        return offers

    def _parse_item(self, item: dict, store_id: str, valid_from: date, valid_to: date) -> Optional[Offer]:
        try:
            name = item.get("name", "")
            if not name:
                return None

            code = item.get("code", "")
            regular_price = float(item.get("priceValue", 0))
            savings = float(item.get("savingsAmount", 0))

            # Get promotion info
            promos = item.get("potentialPromotions", [])
            promo = promos[0] if promos else {}
            promo_price_data = promo.get("price", {})
            offer_price = float(promo_price_data.get("value", regular_price))
            campaign_type = promo.get("campaignType", "")
            condition_label = promo.get("conditionLabel", "")

            # If no promo price, use regular minus savings
            if offer_price == 0 and savings > 0:
                offer_price = regular_price - savings
            elif offer_price == 0:
                offer_price = regular_price

            original_price = regular_price if savings > 0 else None

            # Determine unit
            compare_price = item.get("comparePrice", "")
            compare_unit = item.get("comparePriceUnit", "")
            unit = "kr/st"
            if compare_unit:
                unit = f"kr/{compare_unit.lower()}"

            # Parse quantity deal from condition label
            quantity_deal = None
            if condition_label and ("för" in condition_label.lower() or "köp" in condition_label.lower()):
                quantity_deal = condition_label

            # Membership
            requires_membership = campaign_type == "LOYALTY"

            # Image
            img_data = item.get("image", {})
            image_url = img_data.get("url", "") if isinstance(img_data, dict) else None

            # Category
            category = classify_category(name)

            # Stable ID
            offer_id = hashlib.md5(f"{store_id}:{name}:{code}".encode()).hexdigest()[:12]

            raw_text = f"{name} | {condition_label} | {regular_price} → {offer_price}"

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=name,
                brand=None,
                category=category,
                offer_price=offer_price,
                original_price=original_price,
                unit=unit,
                quantity_deal=quantity_deal,
                max_per_household=None,
                valid_from=valid_from,
                valid_to=valid_to,
                requires_membership=requires_membership,
                image_url=image_url,
                raw_text=raw_text,
            )

        except Exception as e:
            logger.debug(f"Failed to parse Willys item: {e}")
            return None

    def get_store_info(self, store_id: str) -> dict:
        return WILLYS_STORES.get(store_id, {})
