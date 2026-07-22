"""Clustering evaluation against `theme_hint`. Read only here, after clustering ran -
never inside clustering.py/keywords.py/naming.py.
"""

from collections import Counter, defaultdict

from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

UNCLUSTERED = "unclustered"


def evaluate_clustering(records: list[dict], assignments: dict[str, str | None]) -> dict:
    """records: full dataset rows (feedback_id, theme_hint). assignments: feedback_id ->
    theme_id or None."""
    total = len(records)
    n_assigned = sum(1 for r in records if assignments.get(r["feedback_id"]))
    coverage = n_assigned / total if total else None
    unclustered_pct = (1 - coverage) if coverage is not None else None

    themed = [r for r in records if r["theme_hint"]]
    true_labels = [r["theme_hint"] for r in themed]
    pred_labels = [assignments.get(r["feedback_id"]) or UNCLUSTERED for r in themed]
    n = len(themed)

    ari = adjusted_rand_score(true_labels, pred_labels) if n else None
    nmi = normalized_mutual_info_score(true_labels, pred_labels) if n else None

    by_pred: dict[str, list[str]] = defaultdict(list)
    for t, p in zip(true_labels, pred_labels):
        if p != UNCLUSTERED:
            by_pred[p].append(t)
    purity_num = sum(Counter(v).most_common(1)[0][1] for v in by_pred.values())
    purity_den = sum(len(v) for v in by_pred.values())
    purity = purity_num / purity_den if purity_den else None

    tp = fp = fn = 0
    for i in range(n):
        for j in range(i + 1, n):
            same_true = true_labels[i] == true_labels[j]
            same_pred = pred_labels[i] == pred_labels[j] and pred_labels[i] != UNCLUSTERED
            if same_true and same_pred:
                tp += 1
            elif same_pred and not same_true:
                fp += 1
            elif same_true and not same_pred:
                fn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None

    true_to_preds: dict[str, Counter] = defaultdict(Counter)
    for t, p in zip(true_labels, pred_labels):
        if p != UNCLUSTERED:
            true_to_preds[t][p] += 1
    fragmented_true_themes = sorted(
        t for t, c in true_to_preds.items() if len([v for v in c.values() if v >= 2]) > 1
    )

    # "mixed/incoherent": no single true theme accounts for a clear majority (a 50/50 split
    # counts as mixed too, since neither label dominates).
    mixed_predicted_themes = sorted(
        p for p, v in by_pred.items() if Counter(v).most_common(1)[0][1] / len(v) <= 0.5
    )

    return {
        "n_total": total,
        "n_assigned": n_assigned,
        "coverage": coverage,
        "unclustered_percentage": unclustered_pct,
        "n_themed_records_evaluated": n,
        "cluster_purity": purity,
        "adjusted_rand_index": ari,
        "normalized_mutual_information": nmi,
        "pairwise_precision": precision,
        "pairwise_recall": recall,
        "pairwise_f1": f1,
        "fragmented_true_themes": fragmented_true_themes,
        "n_fragmented_true_themes": len(fragmented_true_themes),
        "mixed_predicted_themes": mixed_predicted_themes,
        "n_mixed_predicted_themes": len(mixed_predicted_themes),
    }
