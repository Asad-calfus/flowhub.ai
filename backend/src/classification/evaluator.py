"""Evaluation metrics for classifier predictions against the gold dataset.

Implemented without sklearn (macro precision/recall/F1 and confusion matrices are
simple enough to compute directly) to keep the dependency list small.
"""

from collections import defaultdict
from statistics import mean
from typing import Optional

from src.classification.schemas import PREDICTION_FIELDS


def confusion_matrix(y_true: list[str], y_pred: list[str]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred):
        matrix[t][p] += 1
    return {t: dict(preds) for t, preds in matrix.items()}


def _precision_recall_f1_per_class(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict[str, float]]:
    per_class = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    return per_class


def field_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    assert len(y_true) == len(y_pred) and len(y_true) > 0
    labels = sorted(set(y_true) | set(y_pred))
    per_class = _precision_recall_f1_per_class(y_true, y_pred, labels)

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    macro_precision = mean(c["precision"] for c in per_class.values())
    macro_recall = mean(c["recall"] for c in per_class.values())
    macro_f1 = mean(c["f1"] for c in per_class.values())

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred),
        "n": len(y_true),
    }


def evaluate_predictions(gold_records: list[dict], predictions: dict[str, dict]) -> dict:
    """gold_records: rows from gold_feedback.csv. predictions: feedback_id -> dict with
    PREDICTION_FIELDS keys (missing/failed predictions should be omitted from `predictions`
    and are reported separately as `unscored`).
    """
    metrics: dict = {"fields": {}}
    unscored = [r["feedback_id"] for r in gold_records if r["feedback_id"] not in predictions]

    for field in PREDICTION_FIELDS:
        y_true, y_pred = [], []
        for record in gold_records:
            fid = record["feedback_id"]
            if fid not in predictions:
                continue
            y_true.append(record[field])
            y_pred.append(predictions[fid][field])
        if y_true:
            metrics["fields"][field] = field_metrics(y_true, y_pred)

    metrics["unscored_feedback_ids"] = unscored
    metrics["scored_count"] = len(gold_records) - len(unscored)
    metrics["total_gold_count"] = len(gold_records)
    return metrics


def summarize_run(results: list) -> dict:
    """results: list[ClassificationResult]. Aggregates run-level (not label-accuracy) stats."""
    total = len(results)
    successes = [r for r in results if r.output is not None]
    failures = [r for r in results if r.output is None]
    retries_total = sum(r.retries for r in results)
    latencies = [r.latency_seconds for r in results if not r.from_cache]
    in_tokens = [r.input_tokens for r in results if r.input_tokens]
    out_tokens = [r.output_tokens for r in results if r.output_tokens]

    return {
        "total_records": total,
        "schema_success_count": len(successes),
        "schema_success_rate": len(successes) / total if total else 0.0,
        "failure_count": len(failures),
        "retry_count": retries_total,
        "cache_hit_count": sum(1 for r in results if r.from_cache),
        "average_latency_seconds": mean(latencies) if latencies else None,
        "total_input_tokens": sum(in_tokens) if in_tokens else None,
        "total_output_tokens": sum(out_tokens) if out_tokens else None,
        "average_input_tokens": mean(in_tokens) if in_tokens else None,
        "average_output_tokens": mean(out_tokens) if out_tokens else None,
        "dry_run": results[0].dry_run if results else None,
    }


def summarize_run_from_rows(rows: list[dict]) -> dict:
    """Same as summarize_run but operating on CSV-parsed prediction rows (all strings)."""
    total = len(rows)
    successes = [r for r in rows if r.get("error", "") == "" and r.get("predicted_feedback_type", "")]
    failures = [r for r in rows if r not in successes]
    retries_total = sum(int(r.get("retries") or 0) for r in rows)
    latencies = [float(r["latency_seconds"]) for r in rows if r.get("from_cache") != "True" and r.get("latency_seconds")]
    in_tokens = [int(r["input_tokens"]) for r in rows if r.get("input_tokens")]
    out_tokens = [int(r["output_tokens"]) for r in rows if r.get("output_tokens")]

    return {
        "total_records": total,
        "schema_success_count": len(successes),
        "schema_success_rate": len(successes) / total if total else 0.0,
        "failure_count": len(failures),
        "retry_count": retries_total,
        "cache_hit_count": sum(1 for r in rows if r.get("from_cache") == "True"),
        "average_latency_seconds": mean(latencies) if latencies else None,
        "total_input_tokens": sum(in_tokens) if in_tokens else None,
        "total_output_tokens": sum(out_tokens) if out_tokens else None,
        "average_input_tokens": mean(in_tokens) if in_tokens else None,
        "average_output_tokens": mean(out_tokens) if out_tokens else None,
        "dry_run": rows[0].get("dry_run") == "True" if rows else None,
    }
