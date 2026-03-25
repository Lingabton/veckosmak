from abc import ABC, abstractmethod

from backend.models.offer import Offer


class AbstractScraper(ABC):
    @abstractmethod
    async def fetch_offers(self, store_id: str) -> list[Offer]:
        """Fetch this week's offers from the store."""
        pass

    @abstractmethod
    def get_store_info(self, store_id: str) -> dict:
        """Return store info (name, address, etc)."""
        pass
