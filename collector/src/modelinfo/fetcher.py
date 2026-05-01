import asyncio
import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class Fetcher:
    def __init__(self, max_retries: int = 3, timeout: float = 30.0):
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ModelInfo-Collector/0.1; +https://github.com/xiaoout2023-pixel/aix-future-modelinfos)",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def fetch_json(self, url: str) -> dict:
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning("fetch_json_failed", url=url, attempt=attempt, error=str(e))
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def fetch_html(self, url: str) -> BeautifulSoup:
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                logger.warning("fetch_html_failed", url=url, attempt=attempt, error=str(e))
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
