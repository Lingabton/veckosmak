"""Willys offer scraper.

Fetches weekly offers from the Willys JSON API.
API endpoint: https://www.willys.se/search/oql?q=*&type=offers&size=100&store=STORE_ID
"""

import asyncio
import hashlib
import logging
import re
from datetime import date, timedelta
from typing import Any, Optional

import httpx

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper
from backend.scrapers.ica_maxi import classify_category

logger = logging.getLogger(__name__)

# Major Willys stores across Sweden, keyed by store ID used in the API.
# Store IDs sourced from willys.se store locator.
WILLYS_STORES: dict[str, dict[str, str]] = {
    "willys-2110": {
        "name": "Willys Södermalm",
        "city": "Stockholm",
        "address": "Rosenlundsgatan 36, Stockholm",
    },
    "willys-2063": {
        "name": "Willys Liljeholmen",
        "city": "Stockholm",
        "address": "Liljeholmsvägen 18, Stockholm",
    },
    "willys-2098": {
        "name": "Willys Fridhemsplan",
        "city": "Stockholm",
        "address": "Sankt Eriksgatan 45, Stockholm",
    },
    "willys-2193": {
        "name": "Willys Barkarby",
        "city": "Järfälla",
        "address": "Enköpingsvägen 11, Järfälla",
    },
    "willys-2140": {
        "name": "Willys Angered",
        "city": "Göteborg",
        "address": "Angered Centrum, Göteborg",
    },
    "willys-2003": {
        "name": "Willys Backaplan",
        "city": "Göteborg",
        "address": "Backavägen 3, Göteborg",
    },
    "willys-2005": {
        "name": "Willys Frölunda Torg",
        "city": "Göteborg",
        "address": "Frölunda Torg, Västra Frölunda",
    },
    "willys-2133": {
        "name": "Willys Sisjön",
        "city": "Göteborg",
        "address": "Sisjö Entrégata 10, Askim",
    },
    "willys-2120": {
        "name": "Willys Malmö Jägersro",
        "city": "Malmö",
        "address": "Jägersrovägen 150, Malmö",
    },
    "willys-2013": {
        "name": "Willys Malmö Dalaplan",
        "city": "Malmö",
        "address": "Föreningsgatan 83, Malmö",
    },
    "willys-2167": {
        "name": "Willys Lund",
        "city": "Lund",
        "address": "Fjelievägen 40, Lund",
    },
    "willys-2130": {
        "name": "Willys Uppsala Boländerna",
        "city": "Uppsala",
        "address": "Rapsgatan 7, Uppsala",
    },
    "willys-2114": {
        "name": "Willys Linköping",
        "city": "Linköping",
        "address": "Tornbyvägen 1, Linköping",
    },
    "willys-2018": {
        "name": "Willys Västerås",
        "city": "Västerås",
        "address": "Hälla Shopping, Västerås",
    },
    "willys-2112": {
        "name": "Willys Örebro",
        "city": "Örebro",
        "address": "Södermalmsplan 3, Örebro",
    },
    "willys-2027": {
        "name": "Willys Helsingborg",
        "city": "Helsingborg",
        "address": "Väla Centrum, Helsingborg",
    },
    "willys-2135": {
        "name": "Willys Norrköping",
        "city": "Norrköping",
        "address": "Ingelstavägen, Norrköping",
    },
    "willys-2022": {
        "name": "Willys Jönköping",
        "city": "Jönköping",
        "address": "A6 Center, Jönköping",
    },
    "willys-2052": {
        "name": "Willys Umeå",
        "city": "Umeå",
        "address": "Verkstadsgatan 5, Umeå",
    },
    "willys-2049": {
        "name": "Willys Gävle",
        "city": "Gävle",
        "address": "Norra Kungsgatan 2, Gävle",
    },
}

# Number of retry attempts for HTTP requests.
_MAX_RETRIES = 3

# Base delay in seconds for exponential backoff.
_BACKOFF_BASE = 1.0

# API endpoint template.
_API_URL = "https://www.willys.se/search/oql"


def _generate_offer_id(store_id: str, product_name: str) -> str:
    """Generate a stable, deterministic ID from store + product name."""
    raw = f"{store_id}:{product_name}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def _parse_willys_price(price_value: Any) -> Optional[float]:
    """Parse a price value from the Willys API response.

    The API may return prices as floats, ints, or formatted strings
    like "49:90" or "49,90".
    """
    if price_value is None:
        return None

    if isinstance(price_value, (int, float)):
        return float(price_value)

    text = str(price_value).strip()
    # "49:90" or "49,90" -> 49.90
    text = text.replace(":", ".").replace(",", ".").replace("kr", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def _extract_unit(product: dict) -> str:
    """Determine the price unit from API product data."""
    comparison_price = product.get("comparativePrice", "") or ""
    price_unit = product.get("priceUnit", "") or ""

    comp_lower = str(comparison_price).lower()
    unit_lower = str(price_unit).lower()

    if "kg" in comp_lower or "kg" in unit_lower:
        return "kr/kg"
    if "förp" in comp_lower or "förp" in unit_lower:
        return "kr/förp"
    if "lit" in comp_lower or "lit" in unit_lower or "/l" in comp_lower:
        return "kr/l"
    return "kr/st"


def _parse_quantity_deal(product: dict) -> Optional[str]:
    """Extract multi-buy deal text (e.g. '2 för 50 kr') from the product."""
    promo_text = product.get("potpiece", "") or product.get("promoText", "") or ""
    if not promo_text:
        return None

    # Match patterns like "2 för 50", "3 för 100 kr"
    match = re.search(r"(\d+)\s*för\s*(\d+(?:[.,]\d+)?)", promo_text)
    if match:
        count = match.group(1)
        total = match.group(2).replace(",", ".")
        return f"{count} för {total} kr"

    return None


def _parse_max_per_household(product: dict) -> Optional[int]:
    """Extract max-purchase-per-household limit."""
    for field in ("promoText", "potpiece", "description"):
        text = str(product.get(field, "") or "")
        match = re.search(r"[Mm]ax\s*(\d+)\s*(?:köp|st|per)\s*/?\s*hushåll", text)
        if match:
            return int(match.group(1))
    return None


def _parse_date(date_str: Optional[str], fallback: date) -> date:
    """Parse an ISO-8601 date string, returning *fallback* on failure."""
    if not date_str:
        return fallback
    try:
        # API dates may be ISO "2026-03-23" or "2026-03-23T00:00:00"
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return fallback


def _is_membership_offer(product: dict) -> bool:
    """Check whether the offer requires Willys Plus membership."""
    for field in ("promoText", "potpiece", "description", "offerType"):
        text = str(product.get(field, "") or "").lower()
        if "plus" in text or "medlem" in text:
            return True
    return False


class WillysScraper(AbstractScraper):
    """Scraper for Willys grocery stores using their public JSON API."""

    BASE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Accept-Language": "sv-SE,sv;q=0.9",
    }

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        """Fetch current offers for a Willys store.

        Args:
            store_id: A key from ``WILLYS_STORES`` (e.g. ``"willys-2110"``).

        Returns:
            A list of parsed ``Offer`` objects.  Returns an empty list if the
            request fails after all retries.
        """
        store = WILLYS_STORES.get(store_id)
        if not store:
            raise ValueError(
                f"Unknown Willys store: {store_id}. "
                f"Valid IDs: {', '.join(sorted(WILLYS_STORES))}"
            )

        # The API uses the numeric portion of the store ID.
        numeric_id = store_id.replace("willys-", "")

        logger.info("Fetching Willys offers for %s (%s)", store["name"], store_id)

        data = await self._fetch_with_retry(numeric_id)
        if data is None:
            return []

        products = self._extract_products(data)
        logger.info("API returned %d product entries", len(products))

        if not products:
            logger.warning(
                "No products found in API response for %s — "
                "the API structure may have changed",
                store_id,
            )
            return []

        # Default validity: current week (Monday to Sunday).
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        offers: list[Offer] = []
        for product in products:
            offer = self._parse_product(product, store_id, week_start, week_end)
            if offer is not None:
                offers.append(offer)

        logger.info(
            "Parsed %d offers from %d products for %s",
            len(offers),
            len(products),
            store_id,
        )
        return offers

    def get_store_info(self, store_id: str) -> dict:
        """Return store metadata for *store_id*."""
        return WILLYS_STORES.get(store_id, {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_with_retry(self, numeric_store_id: str) -> Optional[dict]:
        """Fetch the offers JSON with retry + exponential backoff."""
        params = {
            "q": "*",
            "type": "offers",
            "size": 100,
            "store": numeric_store_id,
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True, timeout=20
                ) as client:
                    resp = await client.get(
                        _API_URL,
                        params=params,
                        headers=self.BASE_HEADERS,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_error = exc
                logger.warning(
                    "Willys API attempt %d/%d failed: %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    delay = _BACKOFF_BASE * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "Willys API request error on attempt %d/%d: %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    delay = _BACKOFF_BASE * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        logger.error(
            "All %d Willys API attempts failed. Last error: %s",
            _MAX_RETRIES,
            last_error,
        )
        return None

    @staticmethod
    def _extract_products(data: dict) -> list[dict]:
        """Navigate the API response structure to find the product list.

        Willys' OQL endpoint may wrap results in different ways.  We try
        several common paths to find the actual product array.
        """
        # Most common: data -> results -> [items]
        if isinstance(data, dict):
            for key in ("results", "hits", "products", "items", "data"):
                if key in data:
                    candidate = data[key]
                    if isinstance(candidate, list):
                        return candidate
                    # Nested: results -> items
                    if isinstance(candidate, dict):
                        for inner_key in ("items", "results", "products"):
                            if inner_key in candidate and isinstance(
                                candidate[inner_key], list
                            ):
                                return candidate[inner_key]

        # Fallback: the response itself is a list.
        if isinstance(data, list):
            return data

        logger.warning("Could not locate product list in API response structure")
        return []

    @staticmethod
    def _parse_product(
        product: dict,
        store_id: str,
        default_from: date,
        default_to: date,
    ) -> Optional[Offer]:
        """Parse a single product dict from the API into an Offer."""
        try:
            # Product name — try several possible field names.
            name = (
                product.get("name")
                or product.get("productName")
                or product.get("title")
                or ""
            ).strip()

            if not name:
                return None

            brand = (product.get("brand") or product.get("manufacturer") or "").strip()
            brand = brand or None

            # Prices
            offer_price = _parse_willys_price(
                product.get("offerPrice")
                or product.get("price")
                or product.get("priceValue")
            )
            if offer_price is None or offer_price <= 0:
                # Skip entries without a valid offer price.
                return None

            original_price = _parse_willys_price(
                product.get("originalPrice")
                or product.get("regularPrice")
                or product.get("savingsPrice")
            )

            # Quantity deal (multi-buy).
            quantity_deal = _parse_quantity_deal(product)

            # If there is a quantity deal, adjust offer_price to per-unit.
            if quantity_deal:
                match = re.search(
                    r"(\d+)\s*för\s*(\d+(?:\.\d+)?)", quantity_deal
                )
                if match:
                    count = int(match.group(1))
                    total = float(match.group(2))
                    if count > 0:
                        offer_price = round(total / count, 2)

            unit = _extract_unit(product)
            max_per_household = _parse_max_per_household(product)
            requires_membership = _is_membership_offer(product)

            # Dates
            valid_from = _parse_date(
                product.get("startDate") or product.get("offerStartDate"),
                default_from,
            )
            valid_to = _parse_date(
                product.get("endDate") or product.get("offerEndDate"),
                default_to,
            )

            # Category
            category = classify_category(name, brand or "")

            # Image
            image_url = product.get("imageUrl") or product.get("image") or None
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.willys.se{image_url}"

            # Stable ID
            offer_id = _generate_offer_id(store_id, name)

            # Raw text for debugging
            promo_text = product.get("promoText", "") or ""
            raw_text = f"{name} | {brand or ''} | {offer_price} {unit} | {promo_text}"

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=name,
                brand=brand,
                category=category,
                offer_price=offer_price,
                original_price=original_price,
                unit=unit,
                quantity_deal=quantity_deal,
                max_per_household=max_per_household,
                valid_from=valid_from,
                valid_to=valid_to,
                requires_membership=requires_membership,
                image_url=image_url,
                raw_text=raw_text,
            )
        except Exception:
            logger.error(
                "Failed to parse Willys product: %s",
                product.get("name", "<unknown>"),
                exc_info=True,
            )
            return None
