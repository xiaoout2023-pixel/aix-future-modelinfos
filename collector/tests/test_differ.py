from modelinfo.differ import diff_models, diff_pricing


def test_diff_models_detects_new():
    old = {}
    new = {"openai/gpt-4o": {"model_name": "GPT-4o", "context_length": 128000}}
    added, updated, unchanged = diff_models(old, new)
    assert len(added) == 1
    assert added[0].model_id == "openai/gpt-4o"


def test_diff_models_detects_change():
    old = {"openai/gpt-4o": {"context_length": 128000, "model_name": "GPT-4o"}}
    new = {"openai/gpt-4o": {"context_length": 256000, "model_name": "GPT-4o"}}
    added, updated, unchanged = diff_models(old, new)
    assert len(updated) == 1
    assert updated[0].field_name == "context_length"
    assert updated[0].old_value == "128000"
    assert updated[0].new_value == "256000"


def test_diff_models_detects_unchanged():
    old = {"openai/gpt-4o": {"context_length": 128000}}
    new = {"openai/gpt-4o": {"context_length": 128000}}
    added, updated, unchanged = diff_models(old, new)
    assert len(unchanged) == 1
    assert len(updated) == 0


def test_diff_models_multiple_fields():
    old = {"x": {"a": "1", "b": "2"}}
    new = {"x": {"a": "1_changed", "b": "2"}}
    added, updated, unchanged = diff_models(old, new)
    assert len(updated) == 1
    assert updated[0].field_name == "a"


def test_diff_pricing_detects_price_change():
    old = [{"pricing_id": "a", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0}]
    new = [{"pricing_id": "b", "input_price_per_1m": 2.0, "output_price_per_1m": 8.0}]
    changed, unchanged = diff_pricing("x", old, new)
    assert any(c.field_name == "input_price_per_1m" for c in changed)
    assert any(c.field_name == "output_price_per_1m" for c in changed)


def test_diff_pricing_no_change():
    old = [{"input_price_per_1m": 2.5, "output_price_per_1m": 10.0}]
    new = [{"input_price_per_1m": 2.5, "output_price_per_1m": 10.0}]
    changed, unchanged = diff_pricing("x", old, new)
    assert len(changed) == 0
    assert len(unchanged) == 1
