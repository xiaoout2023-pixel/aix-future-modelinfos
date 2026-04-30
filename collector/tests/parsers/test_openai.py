import json
import pytest
from modelinfo.fetcher import Fetcher
from modelinfo.parsers.openai import OpenAIParser


@pytest.mark.asyncio
async def test_parse_models_from_html(openai_models_html):
    async with Fetcher() as fetcher:
        parser = OpenAIParser(fetcher)
        models = await parser.fetch_models(html_override=openai_models_html)

    assert len(models) == 3
    model_names = [m["model_name"] for m in models]
    assert "gpt-4o" in model_names
    assert "gpt-4o-mini" in model_names

    gpt4o = [m for m in models if m["model_name"] == "gpt-4o"][0]
    assert gpt4o["model_id"] == "openai/gpt-4o"
    assert gpt4o["context_length"] == 128000
    assert gpt4o["max_output_tokens"] == 16384


@pytest.mark.asyncio
async def test_parse_pricing_from_html(openai_pricing_html):
    async with Fetcher() as fetcher:
        parser = OpenAIParser(fetcher)
        pricings = await parser.fetch_pricing(html_override=openai_pricing_html)

    assert len(pricings) == 3

    gpt4o_p = [p for p in pricings if p["model_id"] == "openai/gpt-4o"][0]
    assert gpt4o_p["input_price_per_1m"] == 2.50
    assert gpt4o_p["output_price_per_1m"] == 10.00
    assert gpt4o_p["channel"] == "official"


@pytest.mark.asyncio
async def test_parse_int_handles_formats():
    async with Fetcher() as fetcher:
        parser = OpenAIParser(fetcher)
    assert parser._parse_int("128,000") == 128000
    assert parser._parse_int("1,000,000") == 1000000
    assert parser._parse_int("") is None


@pytest.mark.asyncio
async def test_parse_price_handles_formats():
    async with Fetcher() as fetcher:
        parser = OpenAIParser(fetcher)
    assert parser._parse_price("$2.50 / 1M tokens") == 2.50
    assert parser._parse_price("$10.00 / 1M tokens") == 10.00
    assert parser._parse_price("Free") == 0.0
    assert parser._parse_price("") is None
