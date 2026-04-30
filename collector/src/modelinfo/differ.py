from modelinfo.models import ChangeRecord

PRICE_FIELDS = [
    "input_price_per_1m", "output_price_per_1m",
    "cache_read_price_per_1m", "cache_write_price_per_1m",
    "price_per_request", "price_per_image", "price_per_audio_min",
    "free_tier_tokens",
]


def diff_models(
    old: dict[str, dict], new: dict[str, dict]
) -> tuple[list[ChangeRecord], list[ChangeRecord], list[str]]:
    added: list[ChangeRecord] = []
    updated: list[ChangeRecord] = []
    unchanged: list[str] = []

    for model_id, new_data in new.items():
        if model_id not in old:
            added.append(ChangeRecord(
                table_name="models", model_id=model_id,
                field_name="*", new_value="new model",
            ))
        else:
            old_data = old[model_id]
            changed = False
            for field, new_val in new_data.items():
                old_val = old_data.get(field)
                if str(old_val) != str(new_val):
                    updated.append(ChangeRecord(
                        table_name="models", model_id=model_id,
                        field_name=field,
                        old_value=str(old_val) if old_val is not None else None,
                        new_value=str(new_val) if new_val is not None else None,
                    ))
                    changed = True
            if not changed:
                unchanged.append(model_id)

    return added, updated, unchanged


def diff_pricing(
    model_id: str,
    old_pricing: list[dict],
    new_pricing: list[dict],
) -> tuple[list[ChangeRecord], list[str]]:
    changed: list[ChangeRecord] = []
    unchanged: list[str] = []

    old_latest = old_pricing[0] if old_pricing else None
    new_latest = new_pricing[0] if new_pricing else None

    if old_latest and new_latest:
        for field in PRICE_FIELDS:
            old_val = old_latest.get(field)
            new_val = new_latest.get(field)
            if old_val != new_val:
                changed.append(ChangeRecord(
                    table_name="pricing", model_id=model_id,
                    field_name=field,
                    old_value=str(old_val) if old_val is not None else None,
                    new_value=str(new_val) if new_val is not None else None,
                ))
        if not changed:
            unchanged.append(model_id)
    elif new_latest and not old_latest:
        changed.append(ChangeRecord(
            table_name="pricing", model_id=model_id,
            field_name="*", new_value="new pricing",
        ))
    elif old_latest and not new_latest:
        changed.append(ChangeRecord(
            table_name="pricing", model_id=model_id,
            field_name="*", new_value="pricing removed",
        ))

    return changed, unchanged
