import json
from datetime import date

from modelinfo.parsers.base import BaseParser


class OpenRouterParser(BaseParser):
    source_name = "openrouter"

    API_URL = "https://openrouter.ai/api/v1/models"

    async def fetch_models(self) -> list[dict]:
        data = await self.fetcher.fetch_json(self.API_URL)
        models = []
        for m in data.get("data", []):
            model_id = m["id"]
            model_slug = self._slug(model_id)
            caps_dict = json.loads(self._parse_capabilities(m))
            model = {
                "model_id": model_id,
                "model_name": m.get("name", model_id),
                "provider": model_id.split("/")[0],
                "provider_type": "closed",
                "context_length": m.get("context_length"),
                "max_output_tokens": (m.get("top_provider") or {}).get("max_completion_tokens"),
                "capabilities": self._parse_capabilities(m),
                "urls": json.dumps({"official": f"https://openrouter.ai/models/{model_slug}"}),
                "tags": self._derive_tags(caps_dict),
                "aliases": json.dumps([model_id]),
            }
            models.append(model)
        return models

    async def fetch_pricing(self) -> list[dict]:
        data = await self.fetcher.fetch_json(self.API_URL)
        today = self._today()
        pricings = []
        for m in data.get("data", []):
            pricing_data = m.get("pricing")
            if not pricing_data:
                continue
            prompt = pricing_data.get("prompt")
            completion = pricing_data.get("completion")
            if prompt is None and completion is None:
                continue
            image_price = pricing_data.get("image")
            pricing = {
                "pricing_id": f"{m['id']}/openrouter/global/{today}",
                "model_id": m["id"],
                "channel": "marketplace",
                "market_name": "openrouter",
                "region": "global",
                "valid_from": today,
                "input_price_per_1m": float(prompt) * 1_000_000 if prompt else None,
                "output_price_per_1m": float(completion) * 1_000_000 if completion else None,
                "price_per_image": float(image_price) if image_price else None,
                "source": f"https://openrouter.ai/api/v1/models/{m['id']}",
            }
            pricings.append(pricing)
        return pricings

    # -- helpers ------------------------------------------------------------

    def _parse_capabilities(self, m: dict) -> str:
        modality = (m.get("architecture") or {}).get("modality", "")
        caps = {
            "text": "text" in modality,
            "code": "text" in modality,
            "reasoning": False,
            "vision": "image" in modality,
            "image_gen": False,
            "audio": False,
            "audio_gen": False,
            "video": False,
            "tool_use": False,
            "structured_output": False,
            "streaming": False,
            "batch": False,
            "fine_tuning": False,
            "embedding": False,
        }
        return json.dumps(caps)

    def _derive_tags(self, caps: dict) -> str:
        tags = []
        if caps.get("vision"):
            tags.append("multimodal")
        if caps.get("code"):
            tags.append("coding")
        return json.dumps(tags)

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _slug(model_id: str) -> str:
        return model_id.split("/", 1)[1] if "/" in model_id else model_id
