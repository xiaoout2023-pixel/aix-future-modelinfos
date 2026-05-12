import os
import json
from datetime import date
from modelinfo.parsers.base import BaseParser
import structlog

logger = structlog.get_logger()

API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"

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

AA_EVAL_MAP = {
    "artificial_analysis_intelligence_index": "aa_intelligence_index",
    "artificial_analysis_coding_index": "aa_coding_index",
    "artificial_analysis_math_index": "aa_math_index",
    "mmlu_pro": "mmlu_pro",
    "gpqa": "gpqa",
    "hle": "hle",
    "aime": "aime",
    "livecodebench": "livecodebench",
    "scicode": "scicode",
    "ifbench": "ifbench",
    "lcr": "aa_lcr",
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
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        try:
            resp = await self.fetcher.fetch_json(API_URL, headers=headers)
        except Exception as e:
            logger.error("aa_fetch_models_failed", error=str(e))
            return []

        if isinstance(resp, dict):
            if resp.get("status") != 200:
                logger.error("aa_api_error", status=resp.get("status"))
                return []
            data = resp.get("data", [])
        elif isinstance(resp, list):
            data = resp
        else:
            logger.warning("aa_unexpected_format", resp_type=type(resp).__name__)
            return []

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
        creator_obj = model_entry.get("model_creator", {})
        creator_name = creator_obj.get("name", "") if isinstance(creator_obj, dict) else ""
        if not creator_name:
            creator_name = model_entry.get("creator", "")
        provider = AA_PROVIDER_MAP.get(creator_name, creator_name.lower().replace(" ", "-") if creator_name else "unknown")
        db_model_id = f"{provider}/{slug}" if provider else slug

        evaluations = model_entry.get("evaluations", {})
        if not isinstance(evaluations, dict):
            evaluations = {}

        mapped = {}
        other = {}

        for aa_key, db_key in AA_EVAL_MAP.items():
            val = evaluations.get(aa_key)
            if val is not None:
                try:
                    mapped[db_key] = float(val)
                except (ValueError, TypeError):
                    pass

        for extra_key in ("aime_25", "math_500", "terminalbench_hard", "tau2"):
            val = evaluations.get(extra_key)
            if val is not None:
                other[extra_key] = val

        speed = model_entry.get("median_output_tokens_per_second")
        if speed is not None:
            try:
                mapped["tokens_per_second"] = int(float(speed))
            except (ValueError, TypeError):
                pass

        ttft_sec = model_entry.get("median_time_to_first_token_seconds")
        if ttft_sec is not None:
            try:
                mapped["ttft_ms"] = int(float(ttft_sec) * 1000)
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
