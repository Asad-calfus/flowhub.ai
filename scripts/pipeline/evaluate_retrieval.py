"""Evaluate retrieval predictions against gold labels (used only after retrieval ran).

Usage:
    python3 scripts/pipeline/evaluate_retrieval.py
"""

import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_loader import REPO_ROOT, load_full_dataset, load_gold_records  # noqa: E402
from src.retrieval.evaluator import evaluate_context_matches, evaluate_similar_feedback  # noqa: E402
from src.retrieval.schemas import ContextCandidate, ContextMatchResult  # noqa: E402

RESULTS_DIR = os.path.join(REPO_ROOT, "results", "retrieval")
METRICS_PATH = os.path.join(RESULTS_DIR, "retrieval_metrics.json")


def _parse_matches(raw: str, context_type: str) -> list[ContextCandidate]:
    if not raw:
        return []
    out = []
    for rank, item in enumerate(raw.split(";"), start=1):
        cid, score = item.rsplit(":", 1)
        out.append(ContextCandidate(context_id=cid, context_type=context_type, title=cid, rank=rank, similarity_score=float(score)))
    return out


def main():
    with open(os.path.join(RESULTS_DIR, "similar_feedback_predictions.csv"), newline="", encoding="utf-8") as f:
        similar_rows = list(csv.DictReader(f))
    with open(os.path.join(RESULTS_DIR, "context_match_predictions.csv"), newline="", encoding="utf-8") as f:
        context_rows = list(csv.DictReader(f))

    top5_by_id = defaultdict(list)
    for row in sorted(similar_rows, key=lambda r: int(r["rank"])):
        top5_by_id[row["feedback_id"]].append((row["matched_feedback_id"], float(row["similarity_score"])))

    context_results = {}
    for row in context_rows:
        context_results[row["feedback_id"]] = ContextMatchResult(
            feedback_id=row["feedback_id"],
            status=row["status"],
            matched_context_id=row["matched_context_id"] or None,
            bugs=_parse_matches(row["bug_matches"], "known_bug"),
            feature_requests=_parse_matches(row["feature_request_matches"], "feature_request"),
            releases=_parse_matches(row["release_matches"], "release"),
        )

    gold = load_gold_records()
    all_rows = load_full_dataset()

    context_metrics = evaluate_context_matches(gold, context_results)
    similar_metrics = evaluate_similar_feedback(all_rows, dict(top5_by_id))
    avg_context_latency = (
        sum(float(r["latency_seconds"]) for r in context_rows) / len(context_rows) if context_rows else None
    )

    report = {
        "context_matching": {**context_metrics, "average_latency_seconds": avg_context_latency},
        "similar_feedback": similar_metrics,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Wrote {METRICS_PATH}\n")
    print("=== context matching (gold set) ===")
    for k, v in context_metrics.items():
        print(f"  {k}: {v}")
    print("\n=== similar feedback (all records) ===")
    for k, v in similar_metrics.items():
        if k != "similar_wording_different_meaning_checks":
            print(f"  {k}: {v}")
    print(f"  similar_wording_different_meaning_checks: {similar_metrics['similar_wording_different_meaning_checks']}")


if __name__ == "__main__":
    main()
