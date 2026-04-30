from modelinfo.db import Database, init_schema
from modelinfo.writer import Writer

def test_writer_upserts_models():
    db = Database(url="file:test_writer_models.db", auth_token="")
    init_schema(db)
    writer = Writer(db)
    models = [{"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"}]
    result = writer.write_models(models)
    assert result["upserted"] == 1
    assert result["errors"] == 0

def test_writer_skips_invalid_models():
    db = Database(url="file:test_writer_invalid.db", auth_token="")
    init_schema(db)
    writer = Writer(db)
    models = [
        {"model_id": "valid/model", "model_name": "Valid", "provider": "test"},
        {"model_name": "Missing ID"},  # invalid
    ]
    result = writer.write_models(models)
    assert result["upserted"] == 1
    assert result["errors"] == 1

def test_writer_upserts_pricing():
    db = Database(url="file:test_writer_pricing.db", auth_token="")
    init_schema(db)
    writer = Writer(db)
    pricings = [{
        "pricing_id": "openai/gpt-4o/official/global/2025-01-01",
        "model_id": "openai/gpt-4o", "channel": "official",
        "valid_from": "2025-01-01", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0,
    }]
    result = writer.write_pricing(pricings)
    assert result["upserted"] == 1
