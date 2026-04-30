import json
import pytest
from modelinfo.fetcher import Fetcher
from modelinfo.parsers.anthropic import AnthropicParser


@pytest.mark.asyncio
async def test_parse_models_from_html(anthropic_models_html):
    async with Fetcher() as fetcher:
        parser = AnthropicParser(fetcher)
        models = await parser.fetch_models(html_override=anthropic_models_html)

    assert len(models) == 3
    model_names = [m["model_name"] for m in models]
    assert "claude sonnet 4.6" in model_names
    assert "claude opus 4.7" in model_names
    assert "claude haiku 4.5" in model_names

    sonnet = [m for m in models if "sonnet" in m["model_name"]][0]
    assert sonnet["context_length"] == 200000
    assert sonnet["max_output_tokens"] == 8192
    caps = json.loads(sonnet["capabilities"])
    assert caps["reasoning"] is True
    assert caps["vision"] is True
    assert caps["tool_use"] is True


@pytest.mark.asyncio
async def test_parse_pricing_from_html(anthropic_pricing_html):
    async with Fetcher() as fetcher:
        parser = AnthropicParser(fetcher)
        pricings = await parser.fetch_pricing(html_override=anthropic_pricing_html)

    assert len(pricings) == 3

    sonnet_p = [p for p in pricings if "sonnet" in p["model_id"]][0]
    assert sonnet_p["input_price_per_1m"] == 3.00
    assert sonnet_p["output_price_per_1m"] == 15.00
    assert sonnet_p["channel"] == "official"
    # Should detect thinking token info in page text
    assert sonnet_p["reasoning_tokens_charged"] is True


@pytest.mark.asyncio
async def test_parse_mtok_pricing():
    async with Fetcher() as fetcher:
        parser = AnthropicParser(fetcher)
    assert parser._parse_price("$3.00 / MTok") == 3.00
    assert parser._parse_price("$75.00 / MTok") == 75.00
    assert parser._parse_price("") is None
