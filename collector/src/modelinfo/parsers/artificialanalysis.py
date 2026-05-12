import os
import json
from datetime import date
from modelinfo.parsers.base import BaseParser
import structlog

logger = structlog.get_logger()

API_BASE = "https://api.artificialanalysis.ai/v1"

AA_PROVIDER_MAP = {
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "Google": "google",
    "Meta": "meta",
    "DeepSeek": "deepseek",
    "Mistral": "mistral",
    "Alibaba": "alibaba",
    "NVIDIA": "nvidia",
    "xAI": "xai",
    "Z.ai": "zhipu",
    "Cohere": "cohere",
    "MiniMax": "minimax",
    "Moonshot": "moonshot",
    "Xiaomi": "xiaomi",
    "Microsoft": "microsoft",
    "Amazon": "amazon",
    "Reka": "reka",
    "01.AI": "01ai",
    "AI21 Labs": "ai21",
    "Cerebras": "cerebras",
    "Groq": "groq",
    "Together": "together",
    "Perplexity": "perplexity",
}

AA_BENCHMARK_MAP = {
    "mmlu_pro": "mmlu_pro",
    "gpqa": "gpqa",
    "hle": "hle",
    "aime": "aime",
    "livecodebench": "livecodebench",
    "scicode": "scicode",
    "ifbench": "ifbench",
    "aa_lcr": "aa_lcr",
    "intelligence_index": "aa_intelligence_index",
    "coding_index": "aa_coding_index",
    "math_index": "aa_math_index",
}


class ArtificialAnalysisParser(BaseParser):
    source_name = "artificialanalysis"

    def __init__(self, fetcher):
        super().__init__(fetcher)
        self.api_key = os.environ.get("AA_API_KEY", "")

    async def fetch_evaluations(self) -> list[dict]:
        if not self.api_key:
            logger.warning("aa_no_api_key")
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            data = await self.fetcher.fetch_json(f"{API_BASE}/models", headers=headers)
        except Exception as e:
            logger.error("aa_fetch_models_failed", error=str(e))
            return []

        if not isinstance(data, list):
            data = data.get("models", data.get("data", []))

        logger.info("aa_fetching", total_models=len(data))

        evals = []
        for model_entry in data:
            try:
                eval_record = self._build_eval(model_entry)
                if eval_record:
                    evals.append(eval_record)
            except Exception as e:
                slug = model_entry.get("slug", model_entry.get("id", "?"))
                logger.warning("aa_model_failed", slug=slug, error=str(e))
                continue

        logger.info("aa_done", total_evals=len(evals))
        return evals

    def _build_eval(self, model_entry: dict) -> dict | None:
        slug = model_entry.get("slug", model_entry.get("id", ""))
        creator = model_entry.get("creator", "")
        provider = AA_PROVIDER_MAP.get(creator, creator.lower().replace(" ", "-") if creator else "unknown")
        db_model_id = f"{provider}/{slug}" if provider else slug

        mapped = {}
        other = {}

        for aa_key, db_key in AA_BENCHMARK_MAP.items():
            val = model_entry.get(aa_key)
            if val is not None:
                try:
                    mapped[db_key] = float(val)
                except (ValueError, TypeError):
                    pass

        speed = model_entry.get("speed")
        if speed is not None:
            try:
                mapped["tokens_per_second"] = int(float(speed))
            except (ValueError, TypeError):
                pass

        ttft = model_entry.get("ttft")
        if ttft is not None:
            try:
                mapped["ttft_ms"] = int(float(ttft) * 1000)
            except (ValueError, TypeError):
                pass

        if not mapped:
            return None

        today = self._today()
        return {
            "eval_id": f"{db_model_id}/artificialanalysis/{today}",
            "model_id": db_model_id,
            "eval_date": today,
            "source": "https://artificialanalysis.ai",
            **mapped,
            "other_benchmarks": json.dumps(other) if other else None,
        }

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
