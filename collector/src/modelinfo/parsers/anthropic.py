import json
import re
from datetime import date
from modelinfo.parsers.base import BaseParser

MODELS_URL = "https://platform.claude.com/docs/en/about-claude/models"
PRICING_URL = "https://www.anthropic.com/pricing"


class AnthropicParser(BaseParser):
    source_name = "anthropic"

    async def fetch_models(self, html_override: str | None = None):
        if html_override is not None:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_override, "lxml")
        else:
            soup = await self.fetcher.fetch_html(MODELS_URL)

        table = soup.find("table")
        if not table:
            return []

        # Parse transposed table: headers = model names, rows = features
        rows = table.find_all("tr")
        if not rows:
            return []

        headers = rows[0].find_all(["th", "td"])
        model_names = [h.get_text(strip=True) for h in headers[1:]]

        # Extract features into {feature_name: [value_per_model, ...]}
        features = {}
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            key = cells[0].get_text(strip=True).lower()
            values = [c.get_text(strip=True) for c in cells[1:]]
            features[key] = values

        models = []
        for i, name in enumerate(model_names):
            model_id_name = (features.get("claude api id", [name])[i] if i < len(features.get("claude api id", [])) else name).replace(" ", "-").lower()
            context_raw = features.get("context window", [""])[i] if i < len(features.get("context window", [""])) else ""
            max_output_raw = features.get("max output", [""])[i] if i < len(features.get("max output", [""])) else ""

            model = {
                "model_id": f"anthropic/{model_id_name}",
                "model_name": features.get("claude api id", model_names)[i] if i < len(features.get("claude api id", [""])) else name,
                "provider": "anthropic",
                "provider_type": "closed",
                "context_length": self._parse_int(context_raw),
                "max_output_tokens": self._parse_int(max_output_raw),
                "capabilities": json.dumps({
                    "text": True,
                    "code": True,
                    "reasoning": "extended thinking" in (features.get("extended thinking", [""])[i] if i < len(features.get("extended thinking", [""])) else ""),
                    "vision": "vision" in features.keys(),
                    "tool_use": True,
                    "streaming": True,
                }),
                "urls": json.dumps({"official": MODELS_URL, "pricing": PRICING_URL}),
                "tags": json.dumps(["anthropic", "claude"]),
            }
            models.append(model)
        return models

    async def fetch_pricing(self, html_override: str | None = None):
        """Extract pricing from the models page (transposed table with Pricing row)."""
        if html_override is not None:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_override, "lxml")
        else:
            soup = await self.fetcher.fetch_html(MODELS_URL)

        pricings = []
        table = soup.find("table")
        if not table:
            return pricings

        rows = table.find_all("tr")
        if not rows:
            return pricings

        headers = rows[0].find_all(["th", "td"])
        model_names_api = []  # API IDs

        # Build features map
        features = {}
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            key = cells[0].get_text(strip=True).lower()
            values = [c.get_text(strip=True) for c in cells[1:]]
            features[key] = values

        api_ids = features.get("claude api id", [])
        thinking_flags = features.get("extended thinking", [])

        # Parse pricing row: "$5 / input MTok$25 / output MTok"
        pricing_raw = features.get("pricing1", [])
        for i, api_id in enumerate(api_ids):
            raw = pricing_raw[i] if i < len(pricing_raw) else ""
            input_price, output_price = self._parse_pricing_cell(raw)
            if input_price is None or output_price is None:
                continue

            has_thinking = False
            if i < len(thinking_flags):
                has_thinking = thinking_flags[i].lower() == "yes"

            pricings.append({
                "pricing_id": f"anthropic/{api_id}/official/global/{self._today()}",
                "model_id": f"anthropic/{api_id}",
                "channel": "official",
                "region": "global",
                "valid_from": self._today(),
                "input_price_per_1m": input_price,
                "output_price_per_1m": output_price,
                "reasoning_tokens_charged": has_thinking,
                "source": MODELS_URL,
            })
        return pricings

    def _parse_pricing_cell(self, raw: str) -> tuple:
        """Parse '$5 / input MTok$25 / output MTok' -> (5.0, 25.0)."""
        if not raw:
            return None, None
        # Find input price
        input_match = re.search(r'\$(\d+\.?\d*)\s*/\s*input\s*MTok', raw)
        output_match = re.search(r'\$(\d+\.?\d*)\s*/\s*output\s*MTok', raw)
        if input_match and output_match:
            return float(input_match.group(1)), float(output_match.group(1))
        # Fallback: try to find any two dollar amounts
        amounts = re.findall(r'\$(\d+\.?\d*)', raw)
        if len(amounts) >= 2:
            return float(amounts[0]), float(amounts[1])
        return None, None

    def _parse_int(self, raw: str) -> int | None:
        if not raw:
            return None
        raw = raw.replace(",", "").strip()
        match = re.search(r'(\d+(?:\.?\d*)?)\s*([KMkm]?)\b', raw)
        if match:
            num = float(match.group(1))
            unit = match.group(2).upper()
            if unit == 'K':
                num *= 1000
            elif unit == 'M':
                num *= 1000000
            return int(num)
        return None

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
