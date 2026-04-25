"""Coop grocery store offer scraper.

Uses Coop's DKE offers API:
    GET https://external.api.coop.se/dke/offers/{storeId}?api-version=v2&clustered=true
    Header: Ocp-Apim-Subscription-Key: 32895bd5b86e4a5ab6e94fb0bc8ae234

Returns JSON array of offer objects with product info, prices, and dates.
Store IDs are numeric (e.g., 206403 for Coop Eken Gävle).
"""

import hashlib
import logging
import re
from datetime import date, datetime
from typing import Optional

import httpx

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper
from backend.scrapers.ica_maxi import classify_category

logger = logging.getLogger(__name__)

import os

DKE_BASE_URL = "https://external.api.coop.se/dke/offers"
DKE_KEY = os.environ.get("COOP_DKE_KEY", "32895bd5b86e4a5ab6e94fb0bc8ae234")

COOP_STORES: dict[str, dict] = {
    "coop-206403": {"name": "Coop Eken Gävle", "city": "Gävle", "type": "coop", "dke_id": "206403"},
    "coop-206801": {"name": "Coop Stadion Stockholm", "city": "Stockholm", "type": "coop", "dke_id": "206801"},
    "coop-206810": {"name": "Coop Nordstan Göteborg", "city": "Göteborg", "type": "coop", "dke_id": "206810"},
    "coop-206820": {"name": "Coop Triangeln Malmö", "city": "Malmö", "type": "coop", "dke_id": "206820"},
    "coop-206830": {"name": "Coop Uppsala Centrum", "city": "Uppsala", "type": "coop", "dke_id": "206830"},
    "coop-201301": {"name": "Stora Coop Linköping", "city": "Linköping", "type": "stora-coop", "dke_id": "201301"},
    "coop-201401": {"name": "Stora Coop Örebro", "city": "Örebro", "type": "stora-coop", "dke_id": "201401"},
    "coop-206860": {"name": "Coop Västerås", "city": "Västerås", "type": "coop", "dke_id": "206860"},
    "coop-206870": {"name": "Coop Umeå", "city": "Umeå", "type": "coop", "dke_id": "206870"},
    "coop-201101": {"name": "Stora Coop Valbo", "city": "Gävle", "type": "stora-coop", "dke_id": "201101"},
    "coop-206501": {"name": "Coop Karlstad", "city": "Karlstad", "type": "coop", "dke_id": "206501"},
    "coop-206601": {"name": "Coop Jönköping", "city": "Jönköping", "type": "coop", "dke_id": "206601"},
    "coop-206701": {"name": "Coop Helsingborg", "city": "Helsingborg", "type": "coop", "dke_id": "206701"},
    "coop-206901": {"name": "Coop Sundsvall", "city": "Sundsvall", "type": "coop", "dke_id": "206901"},
    "coop-207001": {"name": "Coop Luleå", "city": "Luleå", "type": "coop", "dke_id": "207001"},
}

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Ocp-Apim-Subscription-Key": DKE_KEY,
}


class CoopScraper(AbstractScraper):

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        store = COOP_STORES.get(store_id)
        if not store:
            logger.warning(f"Unknown Coop store: {store_id}")
            return []

        dke_id = store.get("dke_id", store_id.split("-")[-1])
        url = f"{DKE_BASE_URL}/{dke_id}?api-version=v2&clustered=true"
        logger.info(f"Fetching Coop offers for {store.get('name')} (DKE ID: {dke_id})")

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers=BASE_HEADERS)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Coop API request failed: {e}")
            return []

        if not isinstance(data, list):
            logger.warning(f"Coop API returned unexpected type: {type(data)}")
            return []

        logger.info(f"Coop API returned {len(data)} offer clusters")

        offers = []
        for item in data:
            offer = self._parse_offer(item, store_id)
            if offer:
                offers.append(offer)
            # Also parse cluster interior offers (variants)
            for sub in item.get("clusterInteriorOffers", []):
                sub_offer = self._parse_offer(sub, store_id)
                if sub_offer and sub_offer.id not in {o.id for o in offers}:
                    offers.append(sub_offer)

        logger.info(f"Parsed {len(offers)} Coop offers for {store_id}")
        return offers

    def _parse_offer(self, item: dict, store_id: str) -> Optional[Offer]:
        try:
            content = item.get("content", {})
            price_info = item.get("priceInformation", {})

            name = content.get("title", "")
            if not name:
                return None

            brand = content.get("brand", "")
            offer_price = float(price_info.get("discountValue", 0))
            if offer_price <= 0:
                return None

            # Quantity deal
            min_amount = price_info.get("minimumAmount", 1)
            unit = price_info.get("unit", "st")
            quantity_deal = None
            if min_amount and min_amount > 1:
                total = offer_price * min_amount
                quantity_deal = f"{min_amount} för {int(total)} kr"
                # offer_price is per unit already

            # Membership
            is_member = price_info.get("isMemberPrice", False)

            # Dates
            start_str = item.get("campaignStartDate", "")
            end_str = item.get("campaignEndDate", "")
            try:
                valid_from = datetime.fromisoformat(start_str[:10]).date() if start_str else date.today()
                valid_to = datetime.fromisoformat(end_str[:10]).date() if end_str else valid_from
            except (ValueError, TypeError):
                valid_from = date.today()
                valid_to = valid_from

            # Image
            image_url = content.get("imageUrl", "")
            if image_url and image_url.startswith("//"):
                image_url = f"https:{image_url}"

            # Category
            category_group = item.get("categoryGroup", "")
            category = classify_category(name, brand)
            # Override with Coop's own category if it maps
            coop_cat_map = {
                "Kött": "meat", "Chark": "meat", "Fågel": "meat",
                "Fisk": "fish", "Skaldjur": "fish",
                "Mejeri": "dairy", "Ost": "dairy",
                "Frukt": "produce", "Grönt": "produce",
                "Kolonial": "pantry", "Skafferi": "pantry",
                "Bröd": "bakery", "Bageri": "bakery",
                "Fryst": "frozen",
            }
            for coop_name, our_cat in coop_cat_map.items():
                if coop_name.lower() in category_group.lower():
                    category = our_cat
                    break

            # Comparative price for original
            comp_price_text = content.get("comparativePriceText", "")
            original_price = None

            offer_id = hashlib.md5(f"coop:{store_id}:{name}:{item.get('id', '')}".encode()).hexdigest()[:12]

            raw_text = f"{name} | {brand} | {offer_price} kr/{unit} | {category_group}"

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=name,
                brand=brand or None,
                category=category,
                offer_price=offer_price,
                original_price=original_price,
                unit=f"kr/{unit}",
                quantity_deal=quantity_deal,
                max_per_household=None,
                valid_from=valid_from,
                valid_to=valid_to,
                requires_membership=is_member,
                image_url=image_url or None,
                raw_text=raw_text,
            )

        except Exception as e:
            logger.debug(f"Failed to parse Coop offer: {e}")
            return None

    def get_store_info(self, store_id: str) -> dict:
        return COOP_STORES.get(store_id, {})
