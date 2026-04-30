import json

import pytest
from modelinfo.fetcher import Fetcher
from modelinfo.parsers.openrouter import OpenRouterParser


@pytest.mark.asyncio
async def test_parse_models_from_fixture(httpx_mock, openrouter_response):
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
    )
    async with Fetcher() as fetcher:
        parser = OpenRouterParser(fetcher)
        models = await parser.fetch_models()

    assert len(models) == 3
    model_ids = [m["model_id"] for m in models]
    assert "openai/gpt-4o" in model_ids
    assert "anthropic/claude-sonnet-4-6" in model_ids
    assert "google/gemini-2.5-flash" in model_ids

    gpt4o = [m for m in models if m["model_id"] == "openai/gpt-4o"][0]
    assert gpt4o["provider"] == "openai"
    assert gpt4o["context_length"] == 128000
    assert gpt4o["max_output_tokens"] == 16384

    caps = json.loads(gpt4o["capabilities"])
    assert caps["text"] is True
    assert caps["vision"] is True


@pytest.mark.asyncio
async def test_parse_pricing_from_fixture(httpx_mock, openrouter_response):
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
    )
    async with Fetcher() as fetcher:
        parser = OpenRouterParser(fetcher)
        pricings = await parser.fetch_pricing()

    assert len(pricings) >= 2  # gpt-4o and claude have pricing

    gpt_pricing = [p for p in pricings if p["model_id"] == "openai/gpt-4o"][0]
    assert gpt_pricing["channel"] == "marketplace"
    assert gpt_pricing["market_name"] == "openrouter"
    assert gpt_pricing["input_price_per_1m"] == 2.5
    assert gpt_pricing["output_price_per_1m"] == 10.0
    assert gpt_pricing["price_per_image"] == 0.003125


@pytest.mark.asyncio
async def test_capabilities_from_modality(httpx_mock, openrouter_response):
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
    )
    async with Fetcher() as fetcher:
        parser = OpenRouterParser(fetcher)
        models = await parser.fetch_models()

    # text+image->text should set text=True, vision=True, code=True (default for text models), video=False
    for m in models:
        caps = json.loads(m["capabilities"])
        assert caps["text"] is True
        if m["model_id"] == "google/gemini-2.5-flash":
            # Gemini has no image pricing but modality says text+image->text
            assert caps["vision"] is True
