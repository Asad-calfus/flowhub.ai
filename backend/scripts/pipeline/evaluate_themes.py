"""Evaluate theme clustering against `theme_hint` (read only here, after clustering ran).

Usage:
    python3 scripts/pipeline/evaluate_themes.py
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_loader import REPO_ROOT, load_full_dataset  # noqa: E402
from src.themes.evaluator import evaluate_clustering  # noqa: E402

RESULTS_DIR = os.path.join(REPO_ROOT, "results", "themes")
ASSIGNMENTS_PATH = os.path.join(RESULTS_DIR, "theme_assignments.csv")
METRICS_PATH = os.path.join(RESULTS_DIR, "theme_metrics.json")


def main():
    with open(ASSIGNMENTS_PATH, newline="", encoding="utf-8") as f:
        assignment_rows = list(csv.DictReader(f))
    assignments = {r["feedback_id"]: (r["theme_id"] or None) for r in assignment_rows}

    records = load_full_dataset()
    evaluation = evaluate_clustering(records, assignments)

    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)
    metrics["evaluation"] = evaluation
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Updated {METRICS_PATH} with evaluation section\n")
    for k, v in evaluation.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
