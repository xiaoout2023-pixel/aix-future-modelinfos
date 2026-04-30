import json
import re
from datetime import date
from modelinfo.parsers.base import BaseParser

MODELS_URL = "https://platform.openai.com/docs/models"
PRICING_URL = "https://platform.openai.com/docs/pricing"


class OpenAIParser(BaseParser):
    source_name = "openai"

    async def fetch_models(self, html_override: str | None = None):
        if html_override is not None:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_override, "lxml")
        else:
            soup = await self.fetcher.fetch_html(MODELS_URL)

        models = []
        table = soup.find("table")
        if not table:
            return models

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            name = cols[0].get_text(strip=True).lower()
            context_raw = cols[2].get_text(strip=True) if len(cols) > 2 else ""
            max_output_raw = cols[3].get_text(strip=True) if len(cols) > 3 else ""

            model_id = f"openai/{name}"
            model = {
                "model_id": model_id,
                "model_name": name,
                "provider": "openai",
                "provider_type": "closed",
                "context_length": self._parse_int(context_raw),
                "max_output_tokens": self._parse_int(max_output_raw),
                "capabilities": self._infer_capabilities(name),
                "urls": json.dumps({"official": f"https://platform.openai.com/docs/models/{name}", "pricing": PRICING_URL}),
                "tags": json.dumps(["openai"]),
            }
            models.append(model)
        return models

    async def fetch_pricing(self, html_override: str | None = None):
        if html_override is not None:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_override, "lxml")
        else:
            soup = await self.fetcher.fetch_html(PRICING_URL)

        pricings = []
        table = soup.find("table")
        if not table:
            return pricings

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            name = cols[0].get_text(strip=True).lower()
            input_raw = cols[1].get_text(strip=True)
            output_raw = cols[2].get_text(strip=True)

            input_price = self._parse_price(input_raw)
            output_price = self._parse_price(output_raw)
            if input_price is None and output_price is None:
                continue

            pricings.append({
                "pricing_id": f"openai/{name}/official/global/{self._today()}",
                "model_id": f"openai/{name}",
                "channel": "official",
                "region": "global",
                "valid_from": self._today(),
                "input_price_per_1m": input_price,
                "output_price_per_1m": output_price,
                "source": PRICING_URL,
            })
        return pricings

    def _parse_price(self, raw: str) -> float | None:
        """Parse '$2.50 / 1M tokens' or '$0.15 / 1M tokens' to float."""
        if not raw:
            return None
        if raw.lower() == "free":
            return 0.0
        match = re.search(r'\$?(\d+\.?\d*)', raw)
        if match:
            return float(match.group(1))
        return None

    def _parse_int(self, raw: str) -> int | None:
        """Parse '128,000' or '1,000,000' to int."""
        if not raw:
            return None
        return int(raw.replace(",", ""))

    def _infer_capabilities(self, name: str) -> str:
        caps = {
            "text": True,
            "code": True,
            "vision": "vision" in name.lower() or "gpt-4o" in name.lower(),
            "image_gen": "dall-e" in name.lower(),
            "audio": "whisper" in name.lower() or "tts" in name.lower(),
            "streaming": True,
            "batch": True,
        }
        return json.dumps(caps)

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
