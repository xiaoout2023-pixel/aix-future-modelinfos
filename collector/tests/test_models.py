# collector/tests/test_models.py
from datetime import date
from modelinfo.models import ModelInfo, PricingInfo, Capabilities, Urls, Channel

def test_model_info_minimal():
    m = ModelInfo(model_id="openai/gpt-4o", model_name="GPT-4o", provider="openai")
    assert m.model_id == "openai/gpt-4o"
    assert m.capabilities.text is False
    assert m.tags == []

def test_model_info_full():
    m = ModelInfo(
        model_id="anthropic/claude-sonnet-4-6",
        model_name="Claude Sonnet 4.6",
        provider="anthropic",
        provider_type="closed",
        release_date=date(2025, 6, 15),
        aliases=["claude-sonnet-4-6-20250615"],
        capabilities=Capabilities(text=True, code=True, reasoning=True, vision=True, tool_use=True),
        context_length=200000,
        max_output_tokens=8192,
        urls=Urls(official="https://anthropic.com/claude", pricing="https://anthropic.com/pricing"),
    )
    assert m.capabilities.text is True
    assert m.capabilities.video is False
    assert m.context_length == 200000

def test_pricing_info():
    p = PricingInfo(
        pricing_id="openai/gpt-4o/official/global/2025-01-01",
        model_id="openai/gpt-4o",
        channel=Channel.OFFICIAL,
        valid_from=date(2025, 1, 1),
        input_price_per_1m=2.5,
        output_price_per_1m=10.0,
    )
    assert p.input_price_per_1m == 2.5
    assert p.cache_read_price_per_1m is None

def test_capabilities_default_false():
    c = Capabilities()
    assert c.text is False
    assert c.video is False
    assert c.embedding is False
