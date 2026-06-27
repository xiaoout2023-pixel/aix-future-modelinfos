from modelinfo.validator import validate_model, validate_pricing, validate_evaluation
from modelinfo.differ import diff_models, diff_pricing
from modelinfo.models import ChangeRecord
import structlog

logger = structlog.get_logger()


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

        try:
            existing_rows = self.db.get_all_models()
            old_models = {r["model_id"]: r for r in existing_rows}
            added, updated, _ = diff_models(old_models, valid_models)
            self.changes.extend(added)
            self.changes.extend(updated)
        except Exception as e:
            logger.warning("diff_models_failed", error=str(e))

        # Batch upsert all valid models in one go
        try:
            self.db.upsert_models(list(valid_models.values()))
            upserted = len(valid_models)
        except Exception as e:
            logger.warning("batch_upsert_models_failed", error=str(e), action="fallback_to_single")
            for model in valid_models.values():
                try:
                    self.db.upsert_model(model)
                    upserted += 1
                except Exception as e2:
                    errors += 1
                    logger.warning("upsert_model_failed", model_id=model.get("model_id"), error=str(e2))
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}

    def write_pricing(self, pricings: list[dict]) -> dict:
        upserted = 0
        errors = 0
        valid_pricings = []
        for p in pricings:
            validation_errors = validate_pricing(p)
            if validation_errors:
                errors += 1
                continue
            valid_pricings.append(p)

        # Diff pass: collect changes (one query per model, but uses index now)
        for p in valid_pricings:
            try:
                model_id = p.get("model_id", "")
                old_pricing_rows = self.db.get_all_pricing_for_model(model_id)
                changed, _ = diff_pricing(model_id, old_pricing_rows, [p])
                self.changes.extend(changed)
            except Exception as e:
                logger.warning("diff_pricing_failed", model_id=p.get("model_id"), error=str(e))

        # Batch upsert all valid pricings
        try:
            self.db.upsert_pricings(valid_pricings)
            upserted = len(valid_pricings)
        except Exception as e:
            logger.warning("batch_upsert_pricing_failed", error=str(e), action="fallback_to_single")
            for p in valid_pricings:
                try:
                    self.db.upsert_pricing(p)
                    upserted += 1
                except Exception as e2:
                    errors += 1
                    logger.warning("upsert_pricing_failed", model_id=p.get("model_id"), error=str(e2))
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}

    def write_evaluations(self, evals: list[dict]) -> dict:
        upserted = 0
        errors = 0
        valid_evals = []
        for e in evals:
            validation_errors = validate_evaluation(e)
            if validation_errors:
                errors += 1
                continue
            valid_evals.append(e)

        # Batch upsert all valid evaluations
        try:
            self.db.upsert_evaluations(valid_evals)
            upserted = len(valid_evals)
        except Exception as e:
            logger.warning("batch_upsert_evaluations_failed", error=str(e), action="fallback_to_single")
            for e in valid_evals:
                try:
                    self.db.upsert_evaluation(e)
                    upserted += 1
                except Exception as ex:
                    errors += 1
                    logger.warning("upsert_evaluation_failed", eval_id=e.get("eval_id"), error=str(ex))
        return {"upserted": upserted, "errors": errors, "changes_written": upserted}
