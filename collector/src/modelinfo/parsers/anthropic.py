import json
import re
from datetime import date
from modelinfo.parsers.base import BaseParser

MODELS_URL = "https://docs.anthropic.com/en/docs/about-claude/models"
PRICING_URL = "https://www.anthropic.com/pricing"


class AnthropicParser(BaseParser):
    source_name = "anthropic"

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

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            name = cols[0].get_text(strip=True).lower()
            context_raw = cols[1].get_text(strip=True)
            max_output_raw = cols[2].get_text(strip=True)

            # Normalize model name to ID-friendly format
            model_id_name = name.replace(" ", "-")
            model = {
                "model_id": f"anthropic/{model_id_name}",
                "model_name": name,
                "provider": "anthropic",
                "provider_type": "closed",
                "context_length": self._parse_int(context_raw),
                "max_output_tokens": self._parse_int(max_output_raw),
                "capabilities": self._infer_capabilities(name),
                "urls": json.dumps({"official": f"https://docs.anthropic.com/en/docs/about-claude/models", "pricing": PRICING_URL}),
                "tags": json.dumps(["anthropic", "claude"]),
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
        # Detect thinking token info in page text
        page_text = soup.get_text()
        has_thinking_pricing = "thinking" in page_text.lower() and "charged" in page_text.lower()

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
            if input_price is None or output_price is None:
                continue

            model_id_name = name.replace(" ", "-")
            pricings.append({
                "pricing_id": f"anthropic/{model_id_name}/official/global/{self._today()}",
                "model_id": f"anthropic/{model_id_name}",
                "channel": "official",
                "region": "global",
                "valid_from": self._today(),
                "input_price_per_1m": input_price,
                "output_price_per_1m": output_price,
                "reasoning_tokens_charged": has_thinking_pricing,
                "source": PRICING_URL,
            })
        return pricings

    def _parse_price(self, raw: str) -> float | None:
        """Parse '$3.00 / MTok' or '$15.00 / MTok' to float per 1M tokens."""
        if not raw:
            return None
        # Anthropic uses / MTok (per million tokens) -- same as per 1M, no conversion needed
        match = re.search(r'\$?(\d+\.?\d*)', raw)
        if match:
            return float(match.group(1))
        return None

    def _parse_int(self, raw: str) -> int | None:
        if not raw:
            return None
        return int(raw.replace(",", ""))

    def _infer_capabilities(self, name: str) -> str:
        caps = {
            "text": True,
            "code": True,
            "reasoning": True,  # Claude models have strong reasoning
            "vision": True,     # All Claude models support vision
            "tool_use": True,
            "streaming": True,
        }
        return json.dumps(caps)

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
