"""Run the few-shot LLM classifier over the gold evaluation set (30 records only).

Safe by default: this script ALWAYS runs in dry-run mode (no API calls, no cost) unless
you pass --live explicitly, even if an API key is present in the environment. This
prevents an accidental real spend just from having a key configured.

Results are written to Postgres: one `analysis_results` row per classified record, and
one `evaluation_runs` row summarizing the run (field-level accuracy vs. gold labels, plus
schema-success/latency/token/cache-hit stats). Per-record telemetry (model, tokens,
latency, cache hit, predicted label) is also logged as JSON Lines to
results/logs/classification_runs.jsonl.

Usage:
    python3 scripts/pipeline/run_llm.py                 # dry-run stub, no API calls, no cost
    python3 scripts/pipeline/run_llm.py --live           # real API calls; prints a cost estimate
                                                 # and asks for confirmation first
    python3 scripts/pipeline/run_llm.py --live --yes     # real API calls, skip the confirmation prompt
    python3 scripts/pipeline/run_llm.py --force          # bypass the local cache and reclassify everything
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.analysis import AnalysisResult
from app.repositories import analysis as analysis_repo
from app.repositories import evaluation as evaluation_repo
from app.repositories import feedback as feedback_repo
from app.models.evaluation import EvaluationRun
from src.classification.classifier import FewShotClassifier
from src.classification.evaluator import evaluate_predictions, summarize_run
from src.classification.pricing import RECOMMENDED_MODEL, estimate_run_cost_usd
from src.classification.prompt_builder import select_few_shot_examples
from src.classification.schemas import ClassifierInput
from src.data_loader import REPO_ROOT, load_gold_records, load_non_gold_records
from src.logging_utils import get_jsonl_logger

LOG_PATH = os.path.join(REPO_ROOT, "results", "logs", "classification_runs.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _confirm_live_run(classifier: FewShotClassifier, gold: list[dict], force: bool) -> bool:
    to_call = gold if force else [r for r in gold if r["feedback_id"] not in classifier.cache]
    n = len(to_call)
    if n == 0:
        logger.info("All gold records already have a valid cached prediction - nothing to call.")
        logger.info("(use --force to reclassify anyway)")
        return False

    estimate = estimate_run_cost_usd(classifier.model, n)
    logger.info(f"About to make {n} real '{classifier.provider}' API call(s) with model '{classifier.model}'.")
    if estimate is not None:
        logger.info(f"Estimated cost: ~${estimate:.4f} USD (rough estimate, not billing-accurate).")
    else:
        logger.info(f"No pricing data for model '{classifier.model}' - cost estimate unavailable. Proceed carefully.")
        logger.info(f"Cost-efficient defaults: {RECOMMENDED_MODEL}")

    reply = input("Proceed with live API calls? [y/N]: ").strip().lower()
    return reply == "y"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true", help="make real API calls (default is always dry-run)")
    group.add_argument("--dry-run", action="store_true", help="explicit no-op: dry-run is already the default")
    parser.add_argument("--force", action="store_true", help="bypass cache and reclassify all records")
    parser.add_argument("--yes", action="store_true", help="skip the cost-estimate confirmation prompt for --live")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    get_jsonl_logger("classification.runs", LOG_PATH)

    gold = load_gold_records()
    non_gold = load_non_gold_records()
    examples = select_few_shot_examples(non_gold, per_type=1)

    # Safe-by-default: only --live can turn off dry-run. Just having an API key in the
    # environment is not enough to trigger real spend.
    classifier = FewShotClassifier(examples=examples, dry_run=not args.live)

    if args.live:
        if not classifier.api_key:
            logger.error(f"--live requires {classifier._api_key_env_var()} to be set. Aborting.")
            sys.exit(1)
        if not args.yes and not _confirm_live_run(classifier, gold, args.force):
            logger.info("Aborted - no API calls made.")
            sys.exit(0)

    results = []
    predictions = {}

    db = SessionLocal()
    try:
        for record in gold:
            feedback_id = record["feedback_id"]
            clf_input = ClassifierInput.from_record(record)
            result = classifier.classify(feedback_id, clf_input, force=args.force)
            results.append(result)

            if result.output is None:
                continue

            output = result.output
            predictions[feedback_id] = output.model_dump()
            model_name = "dry-run-stub" if result.dry_run else f"{classifier.provider}:{classifier.model}"

            analysis_repo.create(db, AnalysisResult(
                feedback_id=feedback_id,
                feedback_type=output.feedback_type,
                category=output.category,
                product_module=output.product_module,
                sentiment=output.sentiment,
                urgency=output.urgency,
                confidence=output.confidence,
                reasoning=output.reasoning,
                model_name=model_name,
                prompt_version="v1",
            ))
            feedback = feedback_repo.get(db, feedback_id)
            feedback.processing_status = "processed"

        field_metrics = evaluate_predictions(gold, predictions)
        run_summary = summarize_run(results)
        evaluation_repo.create(db, EvaluationRun(
            model_name=classifier.model,
            dry_run=bool(run_summary["dry_run"]),
            scored_count=field_metrics["scored_count"],
            total_gold_count=field_metrics["total_gold_count"],
            metrics_json={**field_metrics, "run_summary": run_summary},
        ))

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    logger.info(
        f"Classified {len(results)} gold records "
        f"({len(predictions)} succeeded, {len(classifier.failures)} failed), dry_run={classifier.dry_run}"
    )
    logger.info(f"Stored analysis_results + evaluation_runs rows in Postgres; per-record log -> {LOG_PATH}")


if __name__ == "__main__":
    main()
