"""Coop grocery store offer scraper.

Fetches weekly offers from the Coop API at:
    https://www.coop.se/api/offers?storeId=STORE_ID

Supports all Coop store types: Stora Coop, Coop Forum, Coop Konsum,
Coop Extra, and Coop Nära.
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

# ~20 major Coop stores across Sweden, covering all store types
COOP_STORES: dict[str, dict[str, str]] = {
    "coop-forum-nacka": {
        "name": "Coop Forum Nacka",
        "city": "Nacka",
        "address": "Värmdövägen 691, Nacka",
        "type": "coop-forum",
        "store_api_id": "011500",
        "scraper_class": "CoopScraper",
    },
    "coop-forum-barkaby": {
        "name": "Coop Forum Barkarby",
        "city": "Järfälla",
        "address": "Enebybergsvägen 19, Järfälla",
        "type": "coop-forum",
        "store_api_id": "011320",
        "scraper_class": "CoopScraper",
    },
    "coop-forum-Uppsala": {
        "name": "Coop Forum Uppsala",
        "city": "Uppsala",
        "address": "Stålgatan 10, Uppsala",
        "type": "coop-forum",
        "store_api_id": "013720",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-norrkoping": {
        "name": "Stora Coop Norrköping",
        "city": "Norrköping",
        "address": "Fjärilsgatan 2, Norrköping",
        "type": "stora-coop",
        "store_api_id": "062360",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-linkoping": {
        "name": "Stora Coop Linköping",
        "city": "Linköping",
        "address": "Mörtlösa, Linköping",
        "type": "stora-coop",
        "store_api_id": "062060",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-umea": {
        "name": "Stora Coop Umeå",
        "city": "Umeå",
        "address": "Signalvägen 4, Umeå",
        "type": "stora-coop",
        "store_api_id": "082960",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-orebro": {
        "name": "Stora Coop Örebro",
        "city": "Örebro",
        "address": "Marieberg Galleria, Örebro",
        "type": "stora-coop",
        "store_api_id": "062860",
        "scraper_class": "CoopScraper",
    },
    "coop-konsum-sodertorn": {
        "name": "Coop Konsum Södertörn",
        "city": "Stockholm",
        "address": "Dalarövägen 52, Handen",
        "type": "coop-konsum",
        "store_api_id": "014060",
        "scraper_class": "CoopScraper",
    },
    "coop-konsum-goteborg-nordstan": {
        "name": "Coop Konsum Nordstan",
        "city": "Göteborg",
        "address": "Nordstadstorget, Göteborg",
        "type": "coop-konsum",
        "store_api_id": "042060",
        "scraper_class": "CoopScraper",
    },
    "coop-konsum-malmo": {
        "name": "Coop Konsum Malmö",
        "city": "Malmö",
        "address": "Södra Förstadsgatan, Malmö",
        "type": "coop-konsum",
        "store_api_id": "052060",
        "scraper_class": "CoopScraper",
    },
    "coop-konsum-lund": {
        "name": "Coop Konsum Lund",
        "city": "Lund",
        "address": "Mårtenstorget, Lund",
        "type": "coop-konsum",
        "store_api_id": "053260",
        "scraper_class": "CoopScraper",
    },
    "coop-extra-helsingborg": {
        "name": "Coop Extra Helsingborg",
        "city": "Helsingborg",
        "address": "Ödåkravägen 31, Helsingborg",
        "type": "coop-extra",
        "store_api_id": "053860",
        "scraper_class": "CoopScraper",
    },
    "coop-extra-sundsvall": {
        "name": "Coop Extra Sundsvall",
        "city": "Sundsvall",
        "address": "Bergsgatan 61, Sundsvall",
        "type": "coop-extra",
        "store_api_id": "072060",
        "scraper_class": "CoopScraper",
    },
    "coop-extra-gavle": {
        "name": "Coop Extra Gävle",
        "city": "Gävle",
        "address": "Valbo Köpcentrum, Gävle",
        "type": "coop-extra",
        "store_api_id": "073060",
        "scraper_class": "CoopScraper",
    },
    "coop-extra-jonkoping": {
        "name": "Coop Extra Jönköping",
        "city": "Jönköping",
        "address": "A6 Center, Jönköping",
        "type": "coop-extra",
        "store_api_id": "064060",
        "scraper_class": "CoopScraper",
    },
    "coop-nara-stockholm-sodermalm": {
        "name": "Coop Nära Södermalm",
        "city": "Stockholm",
        "address": "Götgatan 31, Stockholm",
        "type": "coop-nara",
        "store_api_id": "012060",
        "scraper_class": "CoopScraper",
    },
    "coop-nara-stockholm-vasastan": {
        "name": "Coop Nära Vasastan",
        "city": "Stockholm",
        "address": "Odengatan 42, Stockholm",
        "type": "coop-nara",
        "store_api_id": "012160",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-karlstad": {
        "name": "Stora Coop Karlstad",
        "city": "Karlstad",
        "address": "Bergvik, Karlstad",
        "type": "stora-coop",
        "store_api_id": "066060",
        "scraper_class": "CoopScraper",
    },
    "stora-coop-lulea": {
        "name": "Stora Coop Luleå",
        "city": "Luleå",
        "address": "Storheden, Luleå",
        "type": "stora-coop",
        "store_api_id": "084060",
        "scraper_class": "CoopScraper",
    },
    "coop-extra-vaxjo": {
        "name": "Coop Extra Växjö",
        "city": "Växjö",
        "address": "Samarkand, Växjö",
        "type": "coop-extra",
        "store_api_id": "065060",
        "scraper_class": "CoopScraper",
    },
}

# Maximum number of retry attempts for API requests
_MAX_RETRIES = 3

# Base delay (seconds) for exponential backoff between retries
_BASE_BACKOFF_SECONDS = 1.0

_API_BASE_URL = "https://www.coop.se/api/offers"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "sv-SE,sv;q=0.9",
    "Referer": "https://www.coop.se/erbjudanden/",
}


def _generate_offer_id(store_id: str, product_name: str) -> str:
    """Generate a stable, deterministic ID from store + product name."""
    raw = f"{store_id}:{product_name}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:12]


def _parse_coop_price(price_data: Any) -> tuple[float, Optional[str], str]:
    """Extract price, quantity deal, and unit from Coop API offer data.

    The API may provide price information in several fields.  This function
    tries common patterns and returns sensible defaults when data is missing.

    Returns:
        (offer_price, quantity_deal, unit)
    """
    if not isinstance(price_data, dict):
        return 0.0, None, "kr/st"

    # Attempt to read structured price fields
    price = _to_float(price_data.get("price") or price_data.get("currentPrice"))

    # Quantity deal ("2 för 50 kr", "3 för 100 kr")
    quantity_deal: Optional[str] = None
    promo_text: str = price_data.get("promotionText") or price_data.get("splash") or ""

    multi_match = re.search(r"(\d+)\s*för\s*(\d+(?:[.,]\d+)?)\s*kr", promo_text)
    if multi_match:
        count = int(multi_match.group(1))
        total = float(multi_match.group(2).replace(",", "."))
        quantity_deal = f"{count} för {int(total)} kr"
        price = price if price else total / count

    # Unit detection
    unit = "kr/st"
    unit_text = (
        price_data.get("unit")
        or price_data.get("unitText")
        or price_data.get("comparisonUnit")
        or promo_text
        or ""
    ).lower()

    if "kg" in unit_text:
        unit = "kr/kg"
    elif "förp" in unit_text:
        unit = "kr/förp"
    elif "/l" in unit_text or "liter" in unit_text:
        unit = "kr/l"

    # Fallback: try parsing price from promo text if still zero
    if not price:
        plain = re.search(r"(\d+(?:[.,]\d+)?)\s*kr", promo_text)
        if plain:
            price = float(plain.group(1).replace(",", "."))

    return price or 0.0, quantity_deal, unit


def _to_float(value: Any) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        if isinstance(value, str):
            value = value.replace(",", ".").strip()
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _parse_dates(
    offer_data: dict,
) -> tuple[date, date]:
    """Extract valid_from / valid_to from an API offer entry.

    Falls back to the current Mon–Sun week if the API does not supply dates.
    """
    today = date.today()
    default_start = today - timedelta(days=today.weekday())  # Monday
    default_end = default_start + timedelta(days=6)  # Sunday

    valid_from = _parse_date_string(
        offer_data.get("startDate") or offer_data.get("validFrom")
    )
    valid_to = _parse_date_string(
        offer_data.get("endDate") or offer_data.get("validTo")
    )

    return valid_from or default_start, valid_to or default_end


def _parse_date_string(value: Any) -> Optional[date]:
    """Parse an ISO-ish date string into a ``date`` object."""
    if not value or not isinstance(value, str):
        return None
    try:
        # Handle both "2026-03-28" and "2026-03-28T00:00:00" formats
        return date.fromisoformat(value[:10])
    except (ValueError, IndexError):
        return None


def _extract_original_price(offer_data: dict) -> Optional[float]:
    """Try to find the original (non-offer) price."""
    for key in ("originalPrice", "ordinaryPrice", "comparePrice", "wasPrice"):
        val = _to_float(offer_data.get(key))
        if val > 0:
            return val

    # Some responses nest it inside a price object
    price_obj = offer_data.get("price") if isinstance(offer_data.get("price"), dict) else {}
    for key in ("originalPrice", "ordinaryPrice", "wasPrice"):
        val = _to_float(price_obj.get(key))
        if val > 0:
            return val

    # Try parsing from descriptive text ("Ord. pris 54,95 kr")
    desc = offer_data.get("description") or offer_data.get("details") or ""
    match = re.search(
        r"[Oo]rd\.?\s*(?:pris)?\s*(\d+(?:[.,]\d+)?)\s*kr", desc
    )
    if match:
        return float(match.group(1).replace(",", "."))

    return None


def _extract_max_per_household(offer_data: dict) -> Optional[int]:
    """Check for household purchase limits."""
    # Direct field
    limit = offer_data.get("maxPerHousehold") or offer_data.get("purchaseLimit")
    if limit and isinstance(limit, (int, float)) and limit > 0:
        return int(limit)

    # From text
    text = offer_data.get("description") or offer_data.get("details") or ""
    match = re.search(r"[Mm]ax\s*(\d+)\s*(?:köp|st|förp)[/ ]*hushåll", text)
    if match:
        return int(match.group(1))

    return None


def _is_membership_offer(offer_data: dict) -> bool:
    """Determine if the offer requires Coop membership (Medmera)."""
    text = (
        (offer_data.get("description") or "")
        + " "
        + (offer_data.get("promotionText") or "")
        + " "
        + (offer_data.get("splash") or "")
        + " "
        + (offer_data.get("campaignType") or "")
    ).lower()
    return any(
        kw in text for kw in ("medmera", "medlemspris", "medlem", "personligt")
    )


class CoopScraper(AbstractScraper):
    """Scraper for Coop grocery stores using their public offers API."""

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        """Fetch current offers for a Coop store.

        Args:
            store_id: Key from ``COOP_STORES``, e.g. ``"stora-coop-orebro"``.

        Returns:
            List of parsed ``Offer`` objects.  Returns an empty list on
            complete failure after retries.
        """
        store = COOP_STORES.get(store_id)
        if not store:
            raise ValueError(
                f"Unknown Coop store: {store_id}. "
                f"Available stores: {', '.join(sorted(COOP_STORES))}"
            )

        api_store_id = store["store_api_id"]
        url = f"{_API_BASE_URL}?storeId={api_store_id}"
        logger.info("Fetching Coop offers for %s (API id: %s)", store_id, api_store_id)

        data = await self._fetch_with_retry(url)
        if data is None:
            return []

        # The API response can be a list directly or wrapped in a container
        offer_items: list[dict] = []
        if isinstance(data, list):
            offer_items = data
        elif isinstance(data, dict):
            # Try common wrapper keys
            for key in ("offers", "items", "results", "products", "data"):
                if key in data and isinstance(data[key], list):
                    offer_items = data[key]
                    break
            if not offer_items:
                # Maybe the dict itself is some single-level structure with
                # category keys mapping to offer lists
                for val in data.values():
                    if isinstance(val, list) and val and isinstance(val[0], dict):
                        offer_items.extend(val)

        if not offer_items:
            logger.warning(
                "No offer items found in API response for %s. "
                "Response type: %s, keys: %s",
                store_id,
                type(data).__name__,
                list(data.keys()) if isinstance(data, dict) else "N/A",
            )
            return []

        logger.info("Found %d raw offer items for %s", len(offer_items), store_id)

        offers: list[Offer] = []
        for item in offer_items:
            offer = self._parse_offer(item, store_id)
            if offer is not None:
                offers.append(offer)

        logger.info(
            "Parsed %d/%d offers successfully for %s",
            len(offers),
            len(offer_items),
            store_id,
        )
        return offers

    def get_store_info(self, store_id: str) -> dict:
        """Return store metadata for a given Coop store ID."""
        return COOP_STORES.get(store_id, {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_with_retry(self, url: str) -> Any | None:
        """Fetch JSON from *url* with up to ``_MAX_RETRIES`` attempts.

        Uses exponential backoff (1s, 2s, 4s ...) between attempts.
        Returns the parsed JSON on success or ``None`` on total failure.
        """
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True, timeout=20.0
                ) as client:
                    resp = await client.get(url, headers=_DEFAULT_HEADERS)
                    resp.raise_for_status()
                    return resp.json()

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Coop API timeout (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                logger.warning(
                    "Coop API HTTP %d (attempt %d/%d): %s",
                    status,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                # Don't retry on client errors (4xx) except 429 (rate-limit)
                if 400 <= status < 500 and status != 429:
                    break
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "Coop API request error (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )

            if attempt < _MAX_RETRIES:
                backoff = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.debug("Retrying in %.1fs ...", backoff)
                await asyncio.sleep(backoff)

        logger.error(
            "All %d attempts to fetch Coop offers failed. Last error: %s",
            _MAX_RETRIES,
            last_error,
        )
        return None

    def _parse_offer(self, item: dict, store_id: str) -> Optional[Offer]:
        """Parse a single offer dict from the API into an ``Offer`` model.

        Returns ``None`` when the item cannot be meaningfully parsed (e.g.
        missing product name or price).
        """
        try:
            product_name = (
                item.get("name")
                or item.get("productName")
                or item.get("title")
                or ""
            ).strip()

            if not product_name:
                return None

            brand = (
                item.get("brand")
                or item.get("manufacturer")
                or ""
            ).strip() or None

            # Build a price-like dict from item for the parser
            price_data = item if not isinstance(item.get("price"), dict) else item["price"]
            # Merge top-level promo text into price data for parsing
            if isinstance(price_data, dict):
                for field in ("promotionText", "splash"):
                    if field in item and field not in price_data:
                        price_data[field] = item[field]
            offer_price, quantity_deal, unit = _parse_coop_price(price_data)

            if offer_price <= 0:
                logger.debug("Skipping offer with zero price: %s", product_name)
                return None

            original_price = _extract_original_price(item)
            valid_from, valid_to = _parse_dates(item)
            max_per_household = _extract_max_per_household(item)
            requires_membership = _is_membership_offer(item)
            category = classify_category(product_name, brand or "")

            image_url = (
                item.get("imageUrl")
                or item.get("image")
                or item.get("imageUri")
            )
            # Ensure absolute URL
            if image_url and not image_url.startswith("http"):
                image_url = f"https://www.coop.se{image_url}"

            offer_id = _generate_offer_id(store_id, product_name)

            # Preserve raw API data for debugging
            raw_parts = [
                product_name,
                brand or "",
                item.get("promotionText") or item.get("splash") or "",
                item.get("description") or item.get("details") or "",
            ]
            raw_text = " | ".join(p for p in raw_parts if p)

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=product_name,
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
                "Failed to parse Coop offer item: %s",
                item.get("name") or item.get("title") or str(item)[:120],
                exc_info=True,
            )
            return None
