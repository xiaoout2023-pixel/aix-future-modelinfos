from modelinfo.validator import validate_model, validate_pricing, validate_evaluation


class Writer:
    def __init__(self, db):
        self.db = db

    def write_models(self, models: list[dict]) -> dict:
        upserted = 0
        errors = 0
        for model in models:
            validation_errors = validate_model(model)
            if validation_errors:
                errors += 1
                continue
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
