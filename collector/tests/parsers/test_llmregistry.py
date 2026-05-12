import json
from modelinfo.parsers.llmregistry import LLMRegistryParser, BENCHMARK_MAP, PROVIDER_MAP, INDEPENDENT_SOURCES


def test_benchmark_map_keys_match_api():
    for key in BENCHMARK_MAP:
        assert isinstance(key, str)


def test_provider_map_covers_major():
    assert "Anthropic" in PROVIDER_MAP
    assert "OpenAI" in PROVIDER_MAP
    assert "Google" in PROVIDER_MAP


def test_independent_sources_filter():
    assert "artificial-analysis" in INDEPENDENT_SOURCES
    assert "livebench" in INDEPENDENT_SOURCES
    assert "anthropic-news" not in INDEPENDENT_SOURCES
    assert "openai-news" not in INDEPENDENT_SOURCES


def test_build_eval_with_independent_sources():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None

    model_entry = {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "provider": "Anthropic",
    }
    scores = {
        "mmlu": {"score": 91.4, "sourceId": "artificial-analysis"},
        "mmlu-pro": {"score": 82.2, "sourceId": "artificial-analysis"},
        "gpqa-diamond": {"score": 84.0, "sourceId": "artificial-analysis"},
        "lmarena-elo": {"score": 1502, "sourceId": "lmarena"},
        "arc-agi-2": {"score": 68.8, "sourceId": "livebench"},
        "mmmu": {"score": 76.5, "sourceId": "anthropic-news"},
    }

    result = parser._build_eval(model_entry, scores)
    assert result is not None
    assert result["model_id"] == "anthropic/claude-opus-4-6"
    assert result["mmlu"] == 91.4
    assert result["mmlu_pro"] == 82.2
    assert result["gpqa"] == 84.0
    assert result["lmarena_elo"] == 1502

    other = json.loads(result["other_benchmarks"])
    assert "arc-agi-2" in other
    assert other["arc-agi-2"] == 68.8
    assert "mmmu" not in other


def test_build_eval_empty_scores():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None
    model_entry = {"id": "test-model", "provider": "Test"}
    result = parser._build_eval(model_entry, {})
    assert result is None


def test_build_eval_only_provider_sources():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None
    model_entry = {"id": "test-model", "provider": "OpenAI"}
    scores = {"mmlu": {"score": 85.0, "sourceId": "openai-news"}}
    result = parser._build_eval(model_entry, scores)
    assert result is None


def test_build_eval_unknown_provider():
    parser = LLMRegistryParser.__new__(LLMRegistryParser)
    parser.fetcher = None
    model_entry = {"id": "some-model", "provider": "NewCompany"}
    scores = {"mmlu": {"score": 85.0, "sourceId": "artificial-analysis"}}
    result = parser._build_eval(model_entry, scores)
    assert result is not None
    assert result["model_id"] == "newcompany/some-model"
