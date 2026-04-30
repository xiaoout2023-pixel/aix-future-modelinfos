from modelinfo.normalizer import (
    normalize_model_id, normalize_price_to_1m, normalize_context_length,
    normalize_date, normalize_tags,
)


def test_normalize_model_id():
    assert normalize_model_id("openai/gpt-4o") == "openai/gpt-4o"
    assert normalize_model_id("GPT-4o", provider="openai") == "openai/gpt-4o"
    assert normalize_model_id("  OpenAI/GPT-4o  ") == "openai/gpt-4o"


def test_normalize_price_to_1m():
    assert normalize_price_to_1m("0.0000025") == 2.5
    assert normalize_price_to_1m(2.5) == 2.5
    assert normalize_price_to_1m(None) is None
    assert normalize_price_to_1m("$2.50 / 1M tokens") == 2.5
    assert normalize_price_to_1m("3.00") == 3.0


def test_normalize_context_length():
    assert normalize_context_length("128,000") == 128000
    assert normalize_context_length("128K") == 128000
    assert normalize_context_length("1M") == 1000000
    assert normalize_context_length(128000) == 128000
    assert normalize_context_length(None) is None
    assert normalize_context_length("") is None


def test_normalize_date():
    assert normalize_date("2025-01-15") == "2025-01-15"
    assert normalize_date("2025/01/15") == "2025-01-15"
    assert normalize_date("Jan 15, 2025") == "2025-01-15"
    assert normalize_date(None) is None


def test_normalize_tags():
    result = normalize_tags(["Chat", "  VISION  ", "CODING", "chat"])
    assert "chat" in result
    assert "vision" in result
    assert "coding" in result
    assert len(result) == 3  # deduplicated
    assert normalize_tags([]) == []
    assert normalize_tags(None) == []
