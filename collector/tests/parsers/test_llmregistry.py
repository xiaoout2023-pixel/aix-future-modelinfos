import json
from modelinfo.parsers.llmregistry import LLMRegistryParser, BENCHMARK_MAP, PROVIDER_MAP
from modelinfo.fetcher import Fetcher


def test_benchmark_map_keys_match_api():
    for key in BENCHMARK_MAP:
        assert isinstance(key, str)
        assert "-" in key or key == "mmlu" or key == "math"


def test_provider_map_covers_major():
    assert "Anthropic" in PROVIDER_MAP
    assert "OpenAI" in PROVIDER_MAP
    assert "Google" in PROVIDER_MAP
    assert "Meta" in PROVIDER_MAP
    assert "DeepSeek" in PROVIDER_MAP


def test_build_eval_with_scores():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None

    model_entry = {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "provider": "Anthropic",
    }
    scores = {
        "mmlu": {"score": 91.4, "sourceId": "anthropic-news"},
        "mmlu-pro": {"score": 82.2, "sourceId": "anthropic-news"},
        "gpqa-diamond": {"score": 84.0, "sourceId": "artificial-analysis"},
        "math": {"score": 89.2, "sourceId": "anthropic-news"},
        "human-eval": {"score": 94.6, "sourceId": "anthropic-news"},
        "swe-bench-verified": {"score": 80.8, "sourceId": "anthropic-news"},
        "lmarena-elo": {"score": 1502, "sourceId": "anthropic-news"},
        "arc-agi-2": {"score": 68.8, "sourceId": "anthropic-news"},
        "mmmu": {"score": 76.5, "sourceId": "anthropic-news"},
    }

    result = parser._build_eval(model_entry, scores)
    assert result is not None
    assert result["model_id"] == "anthropic/claude-opus-4-6"
    assert result["mmlu"] == 91.4
    assert result["mmlu_pro"] == 82.2
    assert result["gpqa"] == 84.0
    assert result["math_500"] == 89.2
    assert result["humaneval"] == 94.6
    assert result["swe_bench"] == 80.8
    assert result["lmarena_elo"] == 1502

    other = json.loads(result["other_benchmarks"])
    assert "arc-agi-2" in other
    assert other["arc-agi-2"] == 68.8
    assert "mmmu" in other
    assert "mmlu" not in other


def test_build_eval_empty_scores():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None

    model_entry = {"id": "test-model", "provider": "Test"}
    result = parser._build_eval(model_entry, {})
    assert result is None


def test_build_eval_unknown_provider():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None

    model_entry = {"id": "some-model", "provider": "NewCompany"}
    scores = {"mmlu": {"score": 85.0}}
    result = parser._build_eval(model_entry, scores)
    assert result is not None
    assert result["model_id"] == "newcompany/some-model"


def test_build_eval_score_none_skipped():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None

    model_entry = {"id": "test", "provider": "OpenAI"}
    scores = {"mmlu": {"score": None}, "arc-agi-2": {"score": 50.0}}
    result = parser._build_eval(model_entry, scores)
    assert result is not None
    assert result.get("mmlu") is None
    other = json.loads(result["other_benchmarks"])
    assert "arc-agi-2" in other
