def validate_model(data: dict) -> list[str]:
    errors = []
    if not data.get("model_id"):
        errors.append("model_id is required")
    if not data.get("model_name"):
        errors.append("model_name is required")
    if not data.get("provider"):
        errors.append("provider is required")
    ctx = data.get("context_length")
    if ctx is not None and ctx <= 0:
        errors.append(f"context_length must be positive, got {ctx}")
    max_out = data.get("max_output_tokens")
    if max_out is not None and max_out <= 0:
        errors.append(f"max_output_tokens must be positive, got {max_out}")
    return errors


def validate_pricing(data: dict) -> list[str]:
    errors = []
    if not data.get("pricing_id"):
        errors.append("pricing_id is required")
    if not data.get("model_id"):
        errors.append("model_id is required")
    if not data.get("valid_from"):
        errors.append("valid_from is required")

    input_price = data.get("input_price_per_1m")
    if input_price is not None:
        if input_price < 0:
            errors.append(f"input_price_per_1m is negative: {input_price}")
        elif input_price > 500:
            errors.append(f"input_price_per_1m seems unreasonable: {input_price}")

    output_price = data.get("output_price_per_1m")
    if output_price is not None:
        if output_price < 0:
            errors.append(f"output_price_per_1m is negative: {output_price}")
        elif output_price > 1000:
            errors.append(f"output_price_per_1m seems unreasonable: {output_price}")

    return errors


def validate_evaluation(data: dict) -> list[str]:
    errors = []
    if not data.get("eval_id"):
        errors.append("eval_id is required")
    if not data.get("model_id"):
        errors.append("model_id is required")
    if not data.get("eval_date"):
        errors.append("eval_date is required")
    if not data.get("source"):
        errors.append("source is required")
    overall = data.get("overall_score")
    if overall is not None and (overall < 0 or overall > 100):
        errors.append(f"overall_score out of range: {overall}")
    return errors
