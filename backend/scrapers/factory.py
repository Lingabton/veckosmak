"""Scraper factory — maps store chains to their scraper implementations."""

import logging

from backend.scrapers.base import AbstractScraper

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular deps and allow missing scrapers
_scraper_cache: dict[str, AbstractScraper] = {}


def get_scraper_for_store(store_id: str) -> AbstractScraper:
    """Return the correct scraper instance for a store ID.

    Store ID prefixes:
    - ica-*        → IcaMaxiScraper
    - willys-*     → WillysScraper
    - coop-*       → CoopScraper
    - lidl-*       → LidlScraper
    """
    prefix = store_id.split("-")[0] if "-" in store_id else store_id

    if prefix in _scraper_cache:
        return _scraper_cache[prefix]

    scraper: AbstractScraper

    if prefix == "ica":
        from backend.scrapers.ica_maxi import IcaMaxiScraper
        scraper = IcaMaxiScraper()
    elif prefix == "willys":
        from backend.scrapers.willys import WillysScraper
        scraper = WillysScraper()
    elif prefix == "coop":
        from backend.scrapers.coop import CoopScraper
        scraper = CoopScraper()
    elif prefix == "lidl":
        from backend.scrapers.lidl import LidlScraper
        scraper = LidlScraper()
    else:
        logger.warning(f"Unknown store prefix '{prefix}' — falling back to ICA scraper")
        from backend.scrapers.ica_maxi import IcaMaxiScraper
        scraper = IcaMaxiScraper()

    _scraper_cache[prefix] = scraper
    return scraper


def get_all_store_registries() -> dict:
    """Merge all store registries into one dict."""
    from backend.scrapers.store_registry import STORE_REGISTRY

    all_stores = dict(STORE_REGISTRY)

    try:
        from backend.scrapers.willys import WILLYS_STORES
        all_stores.update(WILLYS_STORES)
    except ImportError:
        logger.debug("Willys scraper not available")

    try:
        from backend.scrapers.coop import COOP_STORES
        all_stores.update(COOP_STORES)
    except ImportError:
        logger.debug("Coop scraper not available")

    try:
        from backend.scrapers.lidl import LIDL_STORES
        all_stores.update(LIDL_STORES)
    except ImportError:
        logger.debug("Lidl scraper not available")

    return all_stores
