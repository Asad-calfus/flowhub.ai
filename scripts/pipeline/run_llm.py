"""Run the few-shot LLM classifier over the gold evaluation set (30 records only).

Safe by default: this script ALWAYS runs in dry-run mode (no API calls, no cost) unless
you pass --live explicitly, even if an API key is present in the environment. This
prevents an accidental real spend just from having a key configured.

Usage:
    python3 scripts/pipeline/run_llm.py                 # dry-run stub, no API calls, no cost
    python3 scripts/pipeline/run_llm.py --live           # real API calls; prints a cost estimate
                                                 # and asks for confirmation first
    python3 scripts/pipeline/run_llm.py --live --yes     # real API calls, skip the confirmation prompt
    python3 scripts/pipeline/run_llm.py --force          # bypass the local cache and reclassify everything
"""

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classification.classifier import FewShotClassifier
from src.classification.pricing import RECOMMENDED_MODEL, estimate_run_cost_usd
from src.classification.prompt_builder import select_few_shot_examples
from src.classification.schemas import ClassifierInput
from src.data_loader import REPO_ROOT, load_gold_records, load_non_gold_records

PREDICTIONS_PATH = os.path.join(REPO_ROOT, "results", "llm_predictions.csv")
FAILURES_PATH = os.path.join(REPO_ROOT, "results", "llm_failures.json")
RUN_META_PATH = os.path.join(REPO_ROOT, "results", "llm_run_meta.json")

COLUMNS = [
    "feedback_id",
    "predicted_feedback_type", "predicted_category", "predicted_product_module",
    "predicted_sentiment", "predicted_urgency", "confidence", "reasoning",
    "actual_feedback_type", "actual_category", "actual_product_module",
    "actual_sentiment", "actual_urgency",
    "retries", "latency_seconds", "input_tokens", "output_tokens", "from_cache", "dry_run", "error",
]


def _confirm_live_run(classifier: FewShotClassifier, gold: list[dict], force: bool) -> bool:
    to_call = gold if force else [r for r in gold if r["feedback_id"] not in classifier.cache]
    n = len(to_call)
    if n == 0:
        print("All gold records already have a valid cached prediction - nothing to call.")
        print("(use --force to reclassify anyway)")
        return False

    estimate = estimate_run_cost_usd(classifier.model, n)
    print(f"About to make {n} real '{classifier.provider}' API call(s) with model '{classifier.model}'.")
    if estimate is not None:
        print(f"Estimated cost: ~${estimate:.4f} USD (rough estimate, not billing-accurate).")
    else:
        print(f"No pricing data for model '{classifier.model}' - cost estimate unavailable. Proceed carefully.")
        print(f"Cost-efficient defaults: {RECOMMENDED_MODEL}")

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

    gold = load_gold_records()
    non_gold = load_non_gold_records()
    examples = select_few_shot_examples(non_gold, per_type=1)

    # Safe-by-default: only --live can turn off dry-run. Just having an API key in the
    # environment is not enough to trigger real spend.
    classifier = FewShotClassifier(examples=examples, dry_run=not args.live)

    if args.live:
        if not classifier.api_key:
            print(f"--live requires {classifier._api_key_env_var()} to be set. Aborting.")
            sys.exit(1)
        if not args.yes and not _confirm_live_run(classifier, gold, args.force):
            print("Aborted - no API calls made.")
            sys.exit(0)

    rows = []
    results = []
    for record in gold:
        clf_input = ClassifierInput.from_record(record)
        result = classifier.classify(record["feedback_id"], clf_input, force=args.force)
        results.append(result)

        output = result.output
        rows.append({
            "feedback_id": record["feedback_id"],
            "predicted_feedback_type": output.feedback_type if output else "",
            "predicted_category": output.category if output else "",
            "predicted_product_module": output.product_module if output else "",
            "predicted_sentiment": output.sentiment if output else "",
            "predicted_urgency": output.urgency if output else "",
            "confidence": output.confidence if output else "",
            "reasoning": output.reasoning if output else "",
            "actual_feedback_type": record["feedback_type"],
            "actual_category": record["category"],
            "actual_product_module": record["product_module"],
            "actual_sentiment": record["sentiment"],
            "actual_urgency": record["urgency"],
            "retries": result.retries,
            "latency_seconds": round(result.latency_seconds, 4),
            "input_tokens": result.input_tokens or "",
            "output_tokens": result.output_tokens or "",
            "from_cache": result.from_cache,
            "dry_run": result.dry_run,
            "error": result.error or "",
        })

    os.makedirs(os.path.dirname(PREDICTIONS_PATH), exist_ok=True)
    with open(PREDICTIONS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with open(FAILURES_PATH, "w", encoding="utf-8") as f:
        json.dump(classifier.failures, f, indent=2)

    with open(RUN_META_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "dry_run": classifier.dry_run,
            "model": classifier.model,
            "provider": classifier.provider,
            "n_examples": len(examples),
            "example_ids": [e["feedback_id"] for e in examples],
        }, f, indent=2)

    print(f"Wrote {len(rows)} LLM predictions to {PREDICTIONS_PATH} (dry_run={classifier.dry_run})")
    print(f"Failures: {len(classifier.failures)} -> {FAILURES_PATH}")


if __name__ == "__main__":
    main()
