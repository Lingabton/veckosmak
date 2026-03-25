STORE_REGISTRY = {
    "ica-maxi-1004097": {
        "name": "Maxi ICA Stormarknad Orebro Boglundsangen",
        "scraper": "IcaMaxiScraper",
        "url": "https://www.ica.se/erbjudanden/maxi-ica-stormarknad-orebro-boglundsangen-1004097/",
        "city": "Orebro",
    }
}


def get_store_info(store_id: str) -> dict | None:
    return STORE_REGISTRY.get(store_id)
