"""ICA Maxi offer scraper.

Scrapes weekly offers from the ICA offers page.
Offers are server-rendered in initial HTML as <article class="offer-card"> elements.
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
from backend.scrapers.store_registry import STORE_REGISTRY

logger = logging.getLogger(__name__)

# Map common product keywords to categories
CATEGORY_KEYWORDS = {
    "meat": [
        "kyckling", "fläsk", "nöt", "färs", "korv", "bacon", "skinka",
        "lamm", "kalkon", "kebab", "köttbull", "entrecote", "karré",
        "schnitzel", "grillkorv", "falukorv", "kassler", "chorizo",
    ],
    "fish": [
        "lax", "torsk", "sej", "fisk", "räk", "tonfisk", "sill",
        "makrill", "pangasius", "rödspätta",
    ],
    "dairy": [
        "mjölk", "ost", "grädde", "yoghurt", "fil", "smör", "bregott",
        "créme", "kvarg", "cream", "cottage", "herrgård", "präst",
        "grevé", "cheddar", "mozzarella",
    ],
    "produce": [
        "tomat", "gurk", "paprika", "lök", "potatis", "morot", "sallad",
        "broccoli", "äpple", "banan", "citron", "avokado", "svamp",
        "melon", "druv", "päron", "clementin", "mango", "ananas",
    ],
    "pantry": [
        "pasta", "ris", "mjöl", "socker", "olja", "sås", "kross",
        "ketchup", "senap", "buljong", "konserv", "müsli", "flingor",
        "kaffe", "te ", "choklad", "godis", "chips", "läsk",
    ],
    "bakery": [
        "bröd", "limpa", "bulle", "kaka", "franskbröd", "knäcke",
        "baguett", "sikt", "pizza­deg", "pizzadeg",
    ],
    "frozen": [
        "fryst", "frysta", "glass", "pizza", "pommes", "fish fingers",
    ],
}


def classify_category(product_name: str, brand: str = "") -> str:
    text = f"{product_name} {brand}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "other"


def parse_price(splash_text: str) -> tuple[float, Optional[str], str]:
    """Parse price from splash text.

    Returns (price, quantity_deal, unit).

    Examples:
        "2 för 85 kr" -> (42.5, "2 för 85 kr", "kr/st")
        "89 kr/st" -> (89.0, None, "kr/st")
        "69 kr/kg" -> (69.0, None, "kr/kg")
        "40 kr/st" -> (40.0, None, "kr/st")
    """
    text = splash_text.replace(":-", "").replace(",", ".").strip()

    # "X för Y kr" pattern
    multi_match = re.search(r"(\d+)\s*för\s*(\d+(?:\.\d+)?)\s*kr", text)
    if multi_match:
        count = int(multi_match.group(1))
        total = float(multi_match.group(2))
        deal = f"{count} för {int(total)} kr"
        return total / count, deal, "kr/st"

    # "X kr/kg" or "X kr/st" or "X kr/förp"
    unit_match = re.search(r"(\d+(?:\.\d+)?)\s*kr/(kg|st|förp|l)", text)
    if unit_match:
        return float(unit_match.group(1)), None, f"kr/{unit_match.group(2)}"

    # Just "X kr"
    plain_match = re.search(r"(\d+(?:\.\d+)?)\s*kr", text)
    if plain_match:
        return float(plain_match.group(1)), None, "kr/st"

    return 0.0, None, "kr/st"


def parse_original_price(details_text: str) -> Optional[float]:
    """Extract original price from details text.

    Example: "Ord.pris 50:11-54:95 kr" -> 54.95 (use highest)
    """
    match = re.search(r"[Oo]rd\.?\s*pris\s*([\d:,]+)(?:-([\d:,]+))?\s*kr", details_text)
    if not match:
        return None

    def to_float(s: str) -> float:
        return float(s.replace(":", ".").replace(",", "."))

    prices = [to_float(match.group(1))]
    if match.group(2):
        prices.append(to_float(match.group(2)))

    return max(prices)


def parse_max_per_household(details_text: str) -> Optional[int]:
    match = re.search(r"[Mm]ax\s*(\d+)\s*köp/hushåll", details_text)
    return int(match.group(1)) if match else None


def parse_membership(details_text: str) -> bool:
    text_lower = details_text.lower()
    return "stammis" in text_lower or "medlemspris" in text_lower


class IcaMaxiScraper(AbstractScraper):
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "sv-SE,sv;q=0.9",
    }

    async def fetch_offers(self, store_id: str) -> list[Offer]:
        store = STORE_REGISTRY.get(store_id)
        if not store:
            raise ValueError(f"Unknown store: {store_id}")

        url = store["url"]
        logger.info(f"Fetching offers from {url}")

        # Retry up to 2 times on transient errors
        resp = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
                    resp = await client.get(url, headers=self.BASE_HEADERS)
                    resp.raise_for_status()
                    break
            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                logger.warning(f"Scraping attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    logger.error(f"All scraping attempts failed for {store_id}")
                    return []

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("article", class_="offer-card")
        logger.info(f"Found {len(cards)} offer cards")

        if not cards:
            logger.warning("No offer cards found — page structure may have changed")
            return []

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        offers = []
        for card in cards:
            offer = self._parse_card(card, store_id, week_start, week_end)
            if offer:
                offers.append(offer)

        logger.info(f"Parsed {len(offers)} offers successfully")
        return offers

    def _parse_card(
        self, card: Tag, store_id: str, valid_from: date, valid_to: date
    ) -> Optional[Offer]:
        try:
            promo_id = card.get("data-promotion-id", "")
            name = card.get("data-promotion-name", "")
            brand = card.get("data-promotion-brand", "")

            if not name:
                title_el = card.find(class_="offer-card__title")
                name = title_el.get_text(strip=True) if title_el else ""

            if not name:
                return None

            # Price splash
            splash = card.find(class_="offer-card__price-splash")
            splash_text = splash.get_text(strip=True) if splash else ""
            offer_price, quantity_deal, unit = parse_price(splash_text)

            # Details text
            text_el = card.find(class_="offer-card__text")
            details = text_el.get_text(" ", strip=True) if text_el else ""

            original_price = parse_original_price(details)
            max_per_household = parse_max_per_household(details)
            requires_membership = parse_membership(details)
            category = classify_category(name, brand)

            # Image
            img = card.find("img")
            image_url = img.get("src") if img else None

            # Generate stable ID
            offer_id = hashlib.md5(
                f"{store_id}-{promo_id}-{name}".encode()
            ).hexdigest()[:12]

            raw_text = f"{name} | {brand} | {splash_text} | {details}"

            return Offer(
                id=offer_id,
                store_id=store_id,
                product_name=name,
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
        except Exception as e:
            logger.error(f"Failed to parse offer card: {e}", exc_info=True)
            return None

    def get_store_info(self, store_id: str) -> dict:
        return STORE_REGISTRY.get(store_id, {})
