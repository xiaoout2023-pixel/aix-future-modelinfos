from modelinfo.validator import validate_model, validate_pricing, validate_evaluation
from modelinfo.differ import diff_models, diff_pricing
from modelinfo.models import ChangeRecord


class Writer:
    def __init__(self, db):
        self.db = db
        self.changes: list[ChangeRecord] = []

    def write_models(self, models: list[dict]) -> dict:
        upserted = 0
        errors = 0
        valid_models = {}
        for model in models:
            validation_errors = validate_model(model)
            if validation_errors:
                errors += 1
                continue
            valid_models[model["model_id"]] = model

        existing_rows = self.db.get_all_models()
        old_models = {r["model_id"]: r for r in existing_rows}
        added, updated, _ = diff_models(old_models, valid_models)
        self.changes.extend(added)
        self.changes.extend(updated)

        for model in valid_models.values():
            self.db.upsert_model(model)
            upserted += 1
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}

    def write_pricing(self, pricings: list[dict]) -> dict:
        upserted = 0
        errors = 0
        for p in pricings:
            validation_errors = validate_pricing(p)
            if validation_errors:
                errors += 1
                continue
            model_id = p.get("model_id", "")
            channel = p.get("channel", "official")
            region = p.get("region", "global")
            old_pricing_rows = self.db.get_all_pricing_for_model(model_id)
            changed, _ = diff_pricing(model_id, old_pricing_rows, [p])
            self.changes.extend(changed)

            self.db.upsert_pricing(p)
            upserted += 1
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}

    def write_evaluations(self, evals: list[dict]) -> dict:
        upserted = 0
        errors = 0
        for e in evals:
            validation_errors = validate_evaluation(e)
            if validation_errors:
                errors += 1
                continue
            self.db.upsert_evaluation(e)
            upserted += 1
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}
