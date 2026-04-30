import pytest
from modelinfo.db import Database, init_schema
from modelinfo.fetcher import Fetcher
from modelinfo.writer import Writer
from modelinfo.validator import validate_model, validate_pricing
from modelinfo.parsers.openrouter import OpenRouterParser


@pytest.mark.asyncio
async def test_full_pipeline_openrouter(httpx_mock, openrouter_response):
    """End-to-end: fetch from OpenRouter, validate, write to DB, verify."""
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
        is_reusable=True,
    )

    db = Database(url="file:test_integration_full.db", auth_token="")
    init_schema(db)
    writer = Writer(db)

    async with Fetcher() as fetcher:
        parser = OpenRouterParser(fetcher)

        # Fetch and write models
        models = await parser.fetch_models()
        assert len(models) == 3
        for m in models:
            errors = validate_model(m)
            assert len(errors) == 0, f"Validation errors for {m['model_id']}: {errors}"

        result = writer.write_models(models)
        assert result["upserted"] == 3
        assert result["errors"] == 0

        # Fetch and write pricing
        pricings = await parser.fetch_pricing()
        for p in pricings:
            errors = validate_pricing(p)
            assert len(errors) == 0, f"Validation errors for {p['pricing_id']}: {errors}"

        result_p = writer.write_pricing(pricings)
        assert result_p["upserted"] == 3
        assert result_p["errors"] == 0

    # Verify DB state
    all_models = db.get_all_models()
    assert len(all_models) == 3
    model_ids = [m["model_id"] for m in all_models]
    assert "openai/gpt-4o" in model_ids

    # Verify pricing
    gpt_pricing = db.get_all_pricing_for_model("openai/gpt-4o")
    assert len(gpt_pricing) >= 1
    assert gpt_pricing[0]["channel"] == "marketplace"


@pytest.mark.asyncio
async def test_pipeline_idempotency(httpx_mock, openrouter_response):
    """Running the same fetch twice should produce zero or fewer changes on second run."""
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/models",
        json=openrouter_response,
        is_reusable=True,
    )

    db = Database(url="file:test_integration_idempotent.db", auth_token="")
    init_schema(db)
    writer = Writer(db)

    async with Fetcher() as fetcher:
        parser = OpenRouterParser(fetcher)

        # First run
        models1 = await parser.fetch_models()
        result1 = writer.write_models(models1)
        assert result1["upserted"] == 3

        pricings1 = await parser.fetch_pricing()
        result1p = writer.write_pricing(pricings1)
        assert result1p["upserted"] == 3

        # Second run with same data
        models2 = await parser.fetch_models()
        result2 = writer.write_models(models2)
        # Second run upserts should still succeed (idempotent upsert)
        assert result2["upserted"] == 3

        pricings2 = await parser.fetch_pricing()
        result2p = writer.write_pricing(pricings2)
        assert result2p["upserted"] == 3

    # Second run should still have 3 models (upsert is idempotent)
    all_models = db.get_all_models()
    assert len(all_models) == 3


@pytest.mark.asyncio
async def test_database_query_methods():
    """Test basic DB query methods work correctly."""
    db = Database(url="file:test_integration_queries.db", auth_token="")
    init_schema(db)

    # Insert test data
    db.upsert_model({"model_id": "test/model-a", "model_name": "Model A", "provider": "test"})
    db.upsert_model({"model_id": "test/model-b", "model_name": "Model B", "provider": "test"})

    all_models = db.get_all_models()
    assert len(all_models) == 2

    db.upsert_pricing({
        "pricing_id": "test/model-a/official/global/2025-01-01",
        "model_id": "test/model-a", "channel": "official",
        "valid_from": "2025-01-01", "input_price_per_1m": 1.0, "output_price_per_1m": 4.0,
    })

    latest = db.get_latest_pricing("test/model-a", "official", "global")
    assert latest is not None
    assert latest["input_price_per_1m"] == 1.0

    none_pricing = db.get_latest_pricing("nonexistent", "official", "global")
    assert none_pricing is None
