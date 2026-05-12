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
    "Amazon": "amazon",
    "Microsoft": "microsoft",
    "01.AI": "01ai",
    "AI21 Labs": "ai21",
    "Reka": "reka",
}


class LLMRegistryParser(BaseParser):
    source_name = "llmregistry"

    async def fetch_evaluations(self) -> list[dict]:
        all_scores = await self._fetch_all_scores()
        if not all_scores:
            logger.warning("llmregistry_no_scores")
            return []

        logger.info("llmregistry_fetching", total_scores=len(all_scores))

        independent = [s for s in all_scores if s.get("sourceId") in INDEPENDENT_SOURCES]
        logger.info("llmregistry_independent", count=len(independent))

        model_scores: dict[str, dict[str, float]] = {}
        model_providers: dict[str, str] = {}
        for s in independent:
            mid = s.get("modelId", "")
            if not mid:
                continue
            model_providers[mid] = s.get("provider", "")
            if mid not in model_scores:
                model_scores[mid] = {}
            bench_id = s.get("benchmarkId", "")
            score = s.get("score")
            if bench_id and score is not None:
                model_scores[mid][bench_id] = score

        evals = []
        for mid, scores in model_scores.items():
            eval_record = self._build_eval(mid, scores, model_providers.get(mid, ""))
            if eval_record:
                evals.append(eval_record)

        logger.info("llmregistry_done", total_evals=len(evals))
        return evals

    async def _fetch_all_scores(self) -> list[dict]:
        all_scores = []
        offset = 0
        limit = 5000
        while True:
            try:
                data = await self.fetcher.fetch_json(
                    f"{API_BASE}/scores?limit={limit}&offset={offset}"
                )
            except Exception as e:
                logger.error("llmregistry_fetch_scores_failed", offset=offset, error=str(e))
                break

            if not isinstance(data, dict):
                logger.warning("llmregistry_unexpected_format")
                break

            scores = data.get("scores", [])
            all_scores.extend(scores)

            total = data.get("total", 0)
            if offset + limit >= total or len(scores) < limit:
                break
            offset += limit
            await asyncio.sleep(0.5)

        return all_scores

    def _build_eval(self, model_id: str, scores: dict, provider_raw: str) -> dict | None:
        provider = PROVIDER_MAP.get(provider_raw, provider_raw.lower().replace(" ", "-") if provider_raw else model_id.split("-")[0])
        db_model_id = f"{provider}/{model_id}" if provider else model_id

        mapped = {}
        other = {}
        for bench_id, score in scores.items():
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
