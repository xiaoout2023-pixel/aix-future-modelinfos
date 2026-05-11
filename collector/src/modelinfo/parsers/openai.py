import json
import re
from datetime import date
from modelinfo.parsers.base import BaseParser
import structlog

logger = structlog.get_logger()

MODELS_URL = "https://platform.openai.com/docs/models"
PRICING_URL = "https://openai.com/api/pricing/"
PRICING_FALLBACK_URL = "https://platform.openai.com/docs/pricing"


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

        rows = table.find_all("tr")[1:]
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
            soup = await self._fetch_pricing_page()

        pricings = self._parse_pricing_from_sections(soup)
        if not pricings:
            pricings = self._parse_pricing_from_table(soup)
        return pricings

    async def _fetch_pricing_page(self):
        try:
            return await self.fetcher.fetch_html(PRICING_URL)
        except Exception as e:
            logger.warning("openai_pricing_fetch_failed", url=PRICING_URL, error=str(e))
            try:
                return await self.fetcher.fetch_html(PRICING_FALLBACK_URL)
            except Exception as e2:
                logger.error("openai_pricing_all_failed", error=str(e2))
                from bs4 import BeautifulSoup
                return BeautifulSoup("", "lxml")

    def _parse_pricing_from_sections(self, soup) -> list[dict]:
        pricings = []
        seen = set()
        for heading in soup.find_all(["h2", "h3", "h4"]):
            model_name_raw = heading.get_text(strip=True)
            model_name = model_name_raw.lower().strip()
            if not model_name or len(model_name) > 80:
                continue
            if model_name in seen:
                continue

            section = heading.find_next_sibling()
            input_price = None
            output_price = None
            while section and section.name not in ["h2", "h3", "h4"]:
                text = section.get_text(separator=" ", strip=True)
                if not input_price:
                    input_match = re.search(r'(?:输入|Input)[：:]\s*(?:US\s*\$|\$)\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
                    if not input_match:
                        input_match = re.search(r'(?:US\s*\$|\$)\s*([\d,]+\.?\d*)\s*/\s*1M\s*(?:令牌|token)', text, re.IGNORECASE)
                    if input_match:
                        input_price = float(input_match.group(1).replace(",", ""))
                if not output_price:
                    output_match = re.search(r'(?:输出|Output)[：:]\s*(?:US\s*\$|\$)\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
                    if not output_match:
                        output_match = re.search(r'(?:US\s*\$|\$)\s*([\d,]+\.?\d*)\s*/\s*1M\s*(?:令牌|token)', text, re.IGNORECASE)
                        if output_match and input_price is not None:
                            pass
                    if output_match:
                        output_price = float(output_match.group(1).replace(",", ""))
                section = section.find_next_sibling()

            if input_price is not None or output_price is not None:
                seen.add(model_name)
                pricings.append({
                    "pricing_id": f"openai/{model_name}/official/global/{self._today()}",
                    "model_id": f"openai/{model_name}",
                    "channel": "official",
                    "region": "global",
                    "valid_from": self._today(),
                    "input_price_per_1m": input_price,
                    "output_price_per_1m": output_price,
                    "source": PRICING_URL,
                })
        return pricings

    def _parse_pricing_from_table(self, soup) -> list[dict]:
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
