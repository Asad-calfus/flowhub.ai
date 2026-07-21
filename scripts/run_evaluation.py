"""Evaluate baseline_predictions.csv and llm_predictions.csv against the gold set.

Usage:
    python3 scripts/run_evaluation.py
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classification.evaluator import evaluate_predictions, summarize_run_from_rows
from src.classification.schemas import PREDICTION_FIELDS
from src.data_loader import REPO_ROOT, load_gold_records

RESULTS_DIR = os.path.join(REPO_ROOT, "results")
METRICS_PATH = os.path.join(RESULTS_DIR, "evaluation_metrics.json")

PRED_FIELD_MAP = {
    "feedback_type": "predicted_feedback_type",
    "category": "predicted_category",
    "product_module": "predicted_product_module",
    "sentiment": "predicted_sentiment",
    "urgency": "predicted_urgency",
}


def _read_predictions_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _rows_to_predictions(rows: list[dict]) -> dict[str, dict]:
    predictions = {}
    for row in rows:
        if row.get("error"):
            continue
        if not row.get("predicted_feedback_type"):
            continue
        predictions[row["feedback_id"]] = {
            field: row[PRED_FIELD_MAP[field]] for field in PREDICTION_FIELDS
        }
    return predictions


def _strip_confusion_and_per_class_for_print(field_metrics: dict) -> dict:
    return {
        k: v for k, v in field_metrics.items() if k not in ("confusion_matrix", "per_class")
    }


def main():
    gold = load_gold_records()

    baseline_rows = _read_predictions_csv(os.path.join(RESULTS_DIR, "baseline_predictions.csv"))
    llm_rows = _read_predictions_csv(os.path.join(RESULTS_DIR, "llm_predictions.csv"))

    report = {}

    if baseline_rows:
        baseline_preds = _rows_to_predictions(baseline_rows)
        report["baseline"] = evaluate_predictions(gold, baseline_preds)

    if llm_rows:
        llm_preds = _rows_to_predictions(llm_rows)
        report["llm"] = evaluate_predictions(gold, llm_preds)
        report["llm"]["run_summary"] = summarize_run_from_rows(llm_rows)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote evaluation metrics to {METRICS_PATH}\n")
    for model_name, model_report in report.items():
        print(f"=== {model_name} ===")
        print(f"scored {model_report['scored_count']}/{model_report['total_gold_count']} gold records")
        for field, m in model_report["fields"].items():
            print(f"  {field}: accuracy={m['accuracy']:.2f} macro_P={m['macro_precision']:.2f} "
                  f"macro_R={m['macro_recall']:.2f} macro_F1={m['macro_f1']:.2f}")
        if "run_summary" in model_report:
            rs = model_report["run_summary"]
            print(f"  schema_success_rate={rs['schema_success_rate']:.2f} "
                  f"retries={rs['retry_count']} failures={rs['failure_count']} "
                  f"avg_latency={rs['average_latency_seconds']}")
        print()


if __name__ == "__main__":
    main()
