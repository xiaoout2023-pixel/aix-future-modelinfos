from abc import ABC, abstractmethod
from modelinfo.fetcher import Fetcher


class BaseParser(ABC):
    source_name: str = ""

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    @abstractmethod
    async def fetch_models(self) -> list[dict]:
        """Fetch and parse model metadata. Returns list of dicts with model fields."""

    @abstractmethod
    async def fetch_pricing(self) -> list[dict]:
        """Fetch and parse pricing data. Returns list of dicts with pricing fields."""
