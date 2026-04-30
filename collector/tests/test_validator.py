from modelinfo.validator import validate_model, validate_pricing, validate_evaluation

def test_validate_model_missing_required():
    errors = validate_model({"model_name": "Test"})  # missing model_id, provider
    assert len(errors) > 0

def test_validate_model_valid():
    errors = validate_model({
        "model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"
    })
    assert len(errors) == 0

def test_validate_model_negative_context():
    errors = validate_model({
        "model_id": "x", "model_name": "x", "provider": "x",
        "context_length": -1
    })
    assert any("context_length" in e.lower() for e in errors)

def test_validate_pricing_negative_price():
    errors = validate_pricing({
        "pricing_id": "x", "model_id": "x", "valid_from": "2025-01-01",
        "input_price_per_1m": -1.0, "output_price_per_1m": 5.0,
    })
    assert any("negative" in e.lower() for e in errors)

def test_validate_pricing_unreasonable():
    errors = validate_pricing({
        "pricing_id": "x", "model_id": "x", "valid_from": "2025-01-01",
        "input_price_per_1m": 1000.0, "output_price_per_1m": 5.0,
    })
    assert any("unreasonable" in e.lower() for e in errors)

def test_validate_pricing_valid():
    errors = validate_pricing({
        "pricing_id": "x", "model_id": "x", "valid_from": "2025-01-01",
        "input_price_per_1m": 2.5, "output_price_per_1m": 10.0,
    })
    assert len(errors) == 0


def test_validate_evaluation_valid():
    errors = validate_evaluation({
        "eval_id": "test/x/aa/2025-01-01", "model_id": "x",
        "eval_date": "2025-01-01", "source": "test", "overall_score": 85.0,
    })
    assert len(errors) == 0


def test_validate_evaluation_missing_fields():
    errors = validate_evaluation({"source": "test"})
    assert len(errors) > 0
