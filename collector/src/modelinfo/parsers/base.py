from abc import ABC, abstractmethod
from modelinfo.fetcher import Fetcher


class BaseParser(ABC):
    source_name: str = ""

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    async def fetch_models(self) -> list[dict]:
        return []

    async def fetch_pricing(self) -> list[dict]:
        return []

    async def fetch_evaluations(self) -> list[dict]:
        return []
