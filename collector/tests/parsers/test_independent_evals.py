import json
from modelinfo.parsers.artificialanalysis import ArtificialAnalysisParser, AA_BENCHMARK_MAP, AA_PROVIDER_MAP
from modelinfo.parsers.lmarena import LMArenaParser, LMARENA_CATEGORY_MAP, LMARENA_PROVIDER_MAP


def test_aa_benchmark_map():
    for aa_key, db_key in AA_BENCHMARK_MAP.items():
        assert isinstance(aa_key, str)
        assert isinstance(db_key, str)


def test_aa_provider_map():
    assert AA_PROVIDER_MAP["OpenAI"] == "openai"
    assert AA_PROVIDER_MAP["Anthropic"] == "anthropic"
    assert AA_PROVIDER_MAP["Google"] == "google"


def test_aa_build_eval():
    parser = ArtificialAnalysisParser.__new__(ArtificialAnalysisParser)
    parser.fetcher = None

    model_entry = {
        "slug": "claude-opus-4-6",
        "creator": "Anthropic",
        "intelligence_index": 57,
        "coding_index": 48,
        "math_index": 52,
        "mmlu_pro": 82.2,
        "gpqa": 84.0,
        "hle": 28.5,
        "aime": 56.7,
        "livecodebench": 62.3,
        "scicode": 45.1,
        "ifbench": 71.2,
        "aa_lcr": 38.9,
        "speed": 45,
        "ttft": 19.13,
    }

    result = parser._build_eval(model_entry)
    assert result is not None
    assert result["model_id"] == "anthropic/claude-opus-4-6"
    assert result["aa_intelligence_index"] == 57
    assert result["aa_coding_index"] == 48
    assert result["mmlu_pro"] == 82.2
    assert result["gpqa"] == 84.0
    assert result["tokens_per_second"] == 45
    assert result["ttft_ms"] == 19130


def test_aa_build_eval_empty():
    parser = ArtificialAnalysisParser.__new__(ArtificialAnalysisParser)
    parser.fetcher = None
    result = parser._build_eval({"slug": "test"})
    assert result is None


def test_lmarena_category_map():
    assert "full" in LMARENA_CATEGORY_MAP
    assert "coding" in LMARENA_CATEGORY_MAP
    assert "math" in LMARENA_CATEGORY_MAP
    assert "hard_6" in LMARENA_CATEGORY_MAP


def test_lmarena_infer_provider():
    assert LMArenaParser._infer_provider("claude-opus-4-6") == "anthropic"
    assert LMArenaParser._infer_provider("gpt-5.5") == "openai"
    assert LMArenaParser._infer_provider("gemini-3-pro") == "google"
    assert LMArenaParser._infer_provider("deepseek-v4-pro") == "deepseek"
    assert LMArenaParser._infer_provider("qwen3-max") == "alibaba"


def test_lmarena_build_eval():
    parser = LMArenaParser.__new__(LMArenaParser)
    parser.fetcher = None

    categories = {
        "lmarena_elo": {"claude-opus-4-6": {"rating": 1502, "rating_q975": 1508, "rating_q025": 1496}},
        "lmarena_coding": {"claude-opus-4-6": {"rating": 1480, "rating_q975": 1490, "rating_q025": 1470}},
        "lmarena_math": {"claude-opus-4-6": {"rating": 1495, "rating_q975": 1505, "rating_q025": 1485}},
        "lmarena_hard": {"claude-opus-4-6": {"rating": 1510, "rating_q975": 1520, "rating_q025": 1500}},
    }

    result = parser._build_eval("claude-opus-4-6", categories, "2026-05-12")
    assert result is not None
    assert result["model_id"] == "anthropic/claude-opus-4-6"
    assert result["lmarena_elo"] == 1502
    assert result["lmarena_coding"] == 1480
    assert result["lmarena_math"] == 1495
    assert result["lmarena_hard"] == 1510


def test_lmarena_build_eval_no_rating():
    parser = LMArenaParser.__new__(LMArenaParser)
    parser.fetcher = None
    categories = {"lmarena_elo": {}}
    result = parser._build_eval("nonexistent-model", categories, "2026-05-12")
    assert result is None
