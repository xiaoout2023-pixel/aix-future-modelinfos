import asyncio
import json
from datetime import date
from modelinfo.parsers.base import BaseParser
import structlog

logger = structlog.get_logger()

API_BASE = "https://llm-registry.com/api/v1"

BENCHMARK_MAP = {
    "mmlu": "mmlu",
    "mmlu-pro": "mmlu_pro",
    "gpqa-diamond": "gpqa",
    "lmarena-elo": "lmarena_elo",
}

INDEPENDENT_SOURCES = {"artificial-analysis", "livebench", "lmarena", "hf-open-llm"}

PROVIDER_MAP = {
    "Anthropic": "anthropic",
    "OpenAI": "openai",
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
}


class LLMRegistryParser(BaseParser):
    source_name = "llmregistry"

    async def fetch_evaluations(self) -> list[dict]:
        models_data = await self.fetcher.fetch_json(f"{API_BASE}/models")
        if not isinstance(models_data, dict) or "models" not in models_data:
            logger.warning("llmregistry_no_models")
            return []

        models_list = models_data["models"]
        logger.info("llmregistry_fetching", total_models=len(models_list))

        evals = []
        for model_entry in models_list:
            model_id = model_entry.get("id", "")
            if not model_id:
                continue
            try:
                detail = await self.fetcher.fetch_json(f"{API_BASE}/models/{model_id}")
                if not isinstance(detail, dict) or "model" not in detail:
                    continue
                scores = detail["model"].get("scores", {})
                if not scores:
                    continue
                eval_record = self._build_eval(model_entry, scores)
                if eval_record:
                    evals.append(eval_record)
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning("llmregistry_model_failed", model_id=model_id, error=str(e))
                continue

        logger.info("llmregistry_done", total_evals=len(evals))
        return evals

    def _build_eval(self, model_entry: dict, scores: dict) -> dict | None:
        model_id = model_entry.get("id", "")
        provider_raw = model_entry.get("provider", "")
        provider = PROVIDER_MAP.get(provider_raw, provider_raw.lower().replace(" ", "-"))

        db_model_id = f"{provider}/{model_id}" if provider else model_id

        mapped = {}
        other = {}
        for bench_id, score_data in scores.items():
            if not isinstance(score_data, dict):
                continue
            source_id = score_data.get("sourceId", "")
            if source_id not in INDEPENDENT_SOURCES:
                continue
            score = score_data.get("score")
            if score is None:
                continue
            if bench_id in BENCHMARK_MAP:
                mapped[BENCHMARK_MAP[bench_id]] = score
            else:
                other[bench_id] = score

        has_mapped = any(mapped.get(k) is not None for k in BENCHMARK_MAP.values())
        if not has_mapped and not other:
            return None

        today = self._today()
        return {
            "eval_id": f"{db_model_id}/llmregistry/{today}",
            "model_id": db_model_id,
            "eval_date": today,
            "source": API_BASE,
            **mapped,
            "other_benchmarks": json.dumps(other) if other else None,
        }

    @staticmethod
    def _today() -> str:
        return date.today().isoformat()
