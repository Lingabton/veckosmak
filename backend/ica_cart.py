"""ICA online cart integration.

Generates a deep link to handla.ica.se that pre-populates the user's cart
with ingredients from the shopping list. Uses ICA's product search to map
ingredient names to product IDs.

Note: Full cart API integration requires user authentication with ICA.
This module provides:
1. Product search via ICA's public API
2. Deep link generation for handla.ica.se
3. Cart URL builder with pre-selected products
"""

import hashlib
import logging
from typing import Optional
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger(__name__)

# ICA product search endpoint (public, no auth needed)
ICA_SEARCH_URL = "https://handlaprivatkund.ica.se/api/content/v1/collection/customer/search"
ICA_HANDLA_BASE = "https://handla.ica.se"

# Map our categories to ICA's search categories for better results
CATEGORY_SEARCH_HINTS = {
    "meat": "kött chark",
    "fish": "fisk skaldjur",
    "dairy": "mejeri",
    "produce": "frukt grönt",
    "pantry": "skafferi",
    "bakery": "bröd",
    "frozen": "fryst",
}


async def search_ica_products(query: str, store_id: str = "", limit: int = 3) -> list[dict]:
    """Search ICA's product catalog.

    Returns simplified product results:
    [{"id": str, "name": str, "price": float, "unit": str, "image_url": str}]
    """
    try:
        params = {"q": query, "includeAds": "false"}
        if store_id:
            # Extract numeric store ID from our format
            numeric_id = store_id.split("-")[-1] if "-" in store_id else store_id
            params["storeId"] = numeric_id

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(ICA_SEARCH_URL, params=params, headers=headers)
            if resp.status_code != 200:
                logger.debug(f"ICA search returned {resp.status_code} for '{query}'")
                return []

            data = resp.json()
            products = []
            items = data.get("items", data.get("products", []))

            for item in items[:limit]:
                product = {
                    "id": str(item.get("id", item.get("productId", ""))),
                    "name": item.get("name", item.get("productName", "")),
                    "price": float(item.get("price", item.get("currentPrice", 0))),
                    "unit": item.get("unitOfMeasure", "st"),
                    "image_url": item.get("imageUrl", ""),
                }
                if product["name"]:
                    products.append(product)

            return products

    except Exception as e:
        logger.debug(f"ICA product search failed for '{query}': {e}")
        return []


def build_handla_search_url(ingredient_name: str, store_id: str = "") -> str:
    """Build a deep link to ICA Handla that searches for an ingredient."""
    base = f"{ICA_HANDLA_BASE}/search"
    params = {"q": ingredient_name}
    if store_id:
        numeric_id = store_id.split("-")[-1] if "-" in store_id else store_id
        params["storeId"] = numeric_id
    return f"{base}?{urlencode(params)}"


def build_cart_url(items: list[dict], store_id: str = "") -> str:
    """Build a URL that opens ICA Handla with multiple search terms.

    Each item should have: {"ingredient_name": str, "total_amount": float, "unit": str}

    Since ICA doesn't have a public "add to cart" API, we generate a
    shopping list page URL that the user can use to quickly add items.
    """
    if not items:
        return ICA_HANDLA_BASE

    # Build a combined search query from top items
    search_terms = []
    for item in items[:20]:  # Limit to avoid too-long URLs
        name = item.get("ingredient_name", "")
        if name and not item.get("is_pantry_staple", False):
            search_terms.append(name)

    if not search_terms:
        return ICA_HANDLA_BASE

    # Return search URL with first item — user navigates through the rest
    return build_handla_search_url(search_terms[0], store_id)


async def match_shopping_list_to_ica(shopping_items: list[dict], store_id: str = "") -> list[dict]:
    """Match shopping list items to ICA products.

    Returns enriched items with ICA product suggestions:
    [{"ingredient_name": str, ..., "ica_products": [{"id": str, "name": str, "price": float}]}]
    """
    enriched = []
    for item in shopping_items:
        name = item.get("ingredient_name", "")
        category = item.get("category", "other")

        # Skip pantry staples (salt, pepper, etc.)
        if item.get("is_pantry_staple"):
            enriched.append({**item, "ica_products": [], "ica_search_url": ""})
            continue

        # Add category hint for better search
        hint = CATEGORY_SEARCH_HINTS.get(category, "")
        search_query = f"{name} {hint}".strip() if hint else name

        products = await search_ica_products(search_query, store_id, limit=2)

        enriched.append({
            **item,
            "ica_products": products,
            "ica_search_url": build_handla_search_url(name, store_id),
        })

    return enriched


def generate_shopping_list_text_for_ica(menu: dict) -> str:
    """Generate a text format shopping list optimized for ICA Handla search.

    Returns a newline-separated list of items with amounts.
    """
    if not menu or "shopping_list" not in menu:
        return ""

    lines = []
    for item in menu["shopping_list"].get("items", []):
        name = item.get("ingredient_name", "")
        amount = item.get("total_amount", 0)
        unit = item.get("unit", "")

        if amount > 0:
            lines.append(f"{amount} {unit} {name}".strip())
        else:
            lines.append(name)

    return "\n".join(lines)
