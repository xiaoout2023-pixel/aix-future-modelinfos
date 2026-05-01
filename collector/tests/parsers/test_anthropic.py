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

    model_ids = [m["model_id"] for m in models]
    assert "anthropic/claude-sonnet-4-6" in model_ids
    assert "anthropic/claude-opus-4-7" in model_ids
    assert "anthropic/claude-haiku-4-5-20251001" in model_ids

    opus = [m for m in models if "opus" in m["model_id"]][0]
    assert opus["context_length"] == 1000000  # 1M
    assert opus["max_output_tokens"] == 128000  # 128K
    caps = json.loads(opus["capabilities"])
    assert caps["reasoning"] is False  # Extended thinking: No

    haiku = [m for m in models if "haiku" in m["model_id"]][0]
    assert haiku["context_length"] == 200000  # 200K


@pytest.mark.asyncio
async def test_parse_pricing_from_html(anthropic_models_html):
    """Pricing is now extracted from the models page (transposed table)."""
    async with Fetcher() as fetcher:
        parser = AnthropicParser(fetcher)
        pricings = await parser.fetch_pricing(html_override=anthropic_models_html)

    assert len(pricings) == 3

    sonnet_p = [p for p in pricings if "sonnet" in p["model_id"]][0]
    assert sonnet_p["input_price_per_1m"] == 3.00
    assert sonnet_p["output_price_per_1m"] == 15.00
    assert sonnet_p["channel"] == "official"
    assert sonnet_p["reasoning_tokens_charged"] is True  # Extended thinking: Yes

    opus_p = [p for p in pricings if "opus" in p["model_id"]][0]
    assert opus_p["input_price_per_1m"] == 5.00
    assert opus_p["output_price_per_1m"] == 25.00


@pytest.mark.asyncio
async def test_parse_pricing_cell():
    async with Fetcher() as fetcher:
        parser = AnthropicParser(fetcher)
    assert parser._parse_pricing_cell("$3.00 / input MTok$15.00 / output MTok") == (3.00, 15.00)
    assert parser._parse_pricing_cell("$5 / input MTok$25 / output MTok") == (5.0, 25.0)
    assert parser._parse_pricing_cell("") == (None, None)
    assert parser._parse_pricing_cell("garbage") == (None, None)
