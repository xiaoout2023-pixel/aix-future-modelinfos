import json
from datetime import date
from modelinfo.parsers.base import BaseParser
import structlog

logger = structlog.get_logger()

LEADERBOARD_URL = "https://raw.githubusercontent.com/lmarena/arena-catalog/main/data/leaderboard-text.json"

LMARENA_PROVIDER_MAP = {
    "claude": "anthropic",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "gemini": "google",
    "llama": "meta",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "qwen": "alibaba",
    "nvidia": "nvidia",
    "grok": "xai",
    "glm": "zhipu",
    "command": "cohere",
    "minimax": "minimax",
    "kimi": "moonshot",
    "mimo": "xiaomi",
    "phi": "microsoft",
    "nova": "amazon",
    "yi": "01ai",
    "jamba": "ai21",
    "reka": "reka",
    "sonar": "perplexity",
    "dolphin": "cognitivecomputations",
    "together": "together",
}

LMARENA_CATEGORY_MAP = {
    "full": "lmarena_elo",
    "coding": "lmarena_coding",
    "math": "lmarena_math",
    "hard_6": "lmarena_hard",
}


class LMArenaParser(BaseParser):
    source_name = "lmarena"

    async def fetch_evaluations(self) -> list[dict]:
        try:
            data = await self.fetcher.fetch_json(LEADERBOARD_URL)
        except Exception as e:
            logger.error("lmarena_fetch_failed", error=str(e))
            return []

        if not isinstance(data, dict):
            logger.warning("lmarena_unexpected_format")
            return []

        categories = {}
        for cat_key, db_field in LMARENA_CATEGORY_MAP.items():
            cat_data = data.get(cat_key)
            if isinstance(cat_data, dict):
                categories[db_field] = cat_data

        if not categories:
            logger.warning("lmarena_no_categories")
            return []

        all_models = set()
        for cat_data in categories.values():
            all_models.update(cat_data.keys())

        logger.info("lmarena_fetching", total_models=len(all_models), categories=len(categories))

        evals = []
        today = self._today()
        for model_name in all_models:
            eval_record = self._build_eval(model_name, categories, today)
            if eval_record:
                evals.append(eval_record)

        logger.info("lmarena_done", total_evals=len(evals))
        return evals

    def _build_eval(self, model_name: str, categories: dict, today: str) -> dict | None:
        provider = self._infer_provider(model_name)
        db_model_id = f"{provider}/{model_name}" if provider else model_name

        mapped = {}
        other = {}
        for db_field, cat_data in categories.items():
            entry = cat_data.get(model_name)
            if isinstance(entry, dict) and "rating" in entry:
                mapped[db_field] = entry["rating"]

        if not mapped:
            return None

        return {
            "eval_id": f"{db_model_id}/lmarena/{today}",
            "model_id": db_model_id,
            "eval_date": today,
            "source": "https://lmarena.ai",
            **mapped,
            "other_benchmarks": json.dumps(other) if other else None,
        }

    @staticmethod
    def _infer_provider(model_name: str) -> str:
        lower = model_name.lower()
        for prefix, provider in LMARENA_PROVIDER_MAP.items():
            if lower.startswith(prefix):
                return provider
        parts = model_name.split("-", 1)
        if len(parts) > 1:
            return parts[0].lower()
        return "unknown"

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
