"""Lidl grocery store offer scraper.

Scrapes weekly offers from https://www.lidl.se/erbjudanden.
Lidl offers are national (same for all stores), so we scrape once and
assign the given store_id to all offers.

Lidl uses structured HTML with offer cards. Some offers are Lidl Plus
membership-exclusive.
"""

import hashlib
import logging
import re
from datetime import date, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

from backend.models.offer import Offer
from backend.scrapers.base import AbstractScraper
from backend.scrapers.ica_maxi import classify_category

logger = logging.getLogger(__name__)

# Lidl stores across Sweden. Lidl offers are national, but we keep store
# metadata for the store registry and user-facing display.
LIDL_STORES: dict[str, dict] = {
    "lidl-stockholm-hornsberg": {
        "name": "Lidl Hornsberg",
        "city": "Stockholm",
        "address": "Lindhagensgatan 76, Stockholm",
        "scraper_class": "LidlScraper",
    },
    "lidl-stockholm-liljeholmen": {
        "name": "Lidl Liljeholmen",
        "city": "Stockholm",
        "address": "Liljeholmsvägen 18, Stockholm",
        "scraper_class": "LidlScraper",
    },
    "lidl-goteborg-backaplan": {
        "name": "Lidl Backaplan",
        "city": "Göteborg",
        "address": "Backavägen 3, Göteborg",
        "scraper_class": "LidlScraper",
    },
    "lidl-goteborg-molndal": {
        "name": "Lidl Mölndal",
        "city": "Göteborg",
        "address": "Göteborgsvägen 104, Mölndal",
        "scraper_class": "LidlScraper",
    },
    "lidl-malmo-jagersro": {
        "name": "Lidl Jägersro",
        "city": "Malmö",
        "address": "Jägersrovägen 160, Malmö",
        "scraper_class": "LidlScraper",
    },
    "lidl-malmo-fosie": {
        "name": "Lidl Fosie",
        "city": "Malmö",
        "address": "Fosieby Industriväg 15, Malmö",
        "scraper_class": "LidlScraper",
    },
    "lidl-uppsala": {
        "name": "Lidl Uppsala",
        "city": "Uppsala",
        "address": "Stålgatan 6, Uppsala",
        "scraper_class": "LidlScraper",
    },
    "lidl-linkoping": {
        "name": "Lidl Linköping",
        "city": "Linköping",
        "address": "Industrigatan 14, Linköping",
        "scraper_class": "LidlScraper",
    },
    "lidl-norrkoping": {
        "name": "Lidl Norrköping",
        "city": "Norrköping",
        "address": "Malmgatan 2, Norrköping",
        "scraper_class": "LidlScraper",
    },
    "lidl-orebro": {
        "name": "Lidl Örebro",
        "city": "Örebro",
        "address": "Aspholmsvägen 8, Örebro",
        "scraper_class": "LidlScraper",
    },
    "lidl-vasteras": {
        "name": "Lidl Västerås",
        "city": "Västerås",
        "address": "Saltängsvägen 73, Västerås",
        "scraper_class": "LidlScraper",
    },
    "lidl-helsingborg": {
        "name": "Lidl Helsingborg",
        "city": "Helsingborg",
        "address": "Landskronavägen 27, Helsingborg",
        "scraper_class": "LidlScraper",
    },
    "lidl-jonkoping": {
        "name": "Lidl Jönköping",
        "city": "Jönköping",
        "address": "Bataljonsgatan 10, Jönköping",
        "scraper_class": "LidlScraper",
    },
    "lidl-lund": {
        "name": "Lidl Lund",
        "city": "Lund",
        "address": "Traktorvägen 11, Lund",
        "scraper_class": "LidlScraper",
    },
    "lidl-karlstad": {
        "name": "Lidl Karlstad",
        "city": "Karlstad",
        "address": "Våxnäsgatan 10, Karlstad",
        "scraper_class": "LidlScraper",
    },
}

OFFERS_URL = "https://www.lidl.se/erbjudanden"

MAX_RETRIES = 3
REQUEST_TIMEOUT = 20


def _generate_offer_id(store_id: str, product_name: str) -> str:
    """Generate a stable, deterministic ID from store_id + product name."""
    raw = f"{store_id}-{product_name}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:12]


def _parse_lidl_price(text: str) -> tuple[float, Optional[str], str]:
    """Parse a price string in Swedish format.

    Returns (price, quantity_deal, unit).

    Examples:
        "2 för 50 kr"  -> (25.0, "2 för 50 kr", "kr/st")
        "39:90 kr/kg"  -> (39.9, None, "kr/kg")
        "29:90"        -> (29.9, None, "kr/st")
        "14.90 kr"     -> (14.9, None, "kr/st")
    """
    cleaned = text.strip()

    # "X för Y kr" multi-buy deal
    multi_match = re.search(
        r"(\d+)\s*för\s*(\d+(?:[.:,]\d+)?)\s*kr", cleaned, re.IGNORECASE
    )
    if multi_match:
        count = int(multi_match.group(1))
        total = _to_float(multi_match.group(2))
        deal = f"{count} för {int(total) if total == int(total) else total} kr"
        return total / count, deal, "kr/st"

    # Price with explicit unit: "X kr/kg", "X kr/st", "X kr/förp", "X kr/l"
    unit_match = re.search(
        r"(\d+(?:[.:,]\d+)?)\s*kr\s*/\s*(kg|st|förp|l)", cleaned, re.IGNORECASE
    )
    if unit_match:
        return _to_float(unit_match.group(1)), None, f"kr/{unit_match.group(2)}"

    # Plain price with "kr": "29:90 kr" or "29.90 kr" or "29,90 kr"
    plain_match = re.search(r"(\d+(?:[.:,]\d+)?)\s*kr", cleaned, re.IGNORECASE)
    if plain_match:
        return _to_float(plain_match.group(1)), None, "kr/st"

    # Just a number with colon/comma decimal: "29:90" or "29,90"
    bare_match = re.search(r"(\d+(?:[.:,]\d+)?)", cleaned)
    if bare_match:
        return _to_float(bare_match.group(1)), None, "kr/st"

    return 0.0, None, "kr/st"


def _to_float(s: str) -> float:
    """Convert Swedish-formatted number to float. Handles : and , as decimal."""
    return float(s.replace(":", ".").replace(",", "."))


def _parse_original_price(text: str) -> Optional[float]:
    """Extract the original (non-offer) price from surrounding text.

    Patterns: "Ord. pris 45:90", "Ordinarie pris 45,90 kr",
              "Jfr-pris 89:90/kg", "Tidigare pris 39.90"
    """
    patterns = [
        r"[Oo]rd(?:inarie)?\.?\s*pris\s*(\d+(?:[.:,]\d+)?)",
        r"[Tt]idigare\s*pris\s*(\d+(?:[.:,]\d+)?)",
        r"[Jj]fr[.-]?\s*pris\s*(\d+(?:[.:,]\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _to_float(match.group(1))
    return None


def _parse_validity_dates(text: str) -> tuple[Optional[date], Optional[date]]:
    """Extract valid_from and valid_to dates from text.

    Patterns: "Gäller 25/3-31/3", "Giltig t.o.m. 2026-03-31",
              "v.13", "Vecka 13"
    """
    # "DD/MM-DD/MM" or "DD.MM-DD.MM" pattern
    range_match = re.search(
        r"(\d{1,2})[/.](\d{1,2})\s*[-–]\s*(\d{1,2})[/.](\d{1,2})", text
    )
    if range_match:
        year = date.today().year
        try:
            d_from = date(year, int(range_match.group(2)), int(range_match.group(1)))
            d_to = date(year, int(range_match.group(4)), int(range_match.group(3)))
            # If the end date is before start, it wraps around new year
            if d_to < d_from:
                d_to = d_to.replace(year=year + 1)
            return d_from, d_to
        except ValueError:
            pass

    # ISO date range: "2026-03-23 - 2026-03-29"
    iso_match = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*[-–]\s*(\d{4}-\d{2}-\d{2})", text
    )
    if iso_match:
        try:
            d_from = date.fromisoformat(iso_match.group(1))
            d_to = date.fromisoformat(iso_match.group(2))
            return d_from, d_to
        except ValueError:
            pass

    return None, None


def _is_lidl_plus(card: Tag) -> bool:
    """Detect if an offer card is a Lidl Plus membership offer."""
    # Check for Lidl Plus badges, classes, or text markers
    card_html = str(card).lower()
    markers = ["lidl-plus", "lidl plus", "plus-pris", "pluspris", "medlemspris"]
    return any(marker in card_html for marker in markers)


def _parse_max_per_household(text: str) -> Optional[int]:
    """Extract max purchase per household."""
    match = re.search(r"[Mm]ax\s*(\d+)\s*(?:köp|st|förp)?\s*/?\s*hushåll", text)
    if match:
        return int(match.group(1))
    match = re.search(r"[Mm]ax\s*(\d+)\s*(?:per\s*kund|st\s*per)", text)
    if match:
        return int(match.group(1))
    return None


class LidlScraper(AbstractScraper):
    """Scraper for Lidl Sweden weekly offers.

    Lidl offers are national — the same offers apply to all stores.
    We scrape the central offers page once and tag results with the
    requested store_id.
    """

    BASE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.5",
    }

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        """Fetch Lidl's weekly offers.

        Since Lidl offers are national, we scrape the central page and
        assign the given store_id to every offer. This means multiple
        store_ids will return the same offers, which is correct for Lidl.
        """
        if store_id not in LIDL_STORES:
            raise ValueError(
                f"Unknown Lidl store: {store_id}. "
                f"Valid IDs: {', '.join(sorted(LIDL_STORES))}"
            )

        html = await self._fetch_page()
        if html is None:
            return []

        soup = BeautifulSoup(html, "html.parser")
        offers = self._extract_offers(soup, store_id)

        logger.info(
            "Scraped %d offers from Lidl for store %s", len(offers), store_id
        )
        return offers

    async def _fetch_page(self) -> Optional[str]:
        """Fetch the Lidl offers page with retry logic."""
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True, timeout=REQUEST_TIMEOUT
                ) as client:
                    resp = await client.get(OFFERS_URL, headers=self.BASE_HEADERS)
                    resp.raise_for_status()
                    logger.debug(
                        "Fetched Lidl offers page (attempt %d, %d bytes)",
                        attempt,
                        len(resp.text),
                    )
                    return resp.text
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Timeout fetching Lidl offers (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "HTTP %d fetching Lidl offers (attempt %d/%d): %s",
                    exc.response.status_code,
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "Request error fetching Lidl offers (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

        logger.error(
            "All %d attempts to fetch Lidl offers failed. Last error: %s",
            MAX_RETRIES,
            last_error,
        )
        return None

    def _extract_offers(self, soup: BeautifulSoup, store_id: str) -> list[Offer]:
        """Parse offer cards from the page HTML."""
        # Lidl uses various container patterns; try multiple selectors
        cards: list[Tag] = []

        # Primary: structured product cards / offer tiles
        for selector in [
            "article",
            "[data-grid-box]",
            ".product-grid-box",
            ".ods-tile",
            ".offer-card",
            ".ret-o-card",
            ".nuc-a-flex-item",
        ]:
            found = soup.select(selector)
            if found:
                cards = found
                logger.debug(
                    "Found %d cards using selector '%s'", len(found), selector
                )
                break

        if not cards:
            logger.warning(
                "No offer cards found on Lidl page — page structure may have changed"
            )
            return []

        # Determine validity period from page-level metadata or default to
        # current Monday-Sunday week.
        page_text = soup.get_text(" ", strip=True)
        page_valid_from, page_valid_to = _parse_validity_dates(page_text)

        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday

        default_from = page_valid_from or week_start
        default_to = page_valid_to or week_end

        offers: list[Offer] = []
        for card in cards:
            offer = self._parse_card(card, store_id, default_from, default_to)
            if offer is not None:
                offers.append(offer)

        return offers

    def _parse_card(
        self,
        card: Tag,
        store_id: str,
        default_from: date,
        default_to: date,
    ) -> Optional[Offer]:
        """Parse a single offer card into an Offer model."""
        try:
            # --- Product name ---
            product_name = self._extract_product_name(card)
            if not product_name:
                return None

            # --- Brand ---
            brand = self._extract_brand(card)

            # --- Price ---
            price_text = self._extract_price_text(card)
            if not price_text:
                return None
            offer_price, quantity_deal, unit = _parse_lidl_price(price_text)
            if offer_price <= 0:
                return None

            # --- Original price ---
            card_text = card.get_text(" ", strip=True)
            original_price = _parse_original_price(card_text)

            # --- Validity dates (card-level overrides page default) ---
            card_from, card_to = _parse_validity_dates(card_text)
            valid_from = card_from or default_from
            valid_to = card_to or default_to

            # --- Category ---
            category = classify_category(product_name, brand or "")

            # --- Membership ---
            requires_membership = _is_lidl_plus(card)

            # --- Max per household ---
            max_per_household = _parse_max_per_household(card_text)

            # --- Image ---
            img = card.find("img")
            image_url: Optional[str] = None
            if img:
                image_url = img.get("src") or img.get("data-src") or None
                # Resolve protocol-relative URLs
                if image_url and image_url.startswith("//"):
                    image_url = f"https:{image_url}"

            # --- Stable ID ---
            offer_id = _generate_offer_id(store_id, product_name)

            # --- Raw text for debugging ---
            raw_text = card_text[:500]

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=product_name,
                brand=brand or None,
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
                "Failed to parse Lidl offer card",
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # Extraction helpers — isolated so they are easy to update when
    # Lidl changes their HTML structure.
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_product_name(card: Tag) -> Optional[str]:
        """Extract the product name from the card."""
        # Try common selectors for product title
        for selector in [
            ".product-grid-box__title",
            ".ods-tile__title",
            ".ret-o-card__headline",
            "[data-title]",
            "h2",
            "h3",
            ".offer-card__title",
            ".nuc-m-product-card__title",
        ]:
            el = card.select_one(selector)
            if el:
                name = el.get_text(strip=True)
                if name:
                    return name

        # Fallback: data attribute
        for attr in ["data-title", "data-name", "data-promotion-name"]:
            val = card.get(attr)
            if val:
                return str(val).strip()

        return None

    @staticmethod
    def _extract_brand(card: Tag) -> Optional[str]:
        """Extract the brand name from the card."""
        for selector in [
            ".product-grid-box__brand",
            ".ods-tile__subtitle",
            ".ret-o-card__sub-headline",
            ".nuc-m-product-card__subtitle",
        ]:
            el = card.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text

        for attr in ["data-brand", "data-promotion-brand"]:
            val = card.get(attr)
            if val:
                return str(val).strip()

        return None

    @staticmethod
    def _extract_price_text(card: Tag) -> Optional[str]:
        """Extract the raw price text from the card."""
        for selector in [
            ".product-grid-box__price",
            ".ods-tile__price",
            ".ret-o-card__price",
            ".price",
            ".m-price__price",
            ".nuc-m-product-card__price",
            "[data-price]",
        ]:
            el = card.select_one(selector)
            if el:
                text = el.get_text(strip=True)
                if text and re.search(r"\d", text):
                    return text

        # Fallback: data attribute
        price_val = card.get("data-price")
        if price_val:
            return str(price_val)

        return None

    # ------------------------------------------------------------------
    # Store info
    # ------------------------------------------------------------------

    def get_store_info(self, store_id: str) -> dict:
        """Return store metadata for the given Lidl store."""
        return LIDL_STORES.get(store_id, {})
