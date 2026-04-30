import pytest
from modelinfo.db import Database, init_schema


def test_init_schema_creates_tables():
    db = Database(url="file:test_schema.db", auth_token="")
    init_schema(db)
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [r[0] for r in tables]
    for t in ["models", "pricing", "evaluations", "change_log"]:
        assert t in table_names


def test_upsert_model_inserts_and_is_idempotent():
    db = Database(url="file:test_upsert.db", auth_token="")
    init_schema(db)
    data = {"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"}
    db.upsert_model(data)
    db.upsert_model(data)  # should not raise or duplicate
    rows = db.execute("SELECT count(*) FROM models WHERE model_id=?", ["openai/gpt-4o"])
    assert rows[0][0] == 1


def test_get_latest_pricing_returns_most_recent():
    db = Database(url="file:test_pricing.db", auth_token="")
    init_schema(db)
    db.upsert_pricing({
        "pricing_id": "a/official/global/2025-01-01",
        "model_id": "a", "channel": "official", "valid_from": "2025-01-01",
        "input_price_per_1m": 2.5, "output_price_per_1m": 10.0,
    })
    db.upsert_pricing({
        "pricing_id": "a/official/global/2025-03-01",
        "model_id": "a", "channel": "official", "valid_from": "2025-03-01",
        "input_price_per_1m": 2.0, "output_price_per_1m": 8.0,
    })
    latest = db.get_latest_pricing("a", "official", "global")
    assert latest["input_price_per_1m"] == 2.0
    assert latest["output_price_per_1m"] == 8.0


def test_get_all_pricing_for_model():
    db = Database(url="file:test_all_pricing.db", auth_token="")
    init_schema(db)
    db.upsert_pricing({
        "pricing_id": "x/official/global/2025-01-01",
        "model_id": "x", "channel": "official", "valid_from": "2025-01-01",
        "input_price_per_1m": 1.0, "output_price_per_1m": 4.0,
    })
    db.upsert_pricing({
        "pricing_id": "x/marketplace/global/2025-01-01",
        "model_id": "x", "channel": "marketplace", "market_name": "openrouter",
        "valid_from": "2025-01-01", "input_price_per_1m": 1.2, "output_price_per_1m": 4.8,
    })
    all_p = db.get_all_pricing_for_model("x")
    assert len(all_p) == 2


def test_upsert_evaluation():
    db = Database(url="file:test_eval.db", auth_token="")
    init_schema(db)
    db.upsert_evaluation({
        "eval_id": "openai/gpt-4o/artificial_analysis/2025-01-01",
        "model_id": "openai/gpt-4o", "eval_date": "2025-01-01",
        "source": "artificial_analysis", "tokens_per_second": 85, "overall_score": 88.5,
    })
    rows = db.execute("SELECT tokens_per_second, overall_score FROM evaluations WHERE eval_id=?",
                       ["openai/gpt-4o/artificial_analysis/2025-01-01"])
    assert rows[0][0] == 85
    assert rows[0][1] == 88.5
