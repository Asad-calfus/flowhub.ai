"""Run the deterministic rule-based + VADER baseline over the gold evaluation set.

Usage:
    python3 scripts/run_baseline.py
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classification.baseline import classify_baseline
from src.classification.schemas import ClassifierInput
from src.data_loader import REPO_ROOT, load_gold_records

OUTPUT_PATH = os.path.join(REPO_ROOT, "results", "baseline_predictions.csv")

COLUMNS = [
    "feedback_id",
    "predicted_feedback_type", "predicted_category", "predicted_product_module",
    "predicted_sentiment", "predicted_urgency", "confidence", "reasoning",
    "actual_feedback_type", "actual_category", "actual_product_module",
    "actual_sentiment", "actual_urgency",
]


def main():
    gold = load_gold_records()
    rows = []
    for record in gold:
        clf_input = ClassifierInput.from_record(record)
        output = classify_baseline(clf_input)
        rows.append({
            "feedback_id": record["feedback_id"],
            "predicted_feedback_type": output.feedback_type,
            "predicted_category": output.category,
            "predicted_product_module": output.product_module,
            "predicted_sentiment": output.sentiment,
            "predicted_urgency": output.urgency,
            "confidence": output.confidence,
            "reasoning": output.reasoning,
            "actual_feedback_type": record["feedback_type"],
            "actual_category": record["category"],
            "actual_product_module": record["product_module"],
            "actual_sentiment": record["sentiment"],
            "actual_urgency": record["urgency"],
        })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} baseline predictions to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
